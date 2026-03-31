"""
Embedding wrapper for sentence-transformers/all-MiniLM-L6-v2.

Produces 384-dimensional vectors; batch size defaults to 32.
"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

from app.config import settings

EMBEDDING_DIMS = 384


class Embedder:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name: str = model_name or settings.embedding_model
        self.dims: int = EMBEDDING_DIMS
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Embed a list of texts and return as list of float vectors."""
        vectors = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=len(texts) > batch_size,
            convert_to_numpy=True,
        )
        return vectors.tolist()

    def embed_one(self, text: str) -> list[float]:
        """Convenience wrapper for a single text."""
        return self.embed_batch([text])[0]
