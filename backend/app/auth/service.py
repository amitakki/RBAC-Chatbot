"""
Mock authentication service — static user store + JWT helpers (RC-72, RC-73).

Passwords are bcrypt-hashed at module load.  In production this store would be
backed by a database; for this project a static dict is intentional.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
# pbkdf2_sha256 is used instead of bcrypt because bcrypt 4.x raised a
# ValueError in passlib's internal wrap-bug detection (which sends a >72-byte
# test password).  pbkdf2_sha256 is equally secure and has no length limit.
_pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def _hash(password: str) -> str:
    return _pwd_context.hash(password)


# ---------------------------------------------------------------------------
# Static user store (RC-72)
# ---------------------------------------------------------------------------
@dataclass
class _UserRecord:
    user_id: str
    role: str
    password_hash: str


_USER_STORE: dict[str, _UserRecord] = {
    "alice_finance": _UserRecord(
        user_id="u001", role="finance", password_hash=_hash("finance123")
    ),
    "bob_hr": _UserRecord(
        user_id="u002", role="hr", password_hash=_hash("hr123")
    ),
    "charlie_marketing": _UserRecord(
        user_id="u003", role="marketing", password_hash=_hash("marketing123")
    ),
    "diana_engineering": _UserRecord(
        user_id="u004", role="engineering", password_hash=_hash("engineering123")
    ),
    "eve_executive": _UserRecord(
        user_id="u005", role="executive", password_hash=_hash("executive123")
    ),
}


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def authenticate_user(username: str, password: str) -> _UserRecord | None:
    """Return the user record if credentials are valid, else None."""
    record = _USER_STORE.get(username)
    if record is None:
        return None
    if not _pwd_context.verify(password, record.password_hash):
        return None
    return record


def create_jwt(user_id: str, role: str) -> str:
    """Sign and return an HS256 JWT with an 8-hour expiry (RC-73)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_jwt(token: str) -> dict:
    """Decode and validate a JWT.  Raises HTTP 401 on any failure (RC-73)."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return payload
