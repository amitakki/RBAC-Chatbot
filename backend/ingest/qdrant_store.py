"""
Qdrant collection management and batch upsert.

Responsibilities:
  - Create or reset the vector collection (cosine, configured dims)
  - Store embedding model version as a special metadata point (id=0)
  - Batch-upsert chunk vectors with full payload
"""

from __future__ import annotations
import uuid
from datetime import datetime, timezone

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PointStruct,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.config import settings

# Version bump this when the embedding model or schema changes
EMBEDDING_MODEL_VERSION = "1.0.0"
SCHEMA_VERSION = "2"  # v2: added sparse vector support for hybrid search

# Number of points per upsert batch
_UPSERT_BATCH = 100
_POINT_ID_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")


def init_collection(
    client: QdrantClient,
    collection_name: str,
    embedding_model: str,
    reset: bool = False,
) -> None:
    """
    Ensure the Qdrant collection exists and is ready for upserts.

    If reset=True the collection is deleted first (full re-ingestion).
    A metadata sentinel point (id=0) stores model version info.
    """
    existing = {c.name for c in client.get_collections().collections}

    if reset and collection_name in existing:
        client.delete_collection(collection_name)
        existing.discard(collection_name)

    if collection_name not in existing:
        sparse_cfg = (
            {"bm25": SparseVectorParams()}
            if settings.enable_hybrid_search
            else None
        )
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.embedding_dims, distance=Distance.COSINE
            ),
            **({"sparse_vectors_config": sparse_cfg} if sparse_cfg else {}),
        )

    # Upsert the metadata sentinel point (zero vector, id=0)
    client.upsert(
        collection_name=collection_name,
        points=[
            PointStruct(
                id=0,
                vector=[0.0] * settings.embedding_dims,
                payload={
                    "_type":                 "collection_metadata",
                    "embedding_model":        embedding_model,
                    "embedding_model_version": EMBEDDING_MODEL_VERSION,
                    "schema_version":         SCHEMA_VERSION,
                    "created_at":             datetime.now(timezone.utc).isoformat(),
                },
            )
        ],
    )


def batch_upsert(
    client: QdrantClient,
    collection_name: str,
    chunks: list[dict],
    vectors: list[list[float]],
    sparse_vectors: list[tuple[list[int], list[float]]] | None = None,
) -> int:
    """Upsert chunks + their vectors into Qdrant.

    Args:
        client: Qdrant client
        collection_name: Collection name
        chunks: List of chunk dicts with metadata and text
        vectors: List of dense vectors (one per chunk)
        sparse_vectors: Optional list of (indices, values) tuples for BM25
                       (one per chunk, or None to skip sparse vectors)

    Returns:
        The number of points upserted.
    """
    points: list[PointStruct] = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        payload = dict(chunk["metadata"])
        payload["text"] = chunk["text"]
        if sparse_vectors is not None:
            indices, values = sparse_vectors[i]
            vec = {"": vector, "bm25": SparseVector(indices=indices, values=values)}
        else:
            vec = vector  # existing path — plain list for unnamed dense vector
        points.append(
            PointStruct(
                id=str(uuid.uuid5(_POINT_ID_NAMESPACE, payload["doc_id"])),
                vector=vec,
                payload=payload,
            )
        )

    for i in range(0, len(points), _UPSERT_BATCH):
        batch = points[i : i + _UPSERT_BATCH]
        client.upsert(collection_name=collection_name, points=batch)

    return len(points)
