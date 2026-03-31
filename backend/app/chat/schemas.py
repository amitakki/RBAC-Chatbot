"""Pydantic schemas for the /chat endpoint (RC-25)."""

from __future__ import annotations

from pydantic import BaseModel, field_validator

from app.config import settings


class UserContext(BaseModel):
    """Identifies the authenticated user making the request.

    Populated from the request body in EPIC 3.
    EPIC 4 will replace this with JWT-derived values via get_current_user().
    """

    user_id: str
    role: str


class ChatRequest(BaseModel):
    question: str
    user_context: UserContext
    session_id: str | None = None

    @field_validator("question")
    @classmethod
    def check_length(cls, v: str) -> str:
        stripped = v.strip()
        if len(stripped) > settings.max_query_length_chars:
            raise ValueError(
                f"Question exceeds the {settings.max_query_length_chars}-character limit."
            )
        if not stripped:
            raise ValueError("Question must not be empty.")
        return stripped


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    session_id: str
    run_id: str
