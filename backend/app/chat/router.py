"""
Chat router — POST /chat (RC-25).

Thin HTTP layer over the RAG pipeline. Handles session ID generation,
error mapping, and async wrapping of the synchronous pipeline call.
User identity is derived from the JWT via get_current_user() (Epic 4).
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, HTTPException

from app.chat.schemas import ChatRequest, ChatResponse
from app.dependencies import CurrentUser
from app.rag.pipeline import run_rag
from app.rag.retriever import RetrieverUnavailableError

router = APIRouter(tags=["chat"])


@router.post("/", response_model=ChatResponse, summary="Submit a question to the RAG assistant")
async def chat_endpoint(request: ChatRequest, user_context: CurrentUser) -> ChatResponse:
    """Run the RAG pipeline for the given question and authenticated user.

    - User identity (role) is extracted from the Bearer JWT via CurrentUser.
    - Generates a ``session_id`` if not supplied by the caller.
    - Offloads the synchronous ``run_rag()`` call to a thread to avoid
      blocking the async event loop during embedding and LLM I/O.
    - Maps pipeline errors to appropriate HTTP status codes; never exposes
      raw exception details to the client.
    """
    session_id = request.session_id or str(uuid.uuid4())
    request_id = str(uuid.uuid4())

    try:
        result = await asyncio.to_thread(
            run_rag,
            request.question,
            user_context.role,
        )
    except RetrieverUnavailableError:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "search_unavailable",
                "message": "The search service is temporarily unavailable. Please try again shortly.",
                "request_id": request_id,
            },
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "message": "An unexpected error occurred. Please try again shortly.",
                "request_id": request_id,
            },
        )

    return ChatResponse(
        answer=result.answer,
        sources=result.sources,
        session_id=session_id,
        run_id=result.run_id,
    )
