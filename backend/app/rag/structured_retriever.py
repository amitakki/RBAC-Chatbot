"""Structured query retriever using Qdrant scroll for listing/filtering queries."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from qdrant_client.models import FieldCondition, Filter, MatchValue
from app.rag.retriever import RetrievedChunk, RetrieverUnavailableError

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

# Windows: prevent CUDA DLL scan hang (matching pattern from ingest/embedder.py)
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")


class StructuredRetriever:
    """
    Retriever for structured/listing queries using Qdrant scroll.

    Bypasses semantic search to fetch ALL matching HR records accessible
    to the user, then filters by entity text match.
    """

    def __init__(self, client: QdrantClient, collection: str) -> None:
        """
        Initialize the structured retriever.

        Args:
            client: Qdrant client instance
            collection: Collection name
        """
        self._client = client
        self._collection = collection

    def retrieve_all(
        self,
        user_role: str,
        entity: str | None,
    ) -> list[RetrievedChunk]:
        """
        Retrieve all HR row chunks accessible to user, optionally filtered by entity.

        Uses Qdrant scroll to fetch all chunks from hr_data.csv that:
        1. Match the user's RBAC allowed_roles
        2. Are individual row chunks (not summaries)
        3. Contain the entity value (if entity is provided)

        Args:
            user_role: User's RBAC role (e.g., "hr", "finance")
            entity: Entity to filter by (e.g., "Marketing Manager"), or None for all

        Returns:
            List of RetrievedChunk objects with score=1.0 sentinel

        Raises:
            RetrieverUnavailableError: If Qdrant scroll fails
        """
        try:
            # Build scroll filter: RBAC role + HR data source
            scroll_filter = Filter(
                must=[
                    FieldCondition(
                        key="allowed_roles",
                        match=MatchValue(value=user_role),
                    ),
                    FieldCondition(
                        key="source_file",
                        match=MatchValue(value="hr_data.csv"),
                    ),
                ]
            )

            # Paginate through all matching points
            all_points = []
            offset: int | None = None
            batch_size = 100

            while True:
                points, next_offset = self._client.scroll(
                    collection_name=self._collection,
                    scroll_filter=scroll_filter,
                    limit=batch_size,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                all_points.extend(points)

                if next_offset is None:
                    break
                offset = next_offset

            # Post-filter: exclude summary chunks (keep only row chunks with row_id)
            row_chunks = [
                p for p in all_points
                if p.payload and "row_id" in p.payload
            ]

            # If entity provided, filter by text match
            if entity is not None:
                entity_lower = entity.lower()
                row_chunks = [
                    p for p in row_chunks
                    if entity_lower in p.payload.get("text", "").lower()
                ]

            # Convert to RetrievedChunk with score=1.0 sentinel
            chunks = [
                RetrievedChunk(
                    text=p.payload.get("text", ""),
                    source_file=p.payload.get("source_file", ""),
                    score=1.0,  # Sentinel value for structured retrieval
                    doc_id=p.payload.get("doc_id", ""),
                )
                for p in row_chunks
            ]

            logger.info(
                "Structured retrieval: %d row chunks for user_role=%s, entity=%s",
                len(chunks),
                user_role,
                entity,
            )
            return chunks

        except (Exception,) as exc:
            raise RetrieverUnavailableError(
                f"Qdrant scroll failed: {exc}"
            ) from exc
