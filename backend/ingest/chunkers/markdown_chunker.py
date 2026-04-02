"""
Markdown document chunker.

Chunks Markdown documents in two stages:
1. Split by heading boundaries to preserve section semantics.
2. Recursively split oversized sections into smaller chunks.

Metadata preserves the active heading hierarchy for each chunk.
"""

from __future__ import annotations

import re
from pathlib import Path

from ingest.chunkers.metadata import build_metadata

_MAX_CHUNK_SIZE = 512
_CHUNK_OVERLAP = 64
_SEPARATORS = ("\n\n", "\n", " ")

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")


def _split_sections(raw: str) -> list[dict]:
    """Split markdown into heading-aware sections."""
    sections: list[dict] = []
    buffer: list[str] = []
    current_h1 = ""
    current_h2 = ""
    current_h3 = ""

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if not text:
            return
        sections.append(
            {
                "text": text,
                "section_h1": current_h1,
                "section_h2": current_h2,
                "section_h3": current_h3,
            }
        )

    for line in raw.splitlines():
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            flush()
            buffer = [line]

            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            if level == 1:
                current_h1 = heading_text
                current_h2 = ""
                current_h3 = ""
            elif level == 2:
                current_h2 = heading_text
                current_h3 = ""
            else:
                current_h3 = heading_text
            continue

        buffer.append(line)

    flush()
    return sections


def _section_prefix(section: dict) -> str:
    """Return parent heading context to prepend before chunk text."""
    lines: list[str] = []
    text = section["text"]

    if section["section_h1"] and not text.startswith(f"# {section['section_h1']}"):
        lines.append(f"# {section['section_h1']}")
    if section["section_h2"] and not text.startswith(f"## {section['section_h2']}"):
        lines.append(f"## {section['section_h2']}")

    return "\n\n".join(lines).strip()


def _split_section_text(section: dict) -> list[str]:
    """Split one semantic section, carrying parent heading context if needed."""
    prefix = _section_prefix(section)
    section_text = section["text"].strip()

    if prefix:
        section_text = f"{prefix}\n\n{section_text}"

    return _split_with_overlap(section_text)


def _split_with_overlap(text: str) -> list[str]:
    """Split text to fit within chunk size while preserving small overlaps."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= _MAX_CHUNK_SIZE:
        return [text]

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + _MAX_CHUNK_SIZE, len(text))
        split_at = _best_split_position(text, start, end)
        chunk = text[start:split_at].strip()

        if not chunk:
            break

        chunks.append(chunk)
        if split_at >= len(text):
            break

        next_start = max(split_at - _CHUNK_OVERLAP, 0)
        while next_start < len(text) and text[next_start].isspace():
            next_start += 1
        if next_start <= start:
            next_start = split_at
        start = next_start

    return chunks


def _best_split_position(text: str, start: int, end: int) -> int:
    """Prefer paragraph and line boundaries before falling back to hard cuts."""
    for separator in _SEPARATORS:
        split_at = text.rfind(separator, start, end)
        if split_at > start:
            return split_at + len(separator)
    return end


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

    sections = _split_sections(raw)

    raw_chunks: list[dict] = []
    for section in sections:
        for text in _split_section_text(section):
            if not text.strip():
                continue
            raw_chunks.append(
                {
                    "text": text,
                    "section_h1": section["section_h1"],
                    "section_h2": section["section_h2"],
                    "section_h3": section["section_h3"],
                }
            )

    total = len(raw_chunks)
    result: list[dict] = []

    for idx, chunk in enumerate(raw_chunks):
        extra: dict = {}
        if chunk["section_h1"]:
            extra["section_h1"] = chunk["section_h1"]
        if chunk["section_h2"]:
            extra["section_h2"] = chunk["section_h2"]
        if chunk["section_h3"]:
            extra["section_h3"] = chunk["section_h3"]

        metadata = build_metadata(
            source_file=source_file,
            chunk_index=idx,
            total_chunks=total,
            extra=extra,
        )
        result.append({"text": chunk["text"], "metadata": metadata})

    return result
