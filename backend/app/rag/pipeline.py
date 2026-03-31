"""
RAG pipeline orchestrator (RC-69).

run_rag() is the single entry point: it embeds the query, retrieves RBAC-
filtered chunks, assembles the prompt, calls Groq, and returns a RagResult.

LangSmith tracing is activated automatically when LANGCHAIN_TRACING_V2=true
and LANGSMITH_API_KEY are set in the environment.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from functools import lru_cache

from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from langsmith import traceable

from app.config import settings
from app.rag.embedder import get_embedder
from app.rag.prompts.prompt_loader import load_system_prompt
from app.rag.retriever import RbacRetriever, RetrievedChunk, RetrieverUnavailableError


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class RagResult:
    answer: str
    sources: list[str]        # unique source_file values, ordered by first appearance
    num_chunks: int
    top_score: float
    run_id: str
    prompt_version: str = field(default_factory=lambda: settings.prompt_version)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _cached_prompt() -> str:
    """Load and cache the system prompt template (avoids disk I/O per request)."""
    return load_system_prompt()


def _build_prompt(
    template: str,
    role: str,
    question: str,
    chunks: list[RetrievedChunk],
    session_history: list[dict] | None,
) -> str:
    context_parts = [
        f"[Source: {c.source_file}]\n{c.text}" for c in chunks
    ]
    context = "\n\n---\n\n".join(context_parts)

    prompt = template.format(role=role, question=question, context=context)

    if session_history:
        history_lines = []
        for turn in session_history:
            prefix = "User" if turn.get("role") == "user" else "Assistant"
            history_lines.append(f"{prefix}: {turn.get('content', '')}")
        history_text = "\n".join(history_lines)
        prompt = f"CHAT HISTORY:\n{history_text}\n\n{prompt}"

    return prompt


def _call_llm_with_retry(llm: ChatGroq, prompt: str) -> str | None:
    """Call the LLM; retry once on failure. Returns None if both attempts fail."""
    for attempt in range(2):
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            return response.content
        except Exception:
            if attempt == 0:
                time.sleep(2)
    return None


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

@traceable
def run_rag(
    query: str,
    user_role: str,
    session_history: list[dict] | None = None,
) -> RagResult:
    """Execute the full RAG pipeline and return a structured result.

    Args:
        query: The user's question (already length-validated by the router).
        user_role: The authenticated user's role — used for RBAC retrieval filter.
        session_history: Optional list of prior turns as ``{"role": ..., "content": ...}``
            dicts. Up to 12 entries (6 pairs) are passed to the prompt.

    Returns:
        :class:`RagResult` containing the LLM answer and source metadata.

    Raises:
        RetrieverUnavailableError: Propagated from the retriever if Qdrant is down.
    """
    run_id = str(uuid.uuid4())
    start_ms = time.monotonic()

    # Build LLM client once (shared with optional rewriter)
    llm = ChatGroq(
        model=settings.groq_model,
        temperature=0,
        request_timeout=settings.groq_timeout_seconds,
        api_key=settings.groq_api_key,
    )

    # Optional HyDE query rewriting
    effective_query = query
    if settings.enable_query_rewrite:
        from app.rag.rewriter import rewrite_query  # local import — optional feature
        effective_query = rewrite_query(query, llm)

    # RBAC-filtered retrieval (may raise RetrieverUnavailableError)
    retriever = RbacRetriever(
        client=_get_qdrant(),
        embedder=get_embedder(),
        collection=settings.qdrant_collection,
    )
    chunks = retriever.retrieve(effective_query, user_role)

    # Zero-result short-circuit — not an error, just no matching docs
    if not chunks:
        return RagResult(
            answer=(
                "I couldn't find relevant information in your accessible documents "
                "to answer that question."
            ),
            sources=[],
            num_chunks=0,
            top_score=0.0,
            run_id=run_id,
        )

    # Assemble prompt
    template = _cached_prompt()
    history_window = (session_history or [])[-12:]  # last 6 pairs = 12 entries
    prompt = _build_prompt(template, user_role, query, chunks, history_window or None)

    # LLM call with one retry
    answer = _call_llm_with_retry(llm, prompt)
    if answer is None:
        answer = (
            "The assistant is temporarily unavailable. Please try again shortly."
        )

    # Deduplicate sources preserving order
    seen: set[str] = set()
    sources: list[str] = []
    for c in chunks:
        if c.source_file not in seen:
            seen.add(c.source_file)
            sources.append(c.source_file)

    result = RagResult(
        answer=answer,
        sources=sources,
        num_chunks=len(chunks),
        top_score=chunks[0].score,
        run_id=run_id,
    )

    # Annotate LangSmith trace with RAG metadata
    try:
        import langsmith
        run_tree = langsmith.get_current_run_tree()
        if run_tree is not None:
            run_tree.metadata.update(
                {
                    "user_role": user_role,
                    "prompt_version": settings.prompt_version,
                    "num_chunks": result.num_chunks,
                    "top_score": result.top_score,
                    "latency_ms": int((time.monotonic() - start_ms) * 1000),
                }
            )
    except Exception:
        pass  # tracing is best-effort; never fail the user request

    return result


# ---------------------------------------------------------------------------
# Lazy Qdrant client (avoids circular import at module load)
# ---------------------------------------------------------------------------

def _get_qdrant():
    from app.dependencies import get_qdrant_client
    return get_qdrant_client()
