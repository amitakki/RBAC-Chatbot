"""
Optional cross-encoder reranker for RAG retrieval results.

Enabled via ENABLE_RERANKING=true. When active, the pipeline passes the
retrieved chunks through a CrossEncoder model that jointly scores (query, chunk)
pairs, then keeps only the top RERANKER_TOP_N chunks before prompt assembly.

The CrossEncoder singleton is loaded once per process (lazy, on first use).
"""

from __future__ import annotations

import logging
import os

from app.config import settings
from app.rag.retriever import RetrievedChunk

logger = logging.getLogger(__name__)

# Windows: prevent CUDA DLL scan hang (same pattern as ingest/embedder.py)
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

_cross_encoder = None  # module-level singleton


def get_cross_encoder():
    """Return the process-wide CrossEncoder singleton (lazy-initialised)."""
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder  # noqa: PLC0415
        logger.info(
            "Loading cross-encoder model '%s'. First run may download from Hugging Face.",
            settings.reranker_model,
        )
        _cross_encoder = CrossEncoder(settings.reranker_model)
        logger.info("Cross-encoder model '%s' ready.", settings.reranker_model)
    return _cross_encoder


def rerank(
    query: str,
    chunks: list[RetrievedChunk],
    top_n: int,
    min_score: float | None = None,
) -> list[RetrievedChunk]:
    """Rerank *chunks* against *query* using a cross-encoder, return top *top_n*.

    Args:
        query:  The user's effective query (after any HyDE rewriting).
        chunks: Retrieved chunks from Qdrant (already RBAC-filtered).
        top_n:  Maximum number of chunks to return after reranking.
        min_score: Optional cross-encoder logit floor; None = count-only cutoff.

    Returns:
        A new list of at most *top_n* RetrievedChunk objects, ordered by
        cross-encoder score descending. The original ``score`` field (cosine
        similarity from Qdrant) is overwritten with the cross-encoder logit
        so that downstream code (top_score, LangSmith metadata) reflects the
        reranked relevance.

    Notes:
        - Degrades gracefully: on any exception the original *chunks* are
          returned truncated to *top_n*, so the pipeline never fails.
        - The cross-encoder scores are raw logits, not probabilities; they are
          valid for ranking but should not be compared directly to Qdrant cosine
          scores. A typical reranker_min_score of 0.0 separates clear positives
          from negatives.
    """
    if not chunks:
        return chunks

    try:
        model = get_cross_encoder()
        pairs = [(query, chunk.text) for chunk in chunks]
        scores: list[float] = model.predict(pairs).tolist()

        scored = sorted(
            zip(scores, chunks),
            key=lambda x: x[0],
            reverse=True,
        )

        result = []
        for score, chunk in scored:
            if min_score is not None and score < min_score:
                break
            result.append(
                RetrievedChunk(
                    text=chunk.text,
                    source_file=chunk.source_file,
                    score=score,
                    doc_id=chunk.doc_id,
                )
            )
            if len(result) >= top_n:
                break

        logger.debug(
            "Reranker: %d chunks → top %d; top score %.4f",
            len(chunks), len(result), result[0].score if result else 0.0,
        )
        return result

    except Exception:
        logger.exception(
            "Cross-encoder reranking failed; falling back to original retrieval order."
        )
        return chunks[:top_n]
