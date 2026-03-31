"""
Markdown document chunker.

Splits a Markdown file using LangChain's RecursiveCharacterTextSplitter
(chunk_size=512, chunk_overlap=64) and enriches each chunk with heading
hierarchy metadata (section_h1, section_h2).
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ingest.chunkers.metadata import build_metadata

_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=64,
    separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
)

_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_H2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)


def _extract_headings(text: str) -> tuple[str, str]:
    """Return (section_h1, section_h2) found in the chunk text, or empty strings."""
    h1_match = _H1_RE.search(text)
    h2_match = _H2_RE.search(text)
    return (
        h1_match.group(1).strip() if h1_match else "",
        h2_match.group(1).strip() if h2_match else "",
    )


def chunk_markdown(file_path: Path | str) -> list[dict]:
    """
    Load a Markdown file and return a list of chunk dicts.

    Each dict has:
      - "text": the chunk text
      - "metadata": full Qdrant payload dict (from build_metadata)
    """
    file_path = Path(file_path)
    source_file = file_path.name
    raw = file_path.read_text(encoding="utf-8")

    raw_chunks = _SPLITTER.split_text(raw)
    total = len(raw_chunks)

    result: list[dict] = []
    current_h1 = ""
    current_h2 = ""

    for idx, text in enumerate(raw_chunks):
        h1, h2 = _extract_headings(text)
        if h1:
            current_h1 = h1
            current_h2 = ""  # reset sub-heading on new top-level section
        if h2:
            current_h2 = h2

        extra: dict = {}
        if current_h1:
            extra["section_h1"] = current_h1
        if current_h2:
            extra["section_h2"] = current_h2

        metadata = build_metadata(
            source_file=source_file,
            chunk_index=idx,
            total_chunks=total,
            extra=extra,
        )
        result.append({"text": text, "metadata": metadata})

    return result
