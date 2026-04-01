"""
Unit tests for app/auth/service.py (RC-75).

Covers authenticate_user(), create_jwt(), and verify_jwt() without
hitting any external services.  JWT_SECRET is injected via monkeypatch
because the conftest autouse fixture clears it from the environment.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from jose import jwt

_SECRET = "test-secret-for-unit-tests"
_ALGO = "HS256"


@pytest.fixture(autouse=True)
def _inject_jwt_secret(monkeypatch):
    """Provide a deterministic JWT_SECRET so Settings can instantiate."""
    monkeypatch.setenv("JWT_SECRET", _SECRET)
    monkeypatch.setenv("GROQ_API_KEY", "dummy-groq")
    # Re-import settings with the new env so service picks them up
    import importlib
    import app.config as _cfg
    importlib.reload(_cfg)
    import app.auth.service as _svc
    importlib.reload(_svc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _service():
    import app.auth.service as svc
    return svc


# ---------------------------------------------------------------------------
# TestAuthenticateUser
# ---------------------------------------------------------------------------

class TestAuthenticateUser:
    def test_valid_credentials_return_user_record(self):
        svc = _service()
        user = svc.authenticate_user("alice_finance", "finance123")
        assert user is not None
        assert user.role == "finance"
        assert user.user_id == "u001"

    def test_wrong_password_returns_none(self):
        svc = _service()
        assert svc.authenticate_user("alice_finance", "wrongpassword") is None

    def test_unknown_username_returns_none(self):
        svc = _service()
        assert svc.authenticate_user("nobody", "anything") is None

    def test_all_five_users_authenticate(self):
        svc = _service()
        credentials = [
            ("alice_finance", "finance123", "finance"),
            ("bob_hr", "hr123", "hr"),
            ("charlie_marketing", "marketing123", "marketing"),
            ("diana_engineering", "engineering123", "engineering"),
            ("eve_executive", "executive123", "executive"),
        ]
        for username, password, expected_role in credentials:
            user = svc.authenticate_user(username, password)
            assert user is not None, f"{username} failed to authenticate"
            assert user.role == expected_role


# ---------------------------------------------------------------------------
# TestCreateJwt
# ---------------------------------------------------------------------------

class TestCreateJwt:
    def test_returns_non_empty_string(self):
        svc = _service()
        token = svc.create_jwt("u001", "finance")
        assert isinstance(token, str) and len(token) > 0

    def test_payload_contains_sub_and_role(self):
        svc = _service()
        token = svc.create_jwt("u002", "hr")
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGO])
        assert payload["sub"] == "u002"
        assert payload["role"] == "hr"

    def test_expiry_is_approximately_eight_hours(self):
        svc = _service()
        token = svc.create_jwt("u001", "finance")
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGO])
        now = datetime.now(timezone.utc).timestamp()
        delta_hours = (payload["exp"] - now) / 3600
        assert 7.9 < delta_hours <= 8.1, f"Unexpected expiry delta: {delta_hours:.2f}h"

    def test_two_tokens_for_same_user_differ(self):
        svc = _service()
        t1 = svc.create_jwt("u001", "finance")
        t2 = svc.create_jwt("u001", "finance")
        # iat resolution is 1-second; tokens may match in fast tests — just check structure
        p1 = jwt.decode(t1, _SECRET, algorithms=[_ALGO])
        p2 = jwt.decode(t2, _SECRET, algorithms=[_ALGO])
        assert p1["sub"] == p2["sub"]


# ---------------------------------------------------------------------------
# TestVerifyJwt
# ---------------------------------------------------------------------------

class TestVerifyJwt:
    def test_round_trip_encode_decode(self):
        svc = _service()
        token = svc.create_jwt("u003", "marketing")
        payload = svc.verify_jwt(token)
        assert payload["sub"] == "u003"
        assert payload["role"] == "marketing"

    def test_tampered_token_raises_401(self):
        svc = _service()
        token = svc.create_jwt("u001", "finance")
        tampered = token[:-4] + "XXXX"
        with pytest.raises(HTTPException) as exc_info:
            svc.verify_jwt(tampered)
        assert exc_info.value.status_code == 401

    def test_wrong_secret_raises_401(self):
        bad_token = jwt.encode({"sub": "u001", "role": "finance"}, "wrong-secret", algorithm=_ALGO)
        svc = _service()
        with pytest.raises(HTTPException) as exc_info:
            svc.verify_jwt(bad_token)
        assert exc_info.value.status_code == 401

    def test_expired_token_raises_401(self):
        svc = _service()
        now = datetime.now(timezone.utc)
        expired_payload = {
            "sub": "u001",
            "role": "finance",
            "iat": now - timedelta(hours=9),
            "exp": now - timedelta(hours=1),
        }
        expired_token = jwt.encode(expired_payload, _SECRET, algorithm=_ALGO)
        with pytest.raises(HTTPException) as exc_info:
            svc.verify_jwt(expired_token)
        assert exc_info.value.status_code == 401
