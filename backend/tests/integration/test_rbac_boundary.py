"""
Integration test — RC-78

Ingests marketing data into a live Qdrant instance and asserts that a finance-role
user gets 0 chunks back when querying marketing content, proving dual-layer RBAC
enforcement at the retrieval stage.

Requires:
  - Qdrant running (docker compose up qdrant)
  - GROQ_API_KEY set in the environment
  - QDRANT_URL env var or default http://localhost:6333

Skips automatically if either dependency is missing.
"""

from __future__ import annotations

import os
import pathlib
import uuid

import pytest
from qdrant_client import QdrantClient

from ingest.chunkers.markdown_chunker import chunk_markdown
from ingest.embedder import Embedder
from ingest.qdrant_store import batch_upsert, init_collection

_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
_TEST_COLLECTION = f"test_rbac_{uuid.uuid4().hex[:8]}"

_MARKETING_FILE = (
    pathlib.Path(__file__).parents[3]
    / "data"
    / "marketing"
    / "marketing_report_2024.md"
)

_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _qdrant_available() -> bool:
    try:
        QdrantClient(url=_QDRANT_URL, timeout=3).get_collections()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _qdrant_available() or not os.getenv("GROQ_API_KEY"),
    reason=(
        "Skipping RBAC boundary tests: "
        "Qdrant must be reachable and GROQ_API_KEY must be set. "
        "Start Qdrant with: docker compose up qdrant"
    ),
)


@pytest.fixture(scope="module")
def qdrant_client() -> QdrantClient:
    return QdrantClient(url=_QDRANT_URL)


@pytest.fixture(scope="module")
def ingested_marketing_collection(qdrant_client: QdrantClient) -> str:
    """Ingest marketing_report_2024.md into an isolated test collection."""
    assert _MARKETING_FILE.exists(), f"Marketing data file missing: {_MARKETING_FILE}"

    init_collection(qdrant_client, _TEST_COLLECTION, _EMBEDDING_MODEL, reset=True)

    chunks = chunk_markdown(_MARKETING_FILE)
    embedder = Embedder(model_name=_EMBEDDING_MODEL)
    vectors = embedder.embed_batch([c["text"] for c in chunks])
    batch_upsert(qdrant_client, _TEST_COLLECTION, chunks, vectors)

    yield _TEST_COLLECTION

    qdrant_client.delete_collection(_TEST_COLLECTION)


class TestRbacBoundaryFinanceVsMarketing:
    """RC-78: finance role cannot retrieve marketing content."""

    def test_finance_role_gets_zero_chunks_for_marketing_query(
        self, ingested_marketing_collection: str, monkeypatch
    ):
        from app.config import settings
        from app.rag.pipeline import run_rag

        monkeypatch.setattr(settings, "qdrant_collection", ingested_marketing_collection)

        result = run_rag(
            query="What were the Q1 marketing campaign results and budget?",
            user_role="finance",
        )

        assert result.num_chunks == 0, (
            f"Expected 0 chunks for finance role on marketing docs, got {result.num_chunks}"
        )
        assert result.sources == [], (
            f"Expected empty sources for finance role, got {result.sources}"
        )

    def test_finance_role_gets_no_relevant_answer_for_marketing_query(
        self, ingested_marketing_collection: str, monkeypatch
    ):
        from app.config import settings
        from app.rag.pipeline import run_rag

        monkeypatch.setattr(settings, "qdrant_collection", ingested_marketing_collection)

        result = run_rag(
            query="What were the marketing campaign conversion rates?",
            user_role="finance",
        )

        # Pipeline falls back to zero-result message when no chunks pass the filter
        assert "couldn't find" in result.answer.lower() or "relevant information" in result.answer.lower()

    def test_marketing_role_can_access_same_content(
        self, ingested_marketing_collection: str, monkeypatch
    ):
        """Confirm the data is actually there — marketing role should get chunks."""
        from app.config import settings
        from app.rag.pipeline import run_rag

        monkeypatch.setattr(settings, "qdrant_collection", ingested_marketing_collection)

        result = run_rag(
            query="What were the Q1 marketing campaign results and budget?",
            user_role="marketing",
        )

        assert result.num_chunks > 0, (
            "Marketing role should retrieve chunks from marketing docs"
        )
