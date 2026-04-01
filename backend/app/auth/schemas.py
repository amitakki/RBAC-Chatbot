"""Pydantic schemas for authentication and user identity (Epic 4)."""

from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str


class UserContext(BaseModel):
    """Verified user identity extracted from a JWT by get_current_user()."""

    user_id: str
    role: str
