"""
Chat router — POST /chat (RC-25).

Thin HTTP layer: resolves session_id, injects dependencies, delegates to
chat/service.py for all business logic (rate limiting, memory, RAG).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.chat.schemas import ChatRequest, ChatResponse
from app.chat.service import handle_chat
from app.dependencies import CurrentUser, RedisDep

router = APIRouter(tags=["chat"])


@router.post("/", response_model=ChatResponse, summary="Submit a question to the RAG assistant")
async def chat_endpoint(
    request: ChatRequest,
    user_context: CurrentUser,
    redis: RedisDep,
) -> ChatResponse:
    """Run the RAG pipeline with session memory and rate limiting.

    - User identity (role) is extracted from the Bearer JWT via CurrentUser.
    - Session ID is generated if not supplied by the caller and echoed back.
    - Rate limiting is enforced per-user per-role (hourly and daily windows).
    - Session history is loaded from Redis before calling the RAG pipeline.
    - The human+AI turn is saved to Redis after successful generation.
    """
    session_id = request.session_id or str(uuid.uuid4())
    return await handle_chat(request, session_id, user_context, redis)
