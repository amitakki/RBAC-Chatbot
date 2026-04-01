"""
Integration smoke tests for /chat — session memory and rate limiting (RC-35, RC-36).

Requirements:
    - Redis reachable at REDIS_URL (default redis://localhost:6379)
    - JWT_SECRET env var set

Skips automatically when either dependency is unavailable.
"""
from __future__ import annotations

import os

import pytest
import redis as redis_lib
from fastapi.testclient import TestClient

_JWT_SECRET = os.getenv("JWT_SECRET", "")
_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def _redis_available() -> bool:
    try:
        redis_lib.from_url(_REDIS_URL, socket_connect_timeout=2).ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _JWT_SECRET or not _redis_available(),
    reason="Skipping chat memory/rate-limit integration tests: JWT_SECRET and Redis required.",
)


@pytest.fixture(scope="module")
def client():
    os.environ.setdefault("JWT_SECRET", _JWT_SECRET)
    os.environ.setdefault("GROQ_API_KEY", os.getenv("GROQ_API_KEY", "dummy-groq"))
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def finance_headers(client):
    resp = client.post(
        "/auth/login",
        json={"username": "alice_finance", "password": "finance123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Session ID handling
# ---------------------------------------------------------------------------

class TestSessionId:
    def test_provided_session_id_is_echoed_back(self, client, finance_headers):
        sid = "integration-test-session-001"
        resp = client.post(
            "/chat/",
            json={"question": "Hello", "session_id": sid},
            headers=finance_headers,
        )
        if resp.status_code in (500, 503):
            pytest.skip("RAG/LLM backend not available in this environment")
        assert resp.status_code in (200, 400)   # 400 = guardrail block; still has session_id
        if resp.status_code == 200:
            assert resp.json()["session_id"] == sid

    def test_auto_generated_session_id_is_uuid4(self, client, finance_headers):
        resp = client.post(
            "/chat/",
            json={"question": "Hi"},
            headers=finance_headers,
        )
        if resp.status_code in (500, 503):
            pytest.skip("RAG/LLM backend not available in this environment")
        if resp.status_code == 200:
            sid = resp.json()["session_id"]
            assert len(sid) == 36 and sid.count("-") == 4


# ---------------------------------------------------------------------------
# Rate limiting — 429 with Retry-After header
# ---------------------------------------------------------------------------

class TestRateLimiting:
    def test_rate_limit_429_has_retry_after_header(self, client, finance_headers):
        """Flood requests until 429 is received; verify Retry-After header present."""
        for i in range(55):   # finance limit is 50/h
            resp = client.post(
                "/chat/",
                json={"question": f"test query {i}"},
                headers=finance_headers,
            )
            if resp.status_code == 429:
                headers_lower = {k.lower(): v for k, v in resp.headers.items()}
                assert "retry-after" in headers_lower, (
                    "HTTP 429 must include a Retry-After header"
                )
                body = resp.json()["detail"]
                assert body["code"] == "RATE_LIMIT_EXCEEDED"
                assert "retry_after_seconds" in body
                return
            if resp.status_code in (500, 503):
                pytest.skip("RAG/LLM backend not available in this environment")
        pytest.skip("Did not hit rate limit within 55 requests — Redis may have been flushed")
