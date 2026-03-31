"""
Integration test — RC-65

Ingest financial_summary.md into a live Qdrant instance and assert:
  - At least 1 point exists in the collection
  - Each point has the correct payload fields
  - allowed_roles contains finance and executive
  - No finance chunks are returned when filtering for role=hr

Requires:
  - Qdrant running (docker compose up qdrant)
  - QDRANT_URL env var or default http://localhost:6333

Skip automatically if Qdrant is unreachable.
"""

from __future__ import annotations

import os
import uuid

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

from ingest.chunkers.markdown_chunker import chunk_markdown
from ingest.embedder import Embedder
from ingest.qdrant_store import batch_upsert, init_collection

# Isolated test collection — never touches the production collection
_TEST_COLLECTION = f"test_ingest_{uuid.uuid4().hex[:8]}"
_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

DATA_FILE = (
    __file__  # tests/integration/test_ingest.py
    and __import__("pathlib").Path(__file__).parents[3]
    / "data"
    / "finance"
    / "financial_summary.md"
)


def _qdrant_available() -> bool:
    try:
        client = QdrantClient(url=_QDRANT_URL, timeout=3)
        client.get_collections()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _qdrant_available(),
    reason="Qdrant not reachable at %s — start with: docker compose up qdrant" % _QDRANT_URL,
)


@pytest.fixture(scope="module")
def qdrant_client():
    return QdrantClient(url=_QDRANT_URL)


@pytest.fixture(scope="module")
def ingested_collection(qdrant_client: QdrantClient):
    """Create a fresh collection, ingest financial_summary.md, then clean up."""
    import pathlib

    file_path = pathlib.Path(__file__).parents[3] / "data" / "finance" / "financial_summary.md"
    assert file_path.exists(), f"Data file missing: {file_path}"

    embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    init_collection(qdrant_client, _TEST_COLLECTION, embedding_model, reset=True)

    chunks = chunk_markdown(file_path)
    embedder = Embedder(model_name=embedding_model)
    texts = [c["text"] for c in chunks]
    vectors = embedder.embed_batch(texts)
    batch_upsert(qdrant_client, _TEST_COLLECTION, chunks, vectors)

    yield _TEST_COLLECTION

    # Cleanup
    qdrant_client.delete_collection(_TEST_COLLECTION)


class TestIngestFinancialSummary:
    def test_collection_has_at_least_one_point(
        self, qdrant_client: QdrantClient, ingested_collection: str
    ):
        info = qdrant_client.get_collection(ingested_collection)
        # Subtract 1 for the metadata sentinel point (id=0)
        assert info.points_count > 1

    def test_points_have_required_payload_fields(
        self, qdrant_client: QdrantClient, ingested_collection: str
    ):
        results = qdrant_client.scroll(
            collection_name=ingested_collection,
            limit=5,
            with_payload=True,
            with_vectors=False,
        )[0]
        # Filter out the sentinel point
        data_points = [p for p in results if p.id != 0]
        assert data_points, "No data points found"

        required_fields = {
            "doc_id", "source_file", "allowed_roles", "department",
            "sensitivity", "chunk_index", "total_chunks", "ingested_at", "text",
        }
        for point in data_points:
            missing = required_fields - set(point.payload or {})
            assert not missing, f"Point {point.id} missing fields: {missing}"

    def test_allowed_roles_contains_finance_and_executive(
        self, qdrant_client: QdrantClient, ingested_collection: str
    ):
        results = qdrant_client.scroll(
            collection_name=ingested_collection,
            limit=10,
            with_payload=True,
            with_vectors=False,
        )[0]
        data_points = [p for p in results if p.id != 0]
        for point in data_points:
            roles = set(point.payload.get("allowed_roles", []))
            assert "finance" in roles, f"finance missing from {point.id}"
            assert "executive" in roles, f"executive missing from {point.id}"

    def test_source_file_is_financial_summary(
        self, qdrant_client: QdrantClient, ingested_collection: str
    ):
        results = qdrant_client.scroll(
            collection_name=ingested_collection,
            limit=5,
            with_payload=True,
            with_vectors=False,
        )[0]
        data_points = [p for p in results if p.id != 0]
        for point in data_points:
            assert point.payload.get("source_file") == "financial_summary.md"

    def test_hr_role_filter_returns_zero_finance_chunks(
        self, qdrant_client: QdrantClient, ingested_collection: str
    ):
        """RBAC filter: hr role must not retrieve finance chunks (RC-78 basis)."""
        embedder = Embedder()
        query_vector = embedder.embed_one("What is the Q4 revenue?")

        results = qdrant_client.search(
            collection_name=ingested_collection,
            query_vector=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="allowed_roles",
                        match=MatchValue(value="hr"),
                    )
                ]
            ),
            limit=5,
        )
        assert len(results) == 0, (
            f"Expected 0 results for hr role on finance doc, got {len(results)}"
        )
