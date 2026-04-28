"""
Integration tests for POST /auth/login (RC-74, RC-75).

Uses FastAPI's TestClient (httpx).  Does NOT require Qdrant or any external
service — only a JWT_SECRET environment variable.

Skips automatically if JWT_SECRET is not set.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from jose import jwt

_JWT_SECRET = os.getenv("JWT_SECRET", "")

pytestmark = pytest.mark.skipif(
    not _JWT_SECRET,
    reason="Skipping auth integration tests: JWT_SECRET must be set.",
)


@pytest.fixture(scope="module")
def client():
    """Return a TestClient for the FastAPI app."""
    # Ensure env is set before app import so Settings validates
    os.environ.setdefault("JWT_SECRET", _JWT_SECRET)
    if os.getenv("LLM_PROVIDER", "groq").lower() == "ollama":
        os.environ.setdefault("OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "llama3.2"))
    else:
        os.environ.setdefault("GROQ_API_KEY", "dummy-groq")
    from app.main import app
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

class TestLoginSuccess:
    def test_valid_credentials_return_200(self, client):
        resp = client.post("/auth/login", json={"username": "alice_finance", "password": "finance123"})
        assert resp.status_code == 200

    def test_response_contains_access_token(self, client):
        resp = client.post("/auth/login", json={"username": "alice_finance", "password": "finance123"})
        body = resp.json()
        assert "access_token" in body
        assert len(body["access_token"]) > 0

    def test_response_token_type_is_bearer(self, client):
        resp = client.post("/auth/login", json={"username": "bob_hr", "password": "hr123"})
        assert resp.json()["token_type"] == "bearer"

    def test_response_role_matches_user(self, client):
        resp = client.post("/auth/login", json={"username": "charlie_marketing", "password": "marketing123"})
        assert resp.json()["role"] == "marketing"

    def test_response_expires_in_is_28800(self, client):
        resp = client.post("/auth/login", json={"username": "alice_finance", "password": "finance123"})
        assert resp.json()["expires_in"] == 28800

    def test_jwt_payload_contains_correct_sub_and_role(self, client):
        resp = client.post("/auth/login", json={"username": "diana_engineering", "password": "engineering123"})
        token = resp.json()["access_token"]
        payload = jwt.decode(token, _JWT_SECRET, algorithms=["HS256"])
        assert payload["sub"] == "u004"
        assert payload["role"] == "engineering"

    def test_all_five_roles_can_login(self, client):
        credentials = [
            ("alice_finance", "finance123", "finance"),
            ("bob_hr", "hr123", "hr"),
            ("charlie_marketing", "marketing123", "marketing"),
            ("diana_engineering", "engineering123", "engineering"),
            ("eve_executive", "executive123", "executive"),
        ]
        for username, password, expected_role in credentials:
            resp = client.post("/auth/login", json={"username": username, "password": password})
            assert resp.status_code == 200, f"{username} login failed"
            assert resp.json()["role"] == expected_role


# ---------------------------------------------------------------------------
# Failure cases
# ---------------------------------------------------------------------------

class TestLoginFailure:
    def test_wrong_password_returns_401(self, client):
        resp = client.post("/auth/login", json={"username": "alice_finance", "password": "wrong"})
        assert resp.status_code == 401

    def test_unknown_username_returns_401(self, client):
        resp = client.post("/auth/login", json={"username": "nobody", "password": "anything"})
        assert resp.status_code == 401

    def test_error_response_does_not_leak_internals(self, client):
        resp = client.post("/auth/login", json={"username": "alice_finance", "password": "wrong"})
        detail = resp.json().get("detail", "")
        assert "Invalid username or password" in detail
        assert "bcrypt" not in detail.lower()
        assert "traceback" not in detail.lower()
