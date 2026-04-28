"""
Multi-query and step-back query transformation strategies.

Both are opt-in via environment flags and degrade gracefully — if the LLM
call fails, the original question is returned unchanged so the pipeline
always has at least one query to retrieve with.
"""

from __future__ import annotations

import logging

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from app.rag.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_MULTI_QUERY_TEMPLATE = (
    "You are a search assistant helping retrieve relevant documents.\n"
    "Generate {n} different versions of the following question that approach "
    "the same information need from different angles. These will be used as "
    "separate search queries.\n"
    "Output only the queries, one per line, with no numbering, bullets, or extra text.\n\n"
    "Question: {question}"
)

_STEP_BACK_TEMPLATE = (
    "You are a search assistant. Rewrite the following question as a broader, "
    "more general question that captures the underlying topic or policy area. "
    "This helps retrieve background context that a specific question might miss.\n"
    "Output only the rewritten question, nothing else.\n\n"
    "Original question: {question}\n"
    "Broader question:"
)


# ---------------------------------------------------------------------------
# Transformers
# ---------------------------------------------------------------------------

def generate_sub_queries(question: str, llm: BaseChatModel, n: int = 3) -> list[str]:
    """Return up to *n* sub-queries derived from *question* for multi-query retrieval.

    Falls back to ``[question]`` on any LLM failure so the pipeline always
    has at least one query.

    Args:
        question: The user's original question.
        llm: Shared chat model instance from the pipeline.
        n: Number of sub-queries to generate.

    Returns:
        List of query strings (length ≤ n); never empty.
    """
    try:
        prompt = _MULTI_QUERY_TEMPLATE.format(n=n, question=question)
        response = llm.invoke([HumanMessage(content=prompt)])
        lines = [
            line.strip()
            for line in response.content.strip().splitlines()
            if line.strip()
        ]
        sub_queries = lines[:n]
        if sub_queries:
            logger.debug("Multi-query generated %d sub-queries", len(sub_queries))
            return sub_queries
    except Exception:
        logger.exception("Multi-query generation failed; using original question")
    return [question]


def step_back_query(question: str, llm: BaseChatModel) -> str:
    """Return a broader, step-back version of *question*.

    Falls back to *question* unchanged on any LLM failure.

    Args:
        question: The user's original question.
        llm: Shared chat model instance from the pipeline.

    Returns:
        The rewritten (broader) query string.
    """
    try:
        prompt = _STEP_BACK_TEMPLATE.format(question=question)
        response = llm.invoke([HumanMessage(content=prompt)])
        rewritten = response.content.strip()
        if rewritten:
            logger.debug("Step-back query: %r", rewritten)
            return rewritten
    except Exception:
        logger.exception("Step-back query generation failed; using original question")
    return question


# ---------------------------------------------------------------------------
# Chunk deduplication
# ---------------------------------------------------------------------------

def deduplicate_chunks(
    chunk_lists: list[list[RetrievedChunk]],
) -> list[RetrievedChunk]:
    """Merge multiple retrieval results, keeping the highest score per doc_id.

    Chunks without a ``doc_id`` are kept as-is (de-duped by identity).
    Result is sorted by score descending.

    Args:
        chunk_lists: One list of :class:`RetrievedChunk` per query variant.

    Returns:
        Flat, deduplicated list sorted by score descending.
    """
    best: dict[str, RetrievedChunk] = {}
    fallback: list[RetrievedChunk] = []

    for chunks in chunk_lists:
        for chunk in chunks:
            if not chunk.doc_id:
                fallback.append(chunk)
                continue
            existing = best.get(chunk.doc_id)
            if existing is None or chunk.score > existing.score:
                best[chunk.doc_id] = chunk

    merged = list(best.values()) + fallback
    merged.sort(key=lambda c: c.score, reverse=True)
    return merged
