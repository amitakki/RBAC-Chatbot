"""
Qdrant collection management and batch upsert.

Responsibilities:
  - Create or reset the vector collection (cosine, 384 dims)
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
    VectorParams,
)

from ingest.embedder import EMBEDDING_DIMS

# Version bump this when the embedding model or schema changes
EMBEDDING_MODEL_VERSION = "1.0.0"
SCHEMA_VERSION = "1"

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
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=EMBEDDING_DIMS, distance=Distance.COSINE),
        )

    # Upsert the metadata sentinel point (zero vector, id=0)
    client.upsert(
        collection_name=collection_name,
        points=[
            PointStruct(
                id=0,
                vector=[0.0] * EMBEDDING_DIMS,
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
) -> int:
    """
    Upsert chunks + their vectors into Qdrant.

    Returns the number of points upserted.
    """
    points: list[PointStruct] = []
    for chunk, vector in zip(chunks, vectors):
        payload = dict(chunk["metadata"])
        payload["text"] = chunk["text"]
        points.append(
            PointStruct(
                id=str(uuid.uuid5(_POINT_ID_NAMESPACE, payload["doc_id"])),
                vector=vector,
                payload=payload,
            )
        )

    for i in range(0, len(points), _UPSERT_BATCH):
        batch = points[i : i + _UPSERT_BATCH]
        client.upsert(collection_name=collection_name, points=batch)

    return len(points)
