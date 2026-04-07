"""
Unit tests for app/rag/reranker.py.

All tests mock the CrossEncoder so no model is downloaded.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.rag.retriever import RetrievedChunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_chunk(text: str, score: float = 0.8, doc_id: str = "doc1") -> RetrievedChunk:
    return RetrievedChunk(
        text=text,
        source_file="test.md",
        score=score,
        doc_id=doc_id,
    )


# ---------------------------------------------------------------------------
# get_cross_encoder() — singleton behaviour
# ---------------------------------------------------------------------------

class TestGetCrossEncoder:
    def setup_method(self):
        import app.rag.reranker as mod
        mod._cross_encoder = None

    def teardown_method(self):
        import app.rag.reranker as mod
        mod._cross_encoder = None

    def test_model_loaded_once_across_calls(self):
        """get_cross_encoder() must not reload the model on repeated calls."""
        mock_model = MagicMock()
        with patch("sentence_transformers.CrossEncoder", return_value=mock_model) as mock_cls:
            from app.rag.reranker import get_cross_encoder
            result1 = get_cross_encoder()
            result2 = get_cross_encoder()

        mock_cls.assert_called_once()
        assert result1 is result2


# ---------------------------------------------------------------------------
# rerank() — core behaviour
# ---------------------------------------------------------------------------

class TestRerank:
    def setup_method(self):
        import app.rag.reranker as mod
        mod._cross_encoder = None

    def teardown_method(self):
        import app.rag.reranker as mod
        mod._cross_encoder = None

    def _set_mock_model(self, scores: list[float]) -> None:
        import app.rag.reranker as mod
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array(scores)
        mod._cross_encoder = mock_model

    def test_returns_top_n_chunks(self):
        """Only top_n chunks are returned."""
        chunks = [_make_chunk(f"text {i}", doc_id=f"doc{i}") for i in range(5)]
        self._set_mock_model([0.1, 0.9, 0.5, 0.8, 0.2])

        from app.rag.reranker import rerank
        result = rerank("what is revenue?", chunks, top_n=2)

        assert len(result) == 2

    def test_reranked_order_is_score_descending(self):
        """Chunks come back in descending cross-encoder score order."""
        chunks = [
            _make_chunk("low relevance", doc_id="doc0"),
            _make_chunk("high relevance", doc_id="doc1"),
        ]
        self._set_mock_model([0.1, 0.9])

        from app.rag.reranker import rerank
        result = rerank("query", chunks, top_n=2)

        assert result[0].text == "high relevance"
        assert result[1].text == "low relevance"

    def test_score_field_updated_to_cross_encoder_logit(self):
        """RetrievedChunk.score is replaced with the cross-encoder score."""
        chunks = [_make_chunk("text", score=0.55, doc_id="doc0")]
        self._set_mock_model([3.14])

        from app.rag.reranker import rerank
        result = rerank("query", chunks, top_n=1)

        assert abs(result[0].score - 3.14) < 1e-6

    def test_empty_chunks_returns_empty(self):
        """No model call, no crash on empty input."""
        import app.rag.reranker as mod
        mod._cross_encoder = MagicMock()

        from app.rag.reranker import rerank
        result = rerank("query", [], top_n=3)

        assert result == []
        mod._cross_encoder.predict.assert_not_called()

    def test_fewer_chunks_than_top_n_returns_all(self):
        """When fewer chunks exist than top_n, all are returned."""
        chunks = [_make_chunk("only chunk", doc_id="doc0")]
        self._set_mock_model([2.5])

        from app.rag.reranker import rerank
        result = rerank("query", chunks, top_n=5)

        assert len(result) == 1

    def test_original_metadata_preserved(self):
        """source_file and doc_id survive reranking."""
        chunk = _make_chunk("text", doc_id="unique-doc-id")
        chunk.source_file = "finance_report.md"
        self._set_mock_model([1.0])

        from app.rag.reranker import rerank
        result = rerank("query", [chunk], top_n=1)

        assert result[0].source_file == "finance_report.md"
        assert result[0].doc_id == "unique-doc-id"


# ---------------------------------------------------------------------------
# rerank() — graceful degradation
# ---------------------------------------------------------------------------

class TestRerankFallback:
    def setup_method(self):
        import app.rag.reranker as mod
        mod._cross_encoder = None

    def teardown_method(self):
        import app.rag.reranker as mod
        mod._cross_encoder = None

    def test_model_predict_exception_returns_original_chunks_truncated(self):
        """On any cross-encoder error, original chunks are returned up to top_n."""
        import app.rag.reranker as mod
        mock_model = MagicMock()
        mock_model.predict.side_effect = RuntimeError("model inference failed")
        mod._cross_encoder = mock_model

        chunks = [_make_chunk(f"text {i}", doc_id=f"doc{i}") for i in range(5)]

        from app.rag.reranker import rerank
        result = rerank("query", chunks, top_n=3)

        assert len(result) == 3
        assert result[0].text == "text 0"
