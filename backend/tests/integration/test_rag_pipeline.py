"""
Integration test — RC-71

Ingests quarterly_financial_report.md into a live Qdrant instance and asserts
that the RAG pipeline (run_rag) returns an answer containing "$9.4 billion"
when queried as the finance role (FIN-001 golden dataset scenario).

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
_TEST_COLLECTION = f"test_rag_{uuid.uuid4().hex[:8]}"

_DATA_FILE = (
    pathlib.Path(__file__).parents[3]
    / "data"
    / "finance"
    / "quarterly_financial_report.md"
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
        "Skipping RAG integration tests: "
        "Qdrant must be reachable and GROQ_API_KEY must be set. "
        "Start Qdrant with: docker compose up qdrant"
    ),
)


@pytest.fixture(scope="module")
def qdrant_client() -> QdrantClient:
    return QdrantClient(url=_QDRANT_URL)


@pytest.fixture(scope="module")
def ingested_collection(qdrant_client: QdrantClient) -> str:
    """Ingest quarterly_financial_report.md into an isolated test collection."""
    assert _DATA_FILE.exists(), f"Data file missing: {_DATA_FILE}"

    init_collection(qdrant_client, _TEST_COLLECTION, _EMBEDDING_MODEL, reset=True)

    chunks = chunk_markdown(_DATA_FILE)
    embedder = Embedder(model_name=_EMBEDDING_MODEL)
    vectors = embedder.embed_batch([c["text"] for c in chunks])
    batch_upsert(qdrant_client, _TEST_COLLECTION, chunks, vectors)

    yield _TEST_COLLECTION

    qdrant_client.delete_collection(_TEST_COLLECTION)


class TestRagPipelineFin001:
    """FIN-001: finance role query for total revenue → answer contains '$9.4 billion'."""

    def test_finance_query_answer_contains_revenue_figure(
        self, ingested_collection: str, monkeypatch
    ):
        from app.config import settings
        from app.rag.pipeline import run_rag

        monkeypatch.setattr(settings, "qdrant_collection", ingested_collection)

        result = run_rag(
            query="What was FinSolve's total revenue in 2024?",
            user_role="finance",
        )

        assert "$9.4 billion" in result.answer, (
            f"Expected '$9.4 billion' in answer, got:\n{result.answer}"
        )

    def test_finance_query_returns_sources(
        self, ingested_collection: str, monkeypatch
    ):
        from app.config import settings
        from app.rag.pipeline import run_rag

        monkeypatch.setattr(settings, "qdrant_collection", ingested_collection)

        result = run_rag(
            query="What was FinSolve's total revenue in 2024?",
            user_role="finance",
        )

        assert result.sources, "Expected at least one source in the result"
        assert result.num_chunks > 0

    def test_hr_role_returns_no_relevant_chunks(
        self, ingested_collection: str, monkeypatch
    ):
        """RBAC enforcement: hr role must not access finance documents."""
        from app.config import settings
        from app.rag.pipeline import run_rag

        monkeypatch.setattr(settings, "qdrant_collection", ingested_collection)

        result = run_rag(
            query="What was FinSolve's total revenue in 2024?",
            user_role="hr",
        )

        # HR has no access to finance docs — pipeline returns the zero-result message
        assert result.num_chunks == 0
        assert result.sources == []
        assert "couldn't find" in result.answer.lower() or "relevant information" in result.answer.lower()

    def test_run_id_is_unique_per_call(
        self, ingested_collection: str, monkeypatch
    ):
        from app.config import settings
        from app.rag.pipeline import run_rag

        monkeypatch.setattr(settings, "qdrant_collection", ingested_collection)

        result_a = run_rag("What is Q4 revenue?", user_role="finance")
        result_b = run_rag("What is Q4 revenue?", user_role="finance")

        assert result_a.run_id != result_b.run_id
