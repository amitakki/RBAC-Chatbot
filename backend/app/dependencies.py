"""
Shared FastAPI dependency providers.
"""
# Component ownership:
# - get_current_user   : Epic 4 (RBAC & Auth)      ← implemented here
# - get_qdrant_client  : Epic 2 (Ingestion) / Epic 3 (RAG)
# - get_redis_client   : Epic 6 (Memory & Rate Limiting)  ← implemented here

from functools import lru_cache
from typing import Annotated

import redis as redis_lib
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from qdrant_client import QdrantClient

from app.auth.schemas import UserContext
from app.auth.service import verify_jwt
from app.config import settings
from ingest.embedder import Embedder

# ---------------------------------------------------------------------------
# Qdrant & Embedder (Epic 2 / 3)
# ---------------------------------------------------------------------------


def get_qdrant_client() -> QdrantClient:
    """Return a QdrantClient configured from settings."""
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def get_embedder_dep() -> Embedder:
    """Return the process-wide Embedder singleton."""
    from app.rag.embedder import get_embedder  # local import avoids circular at module load
    return get_embedder()


QdrantDep = Annotated[QdrantClient, Depends(get_qdrant_client)]
EmbedderDep = Annotated[Embedder, Depends(get_embedder_dep)]

# ---------------------------------------------------------------------------
# Redis (Epic 6)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_redis_client() -> redis_lib.Redis:
    """Return a Redis client configured from settings.

    Uses an lru_cache so the same connection pool is reused across requests.
    decode_responses=False keeps bytes intact for JSON-serialised session entries.
    """
    return redis_lib.from_url(settings.redis_url, decode_responses=False)


RedisDep = Annotated[redis_lib.Redis, Depends(get_redis_client)]

# ---------------------------------------------------------------------------
# JWT auth (Epic 4)
# ---------------------------------------------------------------------------


_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UserContext:
    """Verify the Bearer JWT and return the authenticated UserContext.

    Raises HTTP 401 if the token is missing, malformed, or expired.
    """
    payload = verify_jwt(credentials.credentials)
    return UserContext(user_id=payload["sub"], role=payload["role"])


CurrentUser = Annotated[UserContext, Depends(get_current_user)]
