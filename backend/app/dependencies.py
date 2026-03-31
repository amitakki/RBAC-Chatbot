"""
Shared FastAPI dependency providers.
Implementations are filled in by their respective epics.
"""
# Stubs — each will be implemented in the epic that owns the component:
# - get_current_user   : Epic 4 (RBAC & Auth)
# - get_qdrant_client  : Epic 2 (Ingestion) / Epic 3 (RAG)  ← implemented here
# - get_redis_client   : Epic 6 (Memory & Rate Limiting)

from typing import Annotated

from fastapi import Depends
from qdrant_client import QdrantClient

from app.config import settings


def get_qdrant_client() -> QdrantClient:
    """Return a QdrantClient configured from settings."""
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


QdrantDep = Annotated[QdrantClient, Depends(get_qdrant_client)]
