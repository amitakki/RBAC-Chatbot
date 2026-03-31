"""
Qdrant retriever with RBAC filtering (RC-66, RC-67).

Embeds a query and searches the vector store, restricting results to chunks
whose `allowed_roles` payload field contains the requesting user's role.
"""

from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.config import settings
from ingest.embedder import Embedder


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
            results = self._client.search(
                collection_name=self._collection,
                query_vector=vector,
                query_filter=role_filter,
                limit=settings.retrieval_top_k,
                score_threshold=settings.retrieval_score_threshold,
            )
        except (UnexpectedResponse, Exception) as exc:
            raise RetrieverUnavailableError(
                f"Qdrant search failed: {exc}"
            ) from exc

        return [
            RetrievedChunk(
                text=r.payload.get("text", ""),
                source_file=r.payload.get("source_file", ""),
                score=r.score,
                doc_id=r.payload.get("doc_id", ""),
            )
            for r in results
        ]
