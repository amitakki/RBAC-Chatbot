"""BM25 sparse-vector embedder singleton for hybrid search.

Mirrors app/rag/embedder.py and app/rag/reranker.py: one SparseTextEmbedding
instance per process, lazy-loaded on first use. Used only when ENABLE_HYBRID_SEARCH=true.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from fastembed import SparseTextEmbedding

logger = logging.getLogger(__name__)

# Windows: prevent CUDA DLL scan hang (same pattern as reranker.py and ingest/embedder.py)
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

_bm25_embedder: "SparseTextEmbedding | None" = None


def get_bm25_embedder() -> "SparseTextEmbedding":
    """Return the process-wide SparseTextEmbedding singleton (lazy-initialised).

    Raises:
        RuntimeError: if fastembed is not installed or the model cannot be loaded.
    """
    global _bm25_embedder
    if _bm25_embedder is None:
        try:
            from fastembed import SparseTextEmbedding  # noqa: PLC0415
        except ImportError as exc:
            raise RuntimeError(
                "fastembed is required for hybrid search. "
                "Add 'fastembed>=0.4' to pyproject.toml and run 'uv sync'."
            ) from exc

        logger.info(
            "Loading BM25 sparse embedding model '%s'. "
            "First run may download the ONNX model from HuggingFace.",
            settings.bm25_model,
        )
        _bm25_embedder = SparseTextEmbedding(model_name=settings.bm25_model)
        logger.info("BM25 model '%s' ready.", settings.bm25_model)

    return _bm25_embedder


def embed_sparse_one(text: str) -> tuple[list[int], list[float]]:
    """Embed a single query text; returns (indices, values) for SparseVector.

    Args:
        text: The query text to embed.

    Returns:
        A (indices, values) pair ready for ``SparseVector(indices=..., values=...)``.
    """
    model = get_bm25_embedder()
    # fastembed query_embed returns a generator of SparseEmbedding objects
    result = list(model.query_embed(text))[0]
    return result.indices.tolist(), result.values.tolist()


def embed_sparse_batch(texts: list[str]) -> list[tuple[list[int], list[float]]]:
    """Embed a batch of passage texts for ingestion.

    Uses ``passage_embed`` (not ``query_embed``) — fastembed distinguishes
    passage-side and query-side BM25 tokenisation.

    Args:
        texts: List of passage texts to embed.

    Returns:
        List of (indices, values) tuples, one per input text.
    """
    model = get_bm25_embedder()
    results = list(model.passage_embed(texts))
    return [(r.indices.tolist(), r.values.tolist()) for r in results]
