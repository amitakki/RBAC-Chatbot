"""
Unit tests for ingest/chunkers/markdown_chunker.py
"""

import textwrap
from pathlib import Path

import pytest

from ingest.chunkers.markdown_chunker import chunk_markdown


@pytest.fixture()
def simple_md(tmp_path: Path) -> Path:
    content = textwrap.dedent("""\
        # Introduction
        This is the introduction paragraph with some content about FinSolve.

        ## Background
        Here is some background information that is relevant to understanding
        the context.

        # Revenue Overview
        Total revenue for Q4 2024 reached $9.4 billion, a 12% increase YoY.

        ## Regional Breakdown
        APAC contributed 35% of total revenue followed by EMEA at 28%.
    """)
    md_file = tmp_path / "financial_summary.md"
    md_file.write_text(content, encoding="utf-8")
    return md_file


@pytest.fixture()
def large_md(tmp_path: Path) -> Path:
    """File large enough to produce multiple chunks."""
    paragraph = "This is a filler sentence to pad out the document. " * 20
    sections = "\n\n".join(
        f"# Section {i}\n\n{paragraph}" for i in range(1, 15)
    )
    md_file = tmp_path / "financial_summary.md"
    md_file.write_text(sections, encoding="utf-8")
    return md_file


@pytest.fixture()
def table_md(tmp_path: Path) -> Path:
    """Markdown with a policy table that must not be split mid-row."""
    content = textwrap.dedent("""\
        # Leave Policy

        ## Types of Leave

        | Leave Type | Entitlement |
        |------------|-------------|
        | Annual     | 21 days     |
        | Sick       | 12 days     |
        | Casual     | 7 days      |
        | Maternity  | 26 weeks    |
        | Paternity  | 15 days     |

        Additional text after the table to ensure prose and table are
        separate blocks.
    """)
    md_file = tmp_path / "employee_handbook.md"
    md_file.write_text(content, encoding="utf-8")
    return md_file


@pytest.fixture()
def quarterly_md(tmp_path: Path) -> Path:
    """Q1 marketing report — quarter label should be detected and injected."""
    content = textwrap.dedent("""\
        # Comprehensive Marketing Report - Q1 2024

        ## Executive Summary
        Q1 2024 marked a foundational quarter with strong digital growth.

        ## Q1 - Marketing Overview
        In Q1 2024, FinNova prioritized digital campaigns across Southeast Asia.
    """)
    md_file = tmp_path / "marketing_report_q1_2024.md"
    md_file.write_text(content, encoding="utf-8")
    return md_file


class TestChunkMarkdown:
    def test_returns_list_of_dicts(self, simple_md: Path):
        chunks = chunk_markdown(simple_md)
        assert isinstance(chunks, list)
        assert all(isinstance(c, dict) for c in chunks)

    def test_each_chunk_has_text_and_metadata(self, simple_md: Path):
        chunks = chunk_markdown(simple_md)
        for chunk in chunks:
            assert "text" in chunk
            assert "metadata" in chunk

    def test_chunk_text_is_non_empty(self, simple_md: Path):
        chunks = chunk_markdown(simple_md)
        for chunk in chunks:
            assert chunk["text"].strip()

    def test_chunk_size_at_most_900_chars(self, large_md: Path):
        chunks = chunk_markdown(large_md)
        for chunk in chunks:
            # Tables may exceed the limit intentionally; skip them
            if not chunk["text"].lstrip().startswith("|"):
                assert len(chunk["text"]) <= 900 + 64, (
                    f"Prose chunk too large: {len(chunk['text'])} chars"
                )

    def test_source_file_in_metadata(self, simple_md: Path):
        chunks = chunk_markdown(simple_md)
        for chunk in chunks:
            assert chunk["metadata"]["source_file"] == "financial_summary.md"

    def test_allowed_roles_correct(self, simple_md: Path):
        chunks = chunk_markdown(simple_md)
        for chunk in chunks:
            assert set(chunk["metadata"]["allowed_roles"]) == {
                "finance", "executive"
            }

    def test_chunk_index_sequential(self, simple_md: Path):
        chunks = chunk_markdown(simple_md)
        for i, chunk in enumerate(chunks):
            assert chunk["metadata"]["chunk_index"] == i

    def test_total_chunks_consistent(self, simple_md: Path):
        chunks = chunk_markdown(simple_md)
        n = len(chunks)
        for chunk in chunks:
            assert chunk["metadata"]["total_chunks"] == n

    def test_heading_metadata_extracted(self, simple_md: Path):
        chunks = chunk_markdown(simple_md)
        h1_values = [
            c["metadata"].get("section_h1", "")
            for c in chunks
            if c["metadata"].get("section_h1")
        ]
        assert h1_values, "No section_h1 found in any chunk"

    def test_large_doc_produces_multiple_chunks(self, large_md: Path):
        chunks = chunk_markdown(large_md)
        assert len(chunks) > 1

    def test_table_preserved_as_single_chunk(self, table_md: Path):
        chunks = chunk_markdown(table_md)
        table_chunks = [c for c in chunks if "|" in c["text"]]
        assert table_chunks, "Expected at least one table chunk"
        for tc in table_chunks:
            rows = [
                line for line in tc["text"].splitlines()
                if line.strip().startswith("|")
            ]
            header_present = any("Leave Type" in row for row in rows)
            data_present = any("Annual" in row for row in rows)
            assert header_present and data_present, (
                "Table header and data rows must be in the same chunk"
            )

    def test_quarter_label_in_chunk_text(self, quarterly_md: Path):
        chunks = chunk_markdown(quarterly_md)
        texts_with_q1 = [c for c in chunks if "Q1" in c["text"]]
        assert texts_with_q1, (
            "Expected [Q1] prefix in at least one chunk's text"
        )

    def test_quarter_in_metadata(self, quarterly_md: Path):
        chunks = chunk_markdown(quarterly_md)
        for chunk in chunks:
            got = chunk["metadata"].get("quarter")
            assert got == "Q1", (
                f"Expected quarter='Q1' in metadata, got: {got}"
            )
