"""
RAG pipeline orchestrator (RC-69).

run_rag() is the single entry point: it embeds the query, retrieves RBAC-
filtered chunks, assembles the prompt, calls the configured LLM, and returns
a RagResult.

LangSmith tracing is activated automatically when LANGCHAIN_TRACING_V2=true
and LANGSMITH_API_KEY are set in the environment.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langsmith import traceable

from app.config import settings
from app.guardrails import GuardBlockedError, apply_output_guard, check_input
from app.rag.cost_metrics import TokenUsage, emit_token_metrics, parse_usage_metadata
from app.rag.embedder import get_embedder
from app.rag.llm_factory import build_chat_model
from app.rag.prompts.prompt_loader import load_system_prompt
from app.rag.retriever import RbacRetriever, RetrievedChunk, RetrieverUnavailableError

logger = logging.getLogger(__name__)

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
    tokens_used: int | None = None        # total tokens from provider usage_metadata (RC-123)
    input_tokens: int | None = None       # prompt token count (RC-143)
    output_tokens: int | None = None      # completion token count (RC-143)


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


def _call_llm_with_retry(
    llm: BaseChatModel, prompt: str
) -> tuple[str | None, TokenUsage | None]:
    """Call the LLM with configurable retries on failure.

    Returns:
        (content, token_usage) — content is None if both attempts fail;
        token_usage is None when usage metadata is absent.
    """
    for attempt in range(settings.llm_retry_attempts):
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            usage = parse_usage_metadata(getattr(response, "usage_metadata", None))
            return response.content, usage
        except Exception:
            logger.exception(
                "LLM call failed on attempt %s/%s",
                attempt + 1,
                settings.llm_retry_attempts,
            )
            if attempt < settings.llm_retry_attempts - 1:
                time.sleep(settings.llm_retry_backoff_seconds)
    return None, None


def _anonymize_excerpt(
    text: str,
    max_chars: int | None = None,
) -> str:
    """Presidio-anonymized excerpt of text, truncated to max_chars (RC-124).

    Reuses the Presidio singletons from output_guard to avoid loading spacy twice.
    Best-effort — returns a plain truncated excerpt on any error.
    """
    max_chars = max_chars or settings.langsmith_chunk_excerpt_max_chars
    truncated = text[:max_chars]
    try:
        from app.guardrails.output_guard import _get_analyzer, _get_anonymizer  # noqa: PLC0415
        analyzer = _get_analyzer()
        anonymizer = _get_anonymizer()
        results = analyzer.analyze(text=truncated, language="en")
        if results:
            return anonymizer.anonymize(text=truncated, analyzer_results=results).text
    except Exception:
        pass
    return truncated


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

    # Input guardrails (injection → scope → PII)
    guard = check_input(query, user_role)
    if guard.blocked:
        # RC-123: annotate BEFORE raising so the trace captures the block reason
        try:
            import langsmith as _ls
            _rt = _ls.get_current_run_tree()
            if _rt is not None:
                _rt.metadata.update({
                    "guardrail_triggered": True,
                    "guardrail_reason": guard.reason or "guardrail_blocked",
                    "user_role": user_role,
                    "latency_ms": int((time.monotonic() - start_ms) * 1000),
                })
        except Exception:
            pass
        raise GuardBlockedError(
            reason=guard.reason or "guardrail_blocked",
            message=guard.message or "Your query could not be processed.",
        )

    # Build LLM client once (shared with optional rewriter)
    llm = build_chat_model()

    # Structured query routing — bypass semantic search for listing/filtering queries
    if settings.enable_structured_retrieval:
        from app.rag.query_intent import detect_intent, QueryIntent  # noqa: PLC0415
        from app.rag.structured_retriever import StructuredRetriever  # noqa: PLC0415
        _intent = detect_intent(query)
        if _intent.intent == "structured" and _intent.entity is not None:
            try:
                _struct_retriever = StructuredRetriever(
                    client=_get_qdrant(),
                    collection=settings.qdrant_collection,
                )
                chunks = _struct_retriever.retrieve_all(user_role, _intent.entity)
                if chunks:
                    # Structured retrieval succeeded — bypass semantic path
                    logger.info(
                        "Structured retrieval matched: %d chunks for user_role=%s, entity=%s",
                        len(chunks),
                        user_role,
                        _intent.entity,
                    )

                    # Assemble prompt, call LLM, apply output guards
                    template = _cached_prompt()
                    history_window = (session_history or [])[-settings.session_history_max_messages :]
                    prompt = _build_prompt(template, user_role, query, chunks, history_window or None)

                    answer, token_usage = _call_llm_with_retry(llm, prompt)
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

                    # Output guardrails (PII redaction + source boundary enforcement)
                    guard_out = apply_output_guard(answer, sources, user_role)
                    answer = guard_out.answer
                    sources = guard_out.sources

                    result = RagResult(
                        answer=answer,
                        sources=sources,
                        num_chunks=len(chunks),
                        top_score=chunks[0].score if chunks else 0.0,
                        run_id=run_id,
                        tokens_used=token_usage.total_tokens if token_usage else None,
                        input_tokens=token_usage.input_tokens if token_usage else None,
                        output_tokens=token_usage.output_tokens if token_usage else None,
                    )

                    # RC-143/144/145: emit CloudWatch token usage and cost metrics
                    if settings.cloudwatch_metrics_enabled and token_usage is not None:
                        _emit_cloudwatch_metrics(token_usage)

                    # LangSmith trace annotation
                    try:
                        import langsmith as _ls
                        _rt = _ls.get_current_run_tree()
                        if _rt is not None:
                            _rt.metadata.update({
                                "retrieval_mode": "structured",
                                "entity": _intent.entity,
                                "num_chunks": len(chunks),
                                "top_score": result.top_score,
                                "latency_ms": int((time.monotonic() - start_ms) * 1000),
                            })
                    except Exception:
                        pass

                    return result
            except RetrieverUnavailableError:
                # Qdrant unavailable — fall through to semantic path
                logger.warning("Qdrant unavailable during structured retrieval, falling back to semantic")

    # Optional HyDE query rewriting
    effective_query = query
    if settings.enable_query_rewrite:
        from app.rag.rewriter import rewrite_query  # local import — optional feature
        effective_query = rewrite_query(query, llm)

    # Collect all query variants (always includes effective_query)
    # Step-back and multi-query always branch from the *original* question so
    # that HyDE expansion doesn't compound with decomposition unexpectedly.
    query_variants: list[str] = [effective_query]

    if settings.enable_step_back:
        from app.rag.query_transforms import step_back_query  # noqa: PLC0415
        query_variants.append(step_back_query(query, llm))

    if settings.enable_multi_query:
        from app.rag.query_transforms import generate_sub_queries  # noqa: PLC0415
        query_variants.extend(
            generate_sub_queries(query, llm, n=settings.multi_query_count)
        )

    # RBAC-filtered retrieval (may raise RetrieverUnavailableError)
    retriever = RbacRetriever(
        client=_get_qdrant(),
        embedder=get_embedder(),
        collection=settings.qdrant_collection,
    )

    if len(query_variants) == 1:
        chunks = retriever.retrieve(query_variants[0], user_role)
    else:
        from app.rag.query_transforms import deduplicate_chunks  # noqa: PLC0415
        chunk_lists = [retriever.retrieve(q, user_role) for q in query_variants]
        chunks = deduplicate_chunks(chunk_lists)

    # Optional cross-encoder reranking — narrows chunks before prompt assembly
    if settings.enable_reranking:
        from app.rag.reranker import rerank  # noqa: PLC0415
        chunks = rerank(
            effective_query,
            chunks,
            top_n=settings.reranker_top_n,
            min_score=settings.reranker_min_score,
        )
    elif settings.retrieval_dynamic_threshold_enabled:
        # Even without reranking, apply a score threshold if configured (RC-161)
        chunks = [
            c for c in chunks if c.score >= settings.retrieval_score_threshold
        ]
    else:
        chunks = chunks[: settings.retrieval_top_k]

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

    logger.info(
        "Retrieved %s chunks for user_role=%s (top score=%.4f)",
        len(chunks),
        user_role,
        chunks[0].score,
    )

    # Assemble prompt
    template = _cached_prompt()
    history_window = (session_history or [])[-settings.session_history_max_messages :]
    prompt = _build_prompt(template, user_role, query, chunks, history_window or None)

    # LLM call with one retry
    answer, token_usage = _call_llm_with_retry(llm, prompt)
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

    # Output guardrails (PII redaction + source boundary enforcement)
    guard_out = apply_output_guard(answer, sources, user_role)
    answer = guard_out.answer
    sources = guard_out.sources

    result = RagResult(
        answer=answer,
        sources=sources,
        num_chunks=len(chunks),
        top_score=chunks[0].score,
        run_id=run_id,
        tokens_used=token_usage.total_tokens if token_usage else None,
        input_tokens=token_usage.input_tokens if token_usage else None,
        output_tokens=token_usage.output_tokens if token_usage else None,
    )

    # RC-143/144/145: emit CloudWatch token usage and cost metrics
    if settings.cloudwatch_metrics_enabled and token_usage is not None:
        emit_token_metrics(
            role=user_role,
            usage=token_usage,
            cost_per_1k_input=settings.groq_cost_per_1k_input_tokens,
            cost_per_1k_output=settings.groq_cost_per_1k_output_tokens,
            namespace=settings.cloudwatch_namespace,
            aws_region=settings.aws_region,
        )

    # RC-123/124: Annotate LangSmith trace with RAG metadata and chunk excerpts
    try:
        import langsmith
        run_tree = langsmith.get_current_run_tree()
        if run_tree is not None:
            run_tree.metadata.update({
                "user_role": user_role,
                "prompt_version": settings.prompt_version,
                "num_chunks": result.num_chunks,
                "top_score": result.top_score,
                "latency_ms": int((time.monotonic() - start_ms) * 1000),
                "tokens_used": result.tokens_used,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "guardrail_triggered": False,
                "environment": settings.environment,
                # RC-161: surface dynamic threshold mode in the trace so
                # LangSmith dashboards can filter/compare runs with and
                # without threshold-based retrieval.
                "retrieval_dynamic_threshold_enabled": (
                    settings.retrieval_dynamic_threshold_enabled
                ),
                "score_threshold_used": (
                    settings.retrieval_score_threshold
                    if settings.retrieval_dynamic_threshold_enabled
                    else None
                ),
            })
            # RC-124: chunk excerpts — Presidio-anonymized, max 200 chars
            run_tree.metadata["chunk_excerpts"] = [
                {
                    "source": c.source_file,
                    "excerpt": _anonymize_excerpt(c.text),
                    "score": round(c.score, 4),
                }
                for c in chunks
            ]
    except Exception:
        pass  # tracing is best-effort; never fail the user request

    return result


# ---------------------------------------------------------------------------
# Lazy Qdrant client (avoids circular import at module load)
# ---------------------------------------------------------------------------

def _get_qdrant():
    from app.dependencies import get_qdrant_client
    return get_qdrant_client()
