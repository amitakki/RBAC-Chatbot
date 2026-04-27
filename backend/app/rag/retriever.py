"""
Qdrant retriever with RBAC filtering (RC-66, RC-67).

Embeds a query and searches the vector store, restricting results to chunks
whose `allowed_roles` payload field contains the requesting user's role.
"""

from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    Prefetch,
    SparseVector,
)

from app.config import settings
from ingest.embedder import Embedder


def _apply_threshold_filter(
    chunks: list["RetrievedChunk"],
    threshold: float,
    min_chunks: int,
    max_chunks: int,
) -> list["RetrievedChunk"]:
    """Post-retrieval score filter with floor/ceiling guards.

    Used by both dense and hybrid paths when
    retrieval_dynamic_threshold_enabled=True. Qdrant's score_threshold
    handles the upper cut on dense search, but hybrid/RRF cannot use it as
    a kwarg — so Python filtering is the only option for hybrid.

    Args:
        chunks: Candidates sorted by score descending (as returned by Qdrant).
        threshold: Minimum acceptable score (maps to retrieval_score_threshold).
        min_chunks: Floor — return at least this many even if all are below
            threshold.
        max_chunks: Ceiling — never return more than this many.

    Returns:
        Filtered, bounded chunk list sorted by score descending.
    """
    filtered = [c for c in chunks if c.score >= threshold]
    # Floor guard: if strict threshold drops everything, keep the best
    # min_chunks available so the pipeline always has *something* to work with.
    if len(filtered) < min_chunks:
        filtered = chunks[:min_chunks]
    return filtered[:max_chunks]


@dataclass
class RetrievedChunk:
    text: str
    source_file: str
    score: float
    doc_id: str


class RetrieverUnavailableError(RuntimeError):
    """Raised when Qdrant is unreachable or returns an unexpected error."""


class RbacRetriever:
    """Retrieves chunks from Qdrant filtered to a specific user role."""

    def __init__(
        self,
        client: QdrantClient,
        embedder: Embedder,
        collection: str,
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._collection = collection

    def retrieve(self, query: str, user_role: str) -> list[RetrievedChunk]:
        """Embed *query* and return top-k chunks accessible to *user_role*.

        Applies a Qdrant `must` filter on ``allowed_roles`` so that only
        chunks whose metadata includes *user_role* are returned.

        Args:
            query: The user's natural-language question.
            user_role: The authenticated user's role (e.g. "finance").

        Returns:
            Ordered list of :class:`RetrievedChunk` with score ≥ threshold.

        Raises:
            RetrieverUnavailableError: If Qdrant cannot be reached.
        """
        vector = self._embedder.embed_one(query)

        # RC-67: RBAC filter — allowed_roles must contain the user's role
        role_filter = Filter(
            must=[
                FieldCondition(
                    key="allowed_roles",
                    match=MatchValue(value=user_role),
                )
            ]
        )

        try:
            if settings.enable_hybrid_search:
                from app.rag.bm25_embedder import embed_sparse_one  # noqa: PLC0415
                indices, values = embed_sparse_one(query)
                sparse_vec = SparseVector(indices=indices, values=values)
                prefetch_limit = (
                    settings.retrieval_top_k * settings.hybrid_prefetch_limit_multiplier
                )
                response = self._client.query_points(
                    collection_name=self._collection,
                    prefetch=[
                        Prefetch(
                            query=vector,
                            using=None,  # unnamed dense vector
                            filter=role_filter,
                            limit=prefetch_limit,
                        ),
                        Prefetch(
                            query=sparse_vec,
                            using="bm25",
                            filter=role_filter,
                            limit=prefetch_limit,
                        ),
                    ],
                    query=FusionQuery(fusion=Fusion.RRF),
                    limit=settings.retrieval_top_k,
                    with_payload=True,
                    # score_threshold omitted — incompatible with FusionQuery
                )
            else:
                # Dynamic mode over-fetches up to max_chunks so Qdrant's
                # score_threshold can return a variable number; static mode
                # keeps the original fixed top_k behaviour.
                fetch_limit = (
                    settings.retrieval_max_chunks
                    if settings.retrieval_dynamic_threshold_enabled
                    else settings.retrieval_top_k
                )
                response = self._client.query_points(
                    collection_name=self._collection,
                    query=vector,
                    query_filter=role_filter,
                    limit=fetch_limit,
                    score_threshold=settings.retrieval_score_threshold,
                )
            results = response.points
        except (UnexpectedResponse, Exception) as exc:
            raise RetrieverUnavailableError(
                f"Qdrant search failed: {exc}"
            ) from exc

        chunks = [
            RetrievedChunk(
                text=r.payload.get("text", ""),
                source_file=r.payload.get("source_file", ""),
                score=r.score,
                doc_id=r.payload.get("doc_id", ""),
            )
            for r in results
        ]

        if settings.retrieval_dynamic_threshold_enabled:
            # Qdrant already filtered by score_threshold; the Python call
            # enforces min_chunks (floor guard) and max_chunks (ceiling cap).
            chunks = _apply_threshold_filter(
                chunks,
                settings.retrieval_score_threshold,
                settings.retrieval_min_chunks,
                settings.retrieval_max_chunks,
            )

        return chunks
