"""Unit tests for StructuredRetriever (scroll-based retrieval)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct

from app.rag.retriever import RetrievedChunk, RetrieverUnavailableError
from app.rag.structured_retriever import StructuredRetriever


def _make_scroll_point(
    text: str = "Employee Aadhya Saxena (ID: FINEMP1004) works as Marketing Manager...",
    row_id: str = "FINEMP1004",
    source_file: str = "hr_data.csv",
    allowed_roles: list[str] | None = None,
    doc_id: str = "hr_data_csv_chunk_000",
) -> PointStruct:
    """Helper to build a mock Qdrant point matching scroll response shape."""
    if allowed_roles is None:
        allowed_roles = ["hr", "executive"]
    return PointStruct(
        id=hash(row_id),  # deterministic but unique
        vector=[],  # scroll with_vectors=False
        payload={
            "text": text,
            "row_id": row_id,
            "source_file": source_file,
            "allowed_roles": allowed_roles,
            "doc_id": doc_id,
        },
    )


def _make_summary_point(
    text: str = "Employees with role Marketing Manager (7 total): Aadhya Saxena, ...",
    summary_type: str = "role",
    summary_group: str = "Marketing Manager",
    source_file: str = "hr_data.csv",
    allowed_roles: list[str] | None = None,
    doc_id: str = "hr_data_csv_chunk_100",
) -> PointStruct:
    """Helper to build a summary chunk (no row_id)."""
    if allowed_roles is None:
        allowed_roles = ["hr", "executive"]
    return PointStruct(
        id=hash(summary_group),
        vector=[],
        payload={
            "text": text,
            "source_file": source_file,
            "allowed_roles": allowed_roles,
            "summary_type": summary_type,
            "summary_group": summary_group,
            "doc_id": doc_id,
            # Note: no row_id field
        },
    )


class TestStructuredRetrieverRbac:
    """Tests for RBAC filtering in scroll."""

    def test_scroll_filter_includes_allowed_roles(self) -> None:
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([], None)

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")
        retriever.retrieve_all("hr", None)

        # Verify the scroll was called
        assert mock_client.scroll.called
        call_args = mock_client.scroll.call_args
        scroll_filter: Filter = call_args.kwargs["scroll_filter"]

        # Verify allowed_roles filter is present
        assert scroll_filter.must is not None
        role_filter = [c for c in scroll_filter.must if c.key == "allowed_roles"]
        assert len(role_filter) == 1
        assert role_filter[0].match.value == "hr"

    def test_scroll_filter_restricts_to_hr_csv(self) -> None:
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([], None)

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")
        retriever.retrieve_all("finance", None)

        call_args = mock_client.scroll.call_args
        scroll_filter: Filter = call_args.kwargs["scroll_filter"]

        # Verify source_file filter is present
        source_filter = [c for c in scroll_filter.must if c.key == "source_file"]
        assert len(source_filter) == 1
        assert source_filter[0].match.value == "hr_data.csv"

    def test_rbac_different_roles(self) -> None:
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([], None)

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")

        # Test with different roles
        for role in ["hr", "finance", "executive"]:
            retriever.retrieve_all(role, None)
            call_args = mock_client.scroll.call_args
            scroll_filter: Filter = call_args.kwargs["scroll_filter"]
            role_filter = [c for c in scroll_filter.must if c.key == "allowed_roles"]
            assert role_filter[0].match.value == role


class TestStructuredRetrieverEntityFilter:
    """Tests for entity text matching."""

    def test_entity_match_returns_matching_chunks(self) -> None:
        point1 = _make_scroll_point(
            text="Employee Aadhya Saxena works as Marketing Manager in Lucknow",
            row_id="FINEMP1004",
        )
        point2 = _make_scroll_point(
            text="Employee Prisha Mehta works as Marketing Manager in Bengaluru",
            row_id="FINEMP1007",
        )
        point3 = _make_scroll_point(
            text="Employee Shaurya Joshi works as Financial Analyst in Delhi",
            row_id="FINEMP1005",
        )

        mock_client = MagicMock()
        mock_client.scroll.return_value = ([point1, point2, point3], None)

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")
        chunks = retriever.retrieve_all("hr", entity="Marketing Manager")

        # Should only return the two Marketing Manager chunks
        assert len(chunks) == 2
        assert all("Marketing Manager" in c.text for c in chunks)

    def test_entity_match_is_case_insensitive(self) -> None:
        point = _make_scroll_point(
            text="Employee works as MARKETING MANAGER"
        )
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([point], None)

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")
        chunks = retriever.retrieve_all("hr", entity="marketing manager")

        # Should match despite case difference
        assert len(chunks) == 1

    def test_entity_none_returns_all_row_chunks(self) -> None:
        point1 = _make_scroll_point(row_id="FINEMP1001")
        point2 = _make_scroll_point(row_id="FINEMP1002")
        summary = _make_summary_point()

        mock_client = MagicMock()
        mock_client.scroll.return_value = ([point1, point2, summary], None)

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")
        chunks = retriever.retrieve_all("hr", entity=None)

        # Should return both row chunks, exclude summary
        assert len(chunks) == 2

    def test_summary_chunks_excluded(self) -> None:
        row_point = _make_scroll_point(row_id="FINEMP1004")
        summary_point = _make_summary_point()  # no row_id

        mock_client = MagicMock()
        mock_client.scroll.return_value = ([row_point, summary_point], None)

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")
        chunks = retriever.retrieve_all("hr", entity=None)

        # Should exclude summary (no row_id)
        assert len(chunks) == 1
        assert "FINEMP1004" in chunks[0].text

    def test_no_matches_returns_empty_list(self) -> None:
        point = _make_scroll_point(text="Employee works as Data Scientist")
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([point], None)

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")
        chunks = retriever.retrieve_all("hr", entity="Marketing Manager")

        # No match
        assert len(chunks) == 0


class TestStructuredRetrieverPagination:
    """Tests for pagination through scroll results."""

    def test_paginates_until_next_offset_none(self) -> None:
        page1_points = [_make_scroll_point(row_id=f"FINEMP{i}") for i in range(1, 11)]
        page2_points = [_make_scroll_point(row_id=f"FINEMP{i}") for i in range(11, 21)]

        mock_client = MagicMock()
        # First call returns page1 with next_offset, second call returns page2 with None
        mock_client.scroll.side_effect = [
            (page1_points, 10),  # offset for next page
            (page2_points, None),  # no more pages
        ]

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")
        chunks = retriever.retrieve_all("hr", entity=None)

        # Should have all 20 chunks
        assert len(chunks) == 20
        # Should have called scroll twice
        assert mock_client.scroll.call_count == 2

    def test_single_page_no_offset(self) -> None:
        points = [_make_scroll_point(row_id=f"FINEMP{i}") for i in range(1, 6)]
        mock_client = MagicMock()
        mock_client.scroll.return_value = (points, None)

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")
        chunks = retriever.retrieve_all("hr", entity=None)

        assert len(chunks) == 5
        assert mock_client.scroll.call_count == 1


class TestStructuredRetrieverChunkConversion:
    """Tests for PointStruct -> RetrievedChunk conversion."""

    def test_score_is_1_0_sentinel(self) -> None:
        point = _make_scroll_point()
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([point], None)

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")
        chunks = retriever.retrieve_all("hr", entity=None)

        assert len(chunks) == 1
        # Score should be 1.0 sentinel for structured retrieval
        assert chunks[0].score == 1.0

    def test_chunk_payload_fields_preserved(self) -> None:
        point = _make_scroll_point(
            text="Test employee text",
            source_file="hr_data.csv",
            doc_id="hr_data_csv_chunk_042",
        )
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([point], None)

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")
        chunks = retriever.retrieve_all("hr", entity=None)

        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.text == "Test employee text"
        assert chunk.source_file == "hr_data.csv"
        assert chunk.doc_id == "hr_data_csv_chunk_042"


class TestStructuredRetrieverErrorHandling:
    """Tests for error handling."""

    def test_scroll_exception_raises_retriever_unavailable(self) -> None:
        mock_client = MagicMock()
        mock_client.scroll.side_effect = RuntimeError("Qdrant connection failed")

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")

        with pytest.raises(RetrieverUnavailableError) as exc_info:
            retriever.retrieve_all("hr", entity=None)

        assert "Qdrant scroll failed" in str(exc_info.value)

    def test_missing_payload_fields_handled(self) -> None:
        # Point with missing text field
        point = PointStruct(
            id=1,
            vector=[],
            payload={
                "row_id": "FINEMP1001",
                "source_file": "hr_data.csv",
                "allowed_roles": ["hr"],
                # missing "text" field
            },
        )
        mock_client = MagicMock()
        mock_client.scroll.return_value = ([point], None)

        retriever = StructuredRetriever(client=mock_client, collection="test_collection")
        chunks = retriever.retrieve_all("hr", entity=None)

        # Should not crash, should return with empty text
        assert len(chunks) == 1
        assert chunks[0].text == ""
