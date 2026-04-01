"""
Unit tests for app/memory/session.py (RC-103).

Uses fakeredis — no live Redis process required.

Key requirement (RC-103):
    save 7 turns → get_history returns only last 6 pairs (12 entries trimmed).
"""
from __future__ import annotations

import fakeredis
import pytest

from app.memory.session import get_history, save_turn

_SESSION = "test-session-rc103"


@pytest.fixture()
def redis():
    """In-process fake Redis instance, reset per test."""
    return fakeredis.FakeRedis()


# ---------------------------------------------------------------------------
# save_turn basic behaviour
# ---------------------------------------------------------------------------

class TestSaveTurn:
    def test_single_turn_creates_two_entries(self, redis):
        save_turn(redis, _SESSION, "hello", "hi there")
        history = get_history(redis, _SESSION)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "hello"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "hi there"

    def test_turn_timestamps_are_present(self, redis):
        save_turn(redis, _SESSION, "what time?", "now")
        history = get_history(redis, _SESSION)
        assert "timestamp" in history[0]
        assert "timestamp" in history[1]

    def test_key_ttl_is_set(self, redis):
        save_turn(redis, _SESSION, "q", "a")
        ttl = redis.ttl(f"session:{_SESSION}")
        # TTL should be 28800 (8 h); allow ±5 s for test execution
        assert 28795 <= ttl <= 28800

    def test_save_is_additive(self, redis):
        save_turn(redis, _SESSION, "q1", "a1")
        save_turn(redis, _SESSION, "q2", "a2")
        history = get_history(redis, _SESSION)
        assert len(history) == 4


# ---------------------------------------------------------------------------
# get_history on missing key
# ---------------------------------------------------------------------------

class TestGetHistoryEmpty:
    def test_nonexistent_session_returns_empty_list(self, redis):
        result = get_history(redis, "no-such-session")
        assert result == []


# ---------------------------------------------------------------------------
# RC-103 — sliding window trim
# ---------------------------------------------------------------------------

class TestHistoryWindowTrim:
    """RC-103: save 7 turns → get_history returns only last 6 pairs (12 entries)."""

    def test_seven_turns_trimmed_to_six_pairs(self, redis):
        for i in range(1, 8):
            save_turn(redis, _SESSION, f"question_{i}", f"answer_{i}")

        history = get_history(redis, _SESSION)
        assert len(history) == 12, (
            f"Expected 12 entries (6 pairs), got {len(history)}"
        )

    def test_trim_drops_oldest_pair(self, redis):
        for i in range(1, 8):
            save_turn(redis, _SESSION, f"question_{i}", f"answer_{i}")

        history = get_history(redis, _SESSION)
        contents = [h["content"] for h in history]

        # Oldest pair must be gone
        assert "question_1" not in contents
        assert "answer_1" not in contents

        # Most recent pair must be present
        assert "question_7" in contents
        assert "answer_7" in contents

    def test_trim_preserves_alternating_order(self, redis):
        for i in range(1, 8):
            save_turn(redis, _SESSION, f"question_{i}", f"answer_{i}")

        history = get_history(redis, _SESSION)
        for idx, turn in enumerate(history):
            expected_role = "user" if idx % 2 == 0 else "assistant"
            assert turn["role"] == expected_role, (
                f"index {idx}: expected '{expected_role}', got '{turn['role']}'"
            )

    def test_exactly_six_pairs_not_trimmed(self, redis):
        for i in range(1, 7):
            save_turn(redis, _SESSION, f"question_{i}", f"answer_{i}")

        history = get_history(redis, _SESSION)
        assert len(history) == 12  # no trim needed for exactly 6 pairs

    def test_ttl_refreshed_on_each_save(self, redis):
        save_turn(redis, _SESSION, "first", "resp1")
        ttl_first = redis.ttl(f"session:{_SESSION}")
        save_turn(redis, _SESSION, "second", "resp2")
        ttl_second = redis.ttl(f"session:{_SESSION}")
        # Second TTL should be within 2 seconds of the first (both near 28800)
        assert abs(ttl_second - ttl_first) <= 2
