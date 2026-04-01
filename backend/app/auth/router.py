"""
Auth router — POST /auth/login (RC-74).

Returns a signed JWT on valid credentials; 401 on bad username or password.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.auth.schemas import LoginRequest, LoginResponse
from app.auth.service import authenticate_user, create_jwt
from app.config import settings

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=LoginResponse, summary="Obtain a JWT access token")
def login(body: LoginRequest) -> LoginResponse:
    """Authenticate with username + password and return a Bearer JWT.

    The token carries ``sub`` (user_id) and ``role`` claims and expires after
    ``jwt_expiry_hours`` hours (default 8).
    """
    user = authenticate_user(body.username, body.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_jwt(user.user_id, user.role)
    return LoginResponse(
        access_token=token,
        expires_in=settings.jwt_expiry_hours * 3600,
        role=user.role,
    )
