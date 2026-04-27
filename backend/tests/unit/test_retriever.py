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


def _make_query_response(*results: MagicMock) -> MagicMock:
    response = MagicMock()
    response.points = list(results)
    return response


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
        mock_client.query_points.return_value = _make_query_response(_make_qdrant_result())
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("What is Q4 revenue?", user_role="finance")

        mock_client.query_points.assert_called_once()
        call_kwargs = mock_client.query_points.call_args.kwargs
        query_filter = call_kwargs["query_filter"]

        assert query_filter is not None
        assert len(query_filter.must) == 1
        condition = query_filter.must[0]
        assert condition.key == "allowed_roles"
        assert condition.match.value == "finance"

    def test_filter_applied_for_hr_role(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response()
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("What is the notice period?", user_role="hr")

        call_kwargs = mock_client.query_points.call_args.kwargs
        assert call_kwargs["query_filter"].must[0].match.value == "hr"

    def test_filter_applied_for_marketing_role(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response()
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("Campaign results?", user_role="marketing")

        assert (
            mock_client.query_points.call_args.kwargs["query_filter"].must[0].match.value
            == "marketing"
        )

    def test_filter_applied_for_engineering_role(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response()
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("What is the CI pipeline?", user_role="engineering")

        assert (
            mock_client.query_points.call_args.kwargs["query_filter"].must[0].match.value
            == "engineering"
        )

    def test_filter_applied_for_executive_role(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response(_make_qdrant_result())
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("Give me a summary of all departments.", user_role="executive")

        assert (
            mock_client.query_points.call_args.kwargs["query_filter"].must[0].match.value
            == "executive"
        )

    def test_different_roles_produce_different_filter_values(self, mock_embedder):
        for role in ("finance", "hr", "marketing", "engineering", "executive"):
            mock_client = MagicMock()
            mock_client.query_points.return_value = _make_query_response()
            retriever = _make_retriever(mock_client, mock_embedder)

            retriever.retrieve("test query", user_role=role)

            value = mock_client.query_points.call_args.kwargs["query_filter"].must[0].match.value
            assert value == role, f"Expected filter value '{role}', got '{value}'"


class TestRetrieverResults:
    def test_returns_retrieved_chunks(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response(
            _make_qdrant_result(score=0.9)
        )
        retriever = _make_retriever(mock_client, mock_embedder)

        chunks = retriever.retrieve("revenue?", user_role="finance")

        assert len(chunks) == 1
        assert chunks[0].text == "Revenue was $9.4 billion."
        assert chunks[0].source_file == "financial_summary.md"
        assert chunks[0].score == 0.9

    def test_empty_results_returns_empty_list(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response()
        retriever = _make_retriever(mock_client, mock_embedder)

        chunks = retriever.retrieve("revenue?", user_role="finance")

        assert chunks == []

    def test_embedder_called_with_query(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response()
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("What is Q4 revenue?", user_role="finance")

        mock_embedder.embed_one.assert_called_once_with("What is Q4 revenue?")

    def test_collection_name_passed_to_query(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response()
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("query", user_role="finance")

        assert mock_client.query_points.call_args.kwargs["collection_name"] == "test_collection"


class TestRetrieverErrorHandling:
    def test_qdrant_exception_raises_retriever_unavailable(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.query_points.side_effect = Exception("connection refused")
        retriever = _make_retriever(mock_client, mock_embedder)

        with pytest.raises(RetrieverUnavailableError):
            retriever.retrieve("test", user_role="finance")

    def test_error_message_includes_original_exception(self, mock_embedder):
        mock_client = MagicMock()
        mock_client.query_points.side_effect = Exception("timeout after 3s")
        retriever = _make_retriever(mock_client, mock_embedder)

        with pytest.raises(RetrieverUnavailableError, match="timeout after 3s"):
            retriever.retrieve("test", user_role="finance")


class TestHybridRetrieval:
    """Test hybrid BM25 + dense retrieval when enable_hybrid_search=True."""

    def test_hybrid_uses_prefetch_list(self, mock_embedder, monkeypatch):
        """When hybrid enabled, query_points called with prefetch list."""
        from qdrant_client.models import Prefetch

        monkeypatch.setattr("app.rag.retriever.settings.enable_hybrid_search", True)
        monkeypatch.setattr(
            "app.rag.retriever.settings.hybrid_prefetch_limit_multiplier", 2
        )
        # Patch the lazy import target directly
        monkeypatch.setattr(
            "app.rag.bm25_embedder.embed_sparse_one",
            lambda text: ([1, 2, 3], [0.5, 0.3, 0.2]),
        )
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response(_make_qdrant_result())
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("Q4 revenue?", user_role="finance")

        kwargs = mock_client.query_points.call_args.kwargs
        assert "prefetch" in kwargs
        assert len(kwargs["prefetch"]) == 2
        assert all(isinstance(p, Prefetch) for p in kwargs["prefetch"])

    def test_hybrid_rbac_filter_in_both_prefetch_arms(self, mock_embedder, monkeypatch):
        """Both Prefetch arms must include the RBAC role filter."""
        monkeypatch.setattr("app.rag.retriever.settings.enable_hybrid_search", True)
        monkeypatch.setattr(
            "app.rag.retriever.settings.hybrid_prefetch_limit_multiplier", 2
        )
        monkeypatch.setattr(
            "app.rag.bm25_embedder.embed_sparse_one",
            lambda text: ([10], [1.0]),
        )
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response()
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("budget?", user_role="finance")

        prefetch = mock_client.query_points.call_args.kwargs["prefetch"]
        for arm in prefetch:
            assert arm.filter is not None
            assert arm.filter.must[0].match.value == "finance"

    def test_hybrid_no_score_threshold(self, mock_embedder, monkeypatch):
        """Hybrid path must not pass score_threshold (incompatible with RRF)."""
        monkeypatch.setattr("app.rag.retriever.settings.enable_hybrid_search", True)
        monkeypatch.setattr(
            "app.rag.retriever.settings.hybrid_prefetch_limit_multiplier", 2
        )
        monkeypatch.setattr(
            "app.rag.bm25_embedder.embed_sparse_one",
            lambda text: ([0], [1.0]),
        )
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response()
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("test?", user_role="hr")

        kwargs = mock_client.query_points.call_args.kwargs
        assert "score_threshold" not in kwargs or kwargs.get("score_threshold") is None

    def test_hybrid_fusion_rrf_query(self, mock_embedder, monkeypatch):
        """Top-level query must be FusionQuery(Fusion.RRF)."""
        from qdrant_client.models import Fusion, FusionQuery

        monkeypatch.setattr("app.rag.retriever.settings.enable_hybrid_search", True)
        monkeypatch.setattr(
            "app.rag.retriever.settings.hybrid_prefetch_limit_multiplier", 2
        )
        monkeypatch.setattr(
            "app.rag.bm25_embedder.embed_sparse_one",
            lambda text: ([5], [0.8]),
        )
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response()
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("test?", user_role="executive")

        kwargs = mock_client.query_points.call_args.kwargs
        assert isinstance(kwargs["query"], FusionQuery)
        assert kwargs["query"].fusion == Fusion.RRF

    def test_hybrid_with_payload_true(self, mock_embedder, monkeypatch):
        """Hybrid path must request payload explicitly."""
        monkeypatch.setattr("app.rag.retriever.settings.enable_hybrid_search", True)
        monkeypatch.setattr(
            "app.rag.retriever.settings.hybrid_prefetch_limit_multiplier", 2
        )
        monkeypatch.setattr(
            "app.rag.bm25_embedder.embed_sparse_one",
            lambda text: ([1], [1.0]),
        )
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response()
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("test?", user_role="marketing")

        kwargs = mock_client.query_points.call_args.kwargs
        assert kwargs.get("with_payload") is True


class TestHybridFlagOff:
    """Test that dense-only path is used when enable_hybrid_search=False."""

    def test_dense_path_has_no_prefetch(self, mock_embedder, monkeypatch):
        """Dense-only path must not use prefetch."""
        monkeypatch.setattr("app.rag.retriever.settings.enable_hybrid_search", False)
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response(_make_qdrant_result())
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("test?", user_role="finance")

        kwargs = mock_client.query_points.call_args.kwargs
        assert "prefetch" not in kwargs

    def test_dense_path_has_score_threshold(self, mock_embedder, monkeypatch):
        """Dense-only path must include score_threshold."""
        monkeypatch.setattr("app.rag.retriever.settings.enable_hybrid_search", False)
        mock_client = MagicMock()
        mock_client.query_points.return_value = _make_query_response()
        retriever = _make_retriever(mock_client, mock_embedder)

        retriever.retrieve("test?", user_role="hr")

        kwargs = mock_client.query_points.call_args.kwargs
        assert "score_threshold" in kwargs
        assert kwargs["score_threshold"] == 0.55  # default threshold
