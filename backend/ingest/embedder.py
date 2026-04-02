"""
Embedding wrapper for sentence-transformers/all-MiniLM-L6-v2.

Produces vectors using the configured embedding dimension; batch size defaults to 32.
"""

from __future__ import annotations

import logging
import os
import time

from app.config import settings

# On Windows, PyTorch's DLL loader triggers a full CUDA device scan on import,
# causing 60-120 s hangs when Windows Defender scans each CUDA DLL.
# The ingest pipeline only needs CPU inference, so hide all CUDA devices before
# sentence_transformers (and its torch dependency) are imported.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

# huggingface_hub checks the Hub on import; pydantic_settings reads .env but
# does NOT propagate values into os.environ, so HF_TOKEN is invisible to the
# Hub client. Bridge the gap here before sentence_transformers is imported.
if settings.hf_token and not os.environ.get("HF_TOKEN"):
    os.environ["HF_TOKEN"] = settings.hf_token

from sentence_transformers import SentenceTransformer

log = logging.getLogger(__name__)


class Embedder:
    def __init__(self, model_name: str | None = None) -> None:
        self.model_name: str = model_name or settings.embedding_model
        self.dims: int = settings.embedding_dims
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            load_t0 = time.perf_counter()
            log.info(
                "Loading embedding model '%s'. First run may download files from Hugging Face.",
                self.model_name,
            )
            try:
                self._model = SentenceTransformer(self.model_name)
            except Exception as exc:
                raise RuntimeError(
                    "Failed to load the embedding model. "
                    "If this is the first ingest run, ensure the machine can reach "
                    "huggingface.co so sentence-transformers/all-MiniLM-L6-v2 can be downloaded."
                ) from exc
            log.info(
                "Embedding model '%s' ready in %.2fs",
                self.model_name,
                time.perf_counter() - load_t0,
            )
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
