"""
App-level embedding singleton.

Wraps ingest.embedder.Embedder so the model is loaded once per process
and reused across all retrieval calls.
"""

from ingest.embedder import Embedder

_embedder: Embedder | None = None


def get_embedder() -> Embedder:
    """Return the process-wide Embedder singleton (lazy-initialised)."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder
