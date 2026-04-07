"""
Health and readiness endpoints (RC-26).

GET /health — liveness probe (instant 200, no downstream checks).
GET /ready  — readiness probe: checks Qdrant, Redis, and the embedding model.
              Returns 200 if all dependencies are reachable, 503 otherwise.
"""

from __future__ import annotations

from datetime import datetime, timezone

import redis as redis_lib
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings
from app.dependencies import QdrantDep
from app.rag.embedder import get_embedder

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict:
    """Always returns 200. Used by the load balancer to detect crashed containers."""
    return {"status": "ok"}


@router.get("/ready", summary="Readiness probe")
async def ready(qdrant: QdrantDep) -> JSONResponse:
    """Check all downstream dependencies and return 200 or 503.

    Checks:
    - **qdrant**: calls ``get_collections()`` on the injected client.
    - **redis**: creates a short-lived connection and calls ``ping()``.
    - **embedding_model**: calls ``embed_one("ping")`` to verify the model loads.
    """
    checks: dict[str, str] = {}

    # Qdrant
    try:
        qdrant.get_collections()
        checks["qdrant"] = "ok"
    except Exception:
        checks["qdrant"] = "unreachable"

    # Redis
    try:
        r = redis_lib.from_url(
            settings.redis_url,
            socket_connect_timeout=settings.health_redis_timeout_seconds,
        )
        r.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "unreachable"

    # Embedding model
    try:
        get_embedder().embed_one("ping")
        checks["embedding_model"] = "ok"
    except Exception:
        checks["embedding_model"] = "unavailable"

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        content={
            "status": "ready" if all_ok else "not_ready",
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        status_code=status_code,
    )
