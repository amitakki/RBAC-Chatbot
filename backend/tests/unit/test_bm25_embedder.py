"""Unit tests for app/rag/bm25_embedder.py.

All tests mock SparseTextEmbedding so no model is downloaded.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


class TestGetBm25Embedder:
    """Test singleton pattern for BM25 embedder."""

    def setup_method(self) -> None:
        import app.rag.bm25_embedder as mod

        mod._bm25_embedder = None

    def teardown_method(self) -> None:
        import app.rag.bm25_embedder as mod

        mod._bm25_embedder = None

    def test_model_loaded_once_across_calls(self) -> None:
        """get_bm25_embedder() must not reload on repeated calls."""
        mock_model = MagicMock()
        mock_cls = MagicMock(return_value=mock_model)
        with patch.dict("sys.modules", {"fastembed": MagicMock(SparseTextEmbedding=mock_cls)}):
            from app.rag.bm25_embedder import get_bm25_embedder

            r1 = get_bm25_embedder()
            r2 = get_bm25_embedder()
        mock_cls.assert_called_once()
        assert r1 is r2

    def test_importerror_raises_runtime_error(self) -> None:
        """Missing fastembed should surface as a clear RuntimeError."""
        import app.rag.bm25_embedder as mod

        mod._bm25_embedder = None
        with patch.dict("sys.modules", {"fastembed": None}):
            with pytest.raises(RuntimeError, match="fastembed is required"):
                from app.rag.bm25_embedder import get_bm25_embedder

                get_bm25_embedder()


class TestEmbedSparseOne:
    """Test single-text sparse embedding."""

    def setup_method(self) -> None:
        import app.rag.bm25_embedder as mod

        mod._bm25_embedder = None

    def teardown_method(self) -> None:
        import app.rag.bm25_embedder as mod

        mod._bm25_embedder = None

    def _inject_mock_model(self, indices: list[int], values: list[float]) -> None:
        """Set a pre-built mock as the module singleton."""
        import numpy as np

        import app.rag.bm25_embedder as mod

        sparse_result = MagicMock()
        sparse_result.indices = np.array(indices)
        sparse_result.values = np.array(values)
        mock_model = MagicMock()
        mock_model.query_embed.return_value = iter([sparse_result])
        mod._bm25_embedder = mock_model

    def test_returns_indices_and_values_lists(self) -> None:
        self._inject_mock_model([1, 42, 100], [0.5, 0.3, 0.8])
        from app.rag.bm25_embedder import embed_sparse_one

        idxs, vals = embed_sparse_one("what is revenue?")
        assert idxs == [1, 42, 100]
        assert vals == pytest.approx([0.5, 0.3, 0.8])

    def test_query_embed_called_with_text(self) -> None:
        self._inject_mock_model([0], [1.0])
        import app.rag.bm25_embedder as mod

        from app.rag.bm25_embedder import embed_sparse_one

        embed_sparse_one("my query")
        mod._bm25_embedder.query_embed.assert_called_once_with("my query")


class TestEmbedSparseBatch:
    """Test batch sparse embedding."""

    def setup_method(self) -> None:
        import app.rag.bm25_embedder as mod

        mod._bm25_embedder = None

    def teardown_method(self) -> None:
        import app.rag.bm25_embedder as mod

        mod._bm25_embedder = None

    def test_returns_one_tuple_per_input_text(self) -> None:
        import numpy as np

        import app.rag.bm25_embedder as mod

        def _make_sparse(idxs: list[int], vals: list[float]) -> MagicMock:
            r = MagicMock()
            r.indices = np.array(idxs)
            r.values = np.array(vals)
            return r

        mock_model = MagicMock()
        mock_model.passage_embed.return_value = iter(
            [
                _make_sparse([1, 2], [0.9, 0.1]),
                _make_sparse([5], [0.7]),
            ]
        )
        mod._bm25_embedder = mock_model

        from app.rag.bm25_embedder import embed_sparse_batch

        result = embed_sparse_batch(["text one", "text two"])
        assert len(result) == 2
        assert result[0] == ([1, 2], pytest.approx([0.9, 0.1]))
        assert result[1] == ([5], pytest.approx([0.7]))
