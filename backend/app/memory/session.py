"""Redis-backed session memory (RC-100, RC-101).

Key schema : session:{session_id}
Structure  : Redis LIST — each element is a JSON-encoded ConversationTurn dict
Window     : Last 12 entries (6 human+assistant pairs) kept via LTRIM
TTL        : jwt_expiry_hours × 3600 seconds (default 28800 = 8 h)
"""
from __future__ import annotations

import json

import redis as redis_lib

from app.config import settings
from app.memory.models import ConversationTurn

_TTL_SECONDS: int = settings.jwt_expiry_hours * 3600   # 28800 by default
_MAX_ENTRIES: int = 12   # 6 message pairs × 2 roles


def save_turn(
    r: redis_lib.Redis,
    session_id: str,
    human: str,
    ai: str,
) -> None:
    """Persist one human+AI exchange and trim the list to _MAX_ENTRIES.

    All four Redis operations (2× RPUSH, LTRIM, EXPIRE) are executed in a
    single pipeline — one round-trip regardless of list length.

    Args:
        r:          Active Redis client.  Never created inside this function
                    so that tests can inject fakeredis without patching globals.
        session_id: Opaque session identifier bound to the user's JWT.
        human:      The user's question text.
        ai:         The assistant's answer text.
    """
    key = f"session:{session_id}"
    pipe = r.pipeline()
    pipe.rpush(key, json.dumps(ConversationTurn(role="user", content=human).to_dict()))
    pipe.rpush(key, json.dumps(ConversationTurn(role="assistant", content=ai).to_dict()))
    pipe.ltrim(key, -_MAX_ENTRIES, -1)
    pipe.expire(key, _TTL_SECONDS)
    pipe.execute()


def get_history(
    r: redis_lib.Redis,
    session_id: str,
) -> list[dict[str, str]]:
    """Return all stored turns as plain dicts for use as run_rag(session_history=...).

    Returns an empty list if the session key does not exist or has expired.

    Args:
        r:          Active Redis client.
        session_id: Opaque session identifier.
    """
    key = f"session:{session_id}"
    raw_entries: list[bytes] = r.lrange(key, 0, -1)
    return [json.loads(entry) for entry in raw_entries]
