"""
Unit tests for structured request logging in app/chat/service.py (RC-126).

Tests verify:
- Success path logs guardrail_outcome="pass" with num_chunks and tokens_used
- GuardBlockedError path logs guardrail_outcome="blocked:<reason>"
- RetrieverUnavailableError path logs guardrail_outcome="retriever_unavailable"
- Unexpected error path logs guardrail_outcome="error"
- latency_ms is a non-negative integer on all paths
"""
from __future__ import annotations

import logging

import fakeredis
import pytest

from app.auth.schemas import UserContext
from app.chat.schemas import ChatRequest
from app.chat.service import handle_chat
from app.guardrails import GuardBlockedError
from app.rag.pipeline import RagResult
from app.rag.retriever import RetrieverUnavailableError

_USER = UserContext(user_id="u1", role="finance")
_SESSION = "test-session-logging"


def _make_request(question: str = "What is Q4 revenue?") -> ChatRequest:
    return ChatRequest(question=question, session_id=_SESSION)


def _make_result(**kwargs) -> RagResult:
    defaults = dict(
        answer="Revenue was $9.4B.",
        sources=["financial_summary.md"],
        num_chunks=3,
        top_score=0.87,
        run_id="run-test-001",
        tokens_used=120,
    )
    defaults.update(kwargs)
    return RagResult(**defaults)


@pytest.fixture()
def fake_redis():
    return fakeredis.FakeRedis()


class TestChatServiceLogging:
    @pytest.mark.asyncio
    async def test_success_path_logs_pass(self, fake_redis, caplog) -> None:
        result = _make_result()
        with (
            pytest.MonkeyPatch().context() as mp,
        ):
            mp.setattr("app.chat.service.check_and_increment", lambda *a, **kw: True)
            mp.setattr("app.chat.service.get_history", lambda *a: [])
            mp.setattr("app.chat.service.save_turn", lambda *a: None)
            mp.setattr("app.chat.service._annotate_langsmith", lambda **kw: None)

            async def _mock_run_rag(*a, **kw):
                return result
            mp.setattr("app.chat.service.asyncio.to_thread", _mock_run_rag)

            with caplog.at_level(logging.INFO, logger="app.chat.service"):
                await handle_chat(_make_request(), _SESSION, _USER, fake_redis)

        record = next(r for r in caplog.records if r.message == "chat_request")
        assert record.__dict__["guardrail_outcome"] == "pass"
        assert record.__dict__["num_chunks"] == 3
        assert record.__dict__["tokens_used"] == 120
        assert record.__dict__["role"] == "finance"
        assert isinstance(record.__dict__["latency_ms"], int)
        assert record.__dict__["latency_ms"] >= 0

    @pytest.mark.asyncio
    async def test_guardrail_blocked_logs_reason(self, fake_redis, caplog) -> None:
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("app.chat.service.check_and_increment", lambda *a, **kw: True)
            mp.setattr("app.chat.service.get_history", lambda *a: [])

            async def _raise_guard(*a, **kw):
                raise GuardBlockedError(reason="pii_bulk_extraction", message="Blocked.")
            mp.setattr("app.chat.service.asyncio.to_thread", _raise_guard)

            with caplog.at_level(logging.INFO, logger="app.chat.service"):
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc_info:
                    await handle_chat(_make_request(), _SESSION, _USER, fake_redis)

        assert exc_info.value.status_code == 400
        record = next(r for r in caplog.records if r.message == "chat_request")
        assert record.__dict__["guardrail_outcome"] == "blocked:pii_bulk_extraction"
        assert record.__dict__["num_chunks"] is None
        assert record.__dict__["tokens_used"] is None

    @pytest.mark.asyncio
    async def test_retriever_unavailable_logs(self, fake_redis, caplog) -> None:
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("app.chat.service.check_and_increment", lambda *a, **kw: True)
            mp.setattr("app.chat.service.get_history", lambda *a: [])

            async def _raise_retriever(*a, **kw):
                raise RetrieverUnavailableError("qdrant down")
            mp.setattr("app.chat.service.asyncio.to_thread", _raise_retriever)

            with caplog.at_level(logging.INFO, logger="app.chat.service"):
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc_info:
                    await handle_chat(_make_request(), _SESSION, _USER, fake_redis)

        assert exc_info.value.status_code == 503
        record = next(r for r in caplog.records if r.message == "chat_request")
        assert record.__dict__["guardrail_outcome"] == "retriever_unavailable"

    @pytest.mark.asyncio
    async def test_unexpected_error_logs_error_outcome(self, fake_redis, caplog) -> None:
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("app.chat.service.check_and_increment", lambda *a, **kw: True)
            mp.setattr("app.chat.service.get_history", lambda *a: [])

            async def _raise_unexpected(*a, **kw):
                raise ValueError("something broke")
            mp.setattr("app.chat.service.asyncio.to_thread", _raise_unexpected)

            with caplog.at_level(logging.INFO, logger="app.chat.service"):
                from fastapi import HTTPException
                with pytest.raises(HTTPException) as exc_info:
                    await handle_chat(_make_request(), _SESSION, _USER, fake_redis)

        assert exc_info.value.status_code == 500
        record = next(r for r in caplog.records if r.message == "chat_request")
        assert record.__dict__["guardrail_outcome"] == "error"

    @pytest.mark.asyncio
    async def test_latency_ms_is_non_negative_int_on_success(self, fake_redis, caplog) -> None:
        result = _make_result(tokens_used=None)
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("app.chat.service.check_and_increment", lambda *a, **kw: True)
            mp.setattr("app.chat.service.get_history", lambda *a: [])
            mp.setattr("app.chat.service.save_turn", lambda *a: None)
            mp.setattr("app.chat.service._annotate_langsmith", lambda **kw: None)

            async def _ok(*a, **kw):
                return result
            mp.setattr("app.chat.service.asyncio.to_thread", _ok)

            with caplog.at_level(logging.INFO, logger="app.chat.service"):
                await handle_chat(_make_request(), _SESSION, _USER, fake_redis)

        record = next(r for r in caplog.records if r.message == "chat_request")
        latency = record.__dict__["latency_ms"]
        assert isinstance(latency, int)
        assert latency >= 0
