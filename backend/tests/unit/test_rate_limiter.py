"""
Unit tests for app/rate_limit/limiter.py (RC-107).

Uses fakeredis — no live Redis process required.

Key requirement (RC-107):
    30 requests succeed; 31st returns False; counter resets after 3600 s.
"""
from __future__ import annotations

import time

import fakeredis
import pytest

from app.rate_limit.limiter import check_and_increment, get_hourly_limit

_USER = "u001"
_WINDOW = 3600
_LIMIT = 30


@pytest.fixture()
def redis():
    """In-process fake Redis instance, reset per test."""
    return fakeredis.FakeRedis()


# ---------------------------------------------------------------------------
# check_and_increment — core sliding window behaviour
# ---------------------------------------------------------------------------

class TestCheckAndIncrement:
    def test_first_request_allowed(self, redis):
        assert check_and_increment(redis, _USER, _WINDOW, _LIMIT) is True

    def test_thirty_requests_all_allowed(self, redis):
        results = [
            check_and_increment(redis, _USER, _WINDOW, _LIMIT)
            for _ in range(30)
        ]
        assert all(results), "All 30 requests within quota must be allowed"

    def test_thirty_first_request_denied(self, redis):
        """RC-107: 31st request within the same window returns False."""
        for _ in range(30):
            check_and_increment(redis, _USER, _WINDOW, _LIMIT)
        result = check_and_increment(redis, _USER, _WINDOW, _LIMIT)
        assert result is False, "31st request must be denied"

    def test_counter_resets_after_window_expires(self, redis, monkeypatch):
        """RC-107: counter resets after 3600 s (simulated via monkeypatch)."""
        # Fill the quota
        for _ in range(_LIMIT):
            check_and_increment(redis, _USER, _WINDOW, _LIMIT)
        assert check_and_increment(redis, _USER, _WINDOW, _LIMIT) is False

        # Advance apparent time by window + 1 second
        original_time = time.time()
        monkeypatch.setattr(
            "app.rate_limit.limiter.time.time",
            lambda: original_time + _WINDOW + 1,
        )

        # The ZREMRANGEBYSCORE prune on the next call removes all old entries
        assert check_and_increment(redis, _USER, _WINDOW, _LIMIT) is True

    def test_different_users_have_independent_counters(self, redis):
        for _ in range(_LIMIT):
            check_and_increment(redis, "user_a", _WINDOW, _LIMIT)
        assert check_and_increment(redis, "user_a", _WINDOW, _LIMIT) is False
        assert check_and_increment(redis, "user_b", _WINDOW, _LIMIT) is True

    def test_different_windows_have_independent_counters(self, redis):
        for _ in range(30):
            check_and_increment(redis, _USER, 3600, 30)
        assert check_and_increment(redis, _USER, 3600, 30) is False
        # Daily window is independent
        assert check_and_increment(redis, _USER, 86400, 100) is True

    def test_key_has_ttl(self, redis):
        check_and_increment(redis, _USER, _WINDOW, _LIMIT)
        key = f"ratelimit:{_USER}:{_WINDOW}"
        ttl = redis.ttl(key)
        assert ttl > 0, "Rate limit key must have a TTL set"
        assert ttl <= _WINDOW + 1


# ---------------------------------------------------------------------------
# get_hourly_limit — per-role configuration (RC-105)
# ---------------------------------------------------------------------------

class TestGetHourlyLimit:
    def test_finance_returns_50(self):
        assert get_hourly_limit("finance") == 50

    def test_engineering_returns_50(self):
        assert get_hourly_limit("engineering") == 50

    def test_executive_returns_100(self):
        assert get_hourly_limit("executive") == 100

    def test_hr_returns_default_30(self):
        assert get_hourly_limit("hr") == 30

    def test_marketing_returns_default_30(self):
        assert get_hourly_limit("marketing") == 30

    def test_unknown_role_returns_default_30(self):
        assert get_hourly_limit("unknown_role") == 30
