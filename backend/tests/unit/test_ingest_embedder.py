from __future__ import annotations

import pytest

from ingest.embedder import Embedder


def test_embedder_wraps_model_load_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_on_load(model_name: str):
        raise OSError(f"cannot load {model_name}")

    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.setattr("ingest.embedder.SentenceTransformer", raise_on_load)

    embedder = Embedder(model_name="sentence-transformers/all-MiniLM-L6-v2")

    with pytest.raises(RuntimeError, match="Failed to load embedding model"):
        _ = embedder.model
