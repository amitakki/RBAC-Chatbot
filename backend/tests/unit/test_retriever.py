"""
Unit tests for app/rag/retriever.py (RC-68).

Verifies that RbacRetriever always applies the RBAC filter in every
Qdrant search request, without requiring a live Qdrant instance.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.rag.retriever import RbacRetriever, RetrieverUnavailableError


def _make_qdrant_result(
    text: str = "Revenue was $9.4 billion.",
    source_file: str = "financial_summary.md",
    doc_id: str = "financial_summary_md_chunk_001",
    allowed_roles: list[str] | None = None,
    score: float = 0.85,
) -> MagicMock:
    """Build a mock ScoredPoint matching the Qdrant response shape."""
    result = MagicMock()
    result.score = score
    result.payload = {
        "text": text,
        "source_file": source_file,
        "doc_id": doc_id,
        "allowed_roles": allowed_roles or ["finance", "executive"],
    }
    return result


def _make_retriever(mock_client: MagicMock, mock_embedder: MagicMock) -> RbacRetriever:
    return RbacRetriever(
        client=mock_client,
        embedder=mock_embedder,
        collection="test_collection",
    )


@pytest.fixture()
def mock_embedder() -> MagicMock:
    emb = MagicMock()
    emb.embed_one.return_value = [0.1] * 384
    return emb


class TestRbacFilterApplied:
    """RC-68: role filter must be present in every search call."""

    def test_filter_applied_for_finance_role(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.search.return_value = [_make_qdrant_result()]
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("What is Q4 revenue?", user_role="finance")

        mock_client.search.assert_called_once()
        call_kwargs = mock_client.search.call_args.kwargs
        query_filter = call_kwargs["query_filter"]

        assert query_filter is not None
        assert len(query_filter.must) == 1
        condition = query_filter.must[0]
        assert condition.key == "allowed_roles"
        assert condition.match.value == "finance"

    def test_filter_applied_for_hr_role(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("What is the notice period?", user_role="hr")

        call_kwargs = mock_client.search.call_args.kwargs
        assert call_kwargs["query_filter"].must[0].match.value == "hr"

    def test_filter_applied_for_marketing_role(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("Campaign results?", user_role="marketing")

        assert (
            mock_client.search.call_args.kwargs["query_filter"].must[0].match.value
            == "marketing"
        )

    def test_filter_applied_for_engineering_role(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("What is the CI pipeline?", user_role="engineering")

        assert (
            mock_client.search.call_args.kwargs["query_filter"].must[0].match.value
            == "engineering"
        )

    def test_filter_applied_for_executive_role(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.search.return_value = [_make_qdrant_result()]
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("Give me a summary of all departments.", user_role="executive")

        assert (
            mock_client.search.call_args.kwargs["query_filter"].must[0].match.value
            == "executive"
        )

    def test_different_roles_produce_different_filter_values(self, mock_embedder):
        for role in ("finance", "hr", "marketing", "engineering", "executive"):
            mock_client = MagicMock()
            mock_client.search.return_value = []
            retriever = _make_retriever(mock_client, mock_embedder)

            retriever.retrieve("test query", user_role=role)

            value = mock_client.search.call_args.kwargs["query_filter"].must[0].match.value
            assert value == role, f"Expected filter value '{role}', got '{value}'"


class TestRetrieverResults:
    def test_returns_retrieved_chunks(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.search.return_value = [_make_qdrant_result(score=0.9)]
        retriever = _make_retriever(mock_client, mock_embedder)

        chunks = retriever.retrieve("revenue?", user_role="finance")

        assert len(chunks) == 1
        assert chunks[0].text == "Revenue was $9.4 billion."
        assert chunks[0].source_file == "financial_summary.md"
        assert chunks[0].score == 0.9

    def test_empty_results_returns_empty_list(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        retriever = _make_retriever(mock_client, mock_embedder)

        chunks = retriever.retrieve("revenue?", user_role="finance")

        assert chunks == []

    def test_embedder_called_with_query(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("What is Q4 revenue?", user_role="finance")

        mock_embedder.embed_one.assert_called_once_with("What is Q4 revenue?")

    def test_collection_name_passed_to_search(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("query", user_role="finance")

        assert mock_client.search.call_args.kwargs["collection_name"] == "test_collection"


class TestRetrieverErrorHandling:
    def test_qdrant_exception_raises_retriever_unavailable(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("connection refused")
        retriever = _make_retriever(mock_client, mock_embedder)

        with pytest.raises(RetrieverUnavailableError):
            retriever.retrieve("test", user_role="finance")

    def test_error_message_includes_original_exception(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.search.side_effect = Exception("timeout after 3s")
        retriever = _make_retriever(mock_client, mock_embedder)

        with pytest.raises(RetrieverUnavailableError, match="timeout after 3s"):
            retriever.retrieve("test", user_role="finance")
