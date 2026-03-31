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
        Here is some background information that is relevant to understanding the context.

        # Revenue Overview
        Total revenue for Q4 2024 reached $9.4 billion, a 12% increase year-over-year.

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
    sections = "\n\n".join(f"# Section {i}\n\n{paragraph}" for i in range(1, 15))
    md_file = tmp_path / "financial_summary.md"
    md_file.write_text(sections, encoding="utf-8")
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

    def test_chunk_size_at_most_512_chars(self, large_md: Path):
        chunks = chunk_markdown(large_md)
        for chunk in chunks:
            assert len(chunk["text"]) <= 512 + 64, (
                f"Chunk too large: {len(chunk['text'])} chars"
            )

    def test_source_file_in_metadata(self, simple_md: Path):
        chunks = chunk_markdown(simple_md)
        for chunk in chunks:
            assert chunk["metadata"]["source_file"] == "financial_summary.md"

    def test_allowed_roles_correct(self, simple_md: Path):
        chunks = chunk_markdown(simple_md)
        for chunk in chunks:
            assert set(chunk["metadata"]["allowed_roles"]) == {"finance", "executive"}

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
