"""Sliding-window rate limiter (RC-104, RC-105, RC-106).

Algorithm : True sliding window via Redis ZSET.
Key schema: ratelimit:{user_id}:{window_seconds}
Members   : str(timestamp) — score equals the same timestamp (float).
            Unique per call because monotonic time has sub-microsecond resolution;
            a UUID suffix guards against theoretical hash collisions at high throughput.

Per-role hourly limits (RC-105):
    finance / engineering : 50 req/h
    executive             : 100 req/h
    all other roles       : settings.rate_limit_default_per_hour (default 30)

Daily limit: settings.rate_limit_default_per_day (default 100) for all roles.
"""
from __future__ import annotations

import time
import uuid

import redis as redis_lib

from app.config import settings

# ---------------------------------------------------------------------------
# Per-role hourly limits (RC-105)
# ---------------------------------------------------------------------------

_ROLE_HOURLY_LIMITS: dict[str, int] = {
    "finance": settings.rate_limit_finance_per_hour,
    "engineering": settings.rate_limit_engineering_per_hour,
    "executive": settings.rate_limit_executive_per_hour,
}


def get_hourly_limit(role: str) -> int:
    """Return the per-hour query limit for *role*.

    Roles not listed in _ROLE_HOURLY_LIMITS fall back to the default from
    settings (30 unless overridden by RATE_LIMIT_DEFAULT_PER_HOUR env var).
    """
    return _ROLE_HOURLY_LIMITS.get(role, settings.rate_limit_default_per_hour)


# ---------------------------------------------------------------------------
# Sliding window counter (RC-104)
# ---------------------------------------------------------------------------

def check_and_increment(
    r: redis_lib.Redis,
    user_id: str,
    window_seconds: int,
    limit: int,
) -> bool:
    """Return True if the request is within quota and increment the counter.

    Implements a true sliding window:
    1. ZREMRANGEBYSCORE — prune entries older than (now - window_seconds).
    2. ZCARD            — count entries remaining in the window.
    3. ZADD             — record the current request.
    4. EXPIRE           — ensure the key self-cleans after the window elapses.

    Steps 1–4 run in a single Redis pipeline (one round-trip).
    The count from step 2 is captured *before* the ZADD of step 3, so the
    comparison is: "how many requests have already been made this window?"

    Args:
        r:              Active Redis client.
        user_id:        Authenticated user identifier (JWT ``sub`` claim).
        window_seconds: Sliding window size in seconds (3600 = hourly, 86400 = daily).
        limit:          Maximum requests allowed within the window.

    Returns:
        True  — request is within quota; counter has been incremented.
        False — quota exceeded; caller should return HTTP 429.
    """
    now = time.time()
    window_start = now - window_seconds
    key = f"ratelimit:{user_id}:{window_seconds}"
    member = f"{now}:{uuid.uuid4().hex}"  # unique member to handle concurrent requests

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, "-inf", window_start)   # 1. prune expired
    pipe.zcard(key)                                     # 2. count (before add)
    pipe.zadd(key, {member: now})                       # 3. record request
    pipe.expire(key, window_seconds + 1)               # 4. TTL
    results = pipe.execute()

    count_before_add: int = results[1]
    return count_before_add < limit
