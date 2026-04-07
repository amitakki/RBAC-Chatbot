"""
Markdown document chunker.

Chunks Markdown documents in two stages:
1. Split by heading boundaries to preserve section semantics.
2. Split oversized sections with table-awareness:
   - Table blocks (contiguous `|`-prefixed lines) are kept whole.
   - Prose blocks are recursively split with overlap.

Quarter labels (Q1–Q4) are detected from the filename or H1 heading and
injected into chunk text and metadata for quarterly report docs.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from ingest.chunkers.metadata import build_metadata

log = logging.getLogger(__name__)

_MAX_CHUNK_SIZE = 900
_CHUNK_OVERLAP = 64
_SEPARATORS = ("\n\n", "\n", " ")

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
_QUARTER_FILE_RE = re.compile(r"q([1-4])", re.IGNORECASE)
_QUARTER_TEXT_RE = re.compile(r"\bQ([1-4])\b")


# ---------------------------------------------------------------------------
# Quarter detection
# ---------------------------------------------------------------------------

def _extract_quarter(source_file: str, h1: str) -> str | None:
    """Return 'Q1'–'Q4' if detectable from the filename or H1 heading, else None."""
    m = _QUARTER_FILE_RE.search(source_file)
    if m:
        return f"Q{m.group(1).upper()}"
    m = _QUARTER_TEXT_RE.search(h1)
    if m:
        return f"Q{m.group(1)}"
    return None


# ---------------------------------------------------------------------------
# Section splitting
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Table-aware block splitting
# ---------------------------------------------------------------------------

def _split_into_blocks(text: str) -> list[dict]:
    """Partition *text* into alternating prose and table blocks.

    Returns a list of ``{"kind": "prose"|"table", "text": str}`` dicts.
    """
    blocks: list[dict] = []
    lines = text.splitlines(keepends=True)
    current_kind: str | None = None
    buffer: list[str] = []

    def flush_block() -> None:
        if buffer:
            blocks.append({"kind": current_kind, "text": "".join(buffer).strip()})

    for line in lines:
        kind = "table" if line.lstrip().startswith("|") else "prose"
        if kind != current_kind:
            flush_block()
            buffer = []
            current_kind = kind
        buffer.append(line)

    flush_block()
    return [b for b in blocks if b["text"]]


# ---------------------------------------------------------------------------
# Section prefix
# ---------------------------------------------------------------------------

def _section_prefix(
    section: dict,
    quarter: str | None = None,
) -> str:
    """Return parent heading context to prepend before chunk text."""
    lines: list[str] = []
    text = section["text"]

    if quarter:
        lines.append(f"[{quarter}]")
    if section["section_h1"] and not text.startswith(f"# {section['section_h1']}"):
        lines.append(f"# {section['section_h1']}")
    if section["section_h2"] and not text.startswith(f"## {section['section_h2']}"):
        lines.append(f"## {section['section_h2']}")
    if section["section_h3"] and not text.startswith(f"### {section['section_h3']}"):
        lines.append(f"### {section['section_h3']}")

    return "\n\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Section text splitting (table-aware)
# ---------------------------------------------------------------------------

def _split_section_text(
    section: dict,
    quarter: str | None = None,
) -> list[str]:
    """Split one semantic section into chunks, preserving table blocks whole."""
    prefix = _section_prefix(section, quarter=quarter)
    section_text = section["text"].strip()

    if prefix:
        section_text = f"{prefix}\n\n{section_text}"

    chunks: list[str] = []
    for block in _split_into_blocks(section_text):
        if block["kind"] == "table":
            block_text = block["text"]
            if len(block_text) > _MAX_CHUNK_SIZE:
                log.warning(
                    "Table block (%d chars) exceeds _MAX_CHUNK_SIZE=%d — "
                    "keeping whole to preserve header context",
                    len(block_text),
                    _MAX_CHUNK_SIZE,
                )
            chunks.append(block_text)
        else:
            chunks.extend(_split_with_overlap(block["text"]))

    return [c for c in chunks if c.strip()]


# ---------------------------------------------------------------------------
# Character-level overlap splitter (prose only)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def chunk_markdown(file_path: Path | str) -> list[dict]:
    """
    Load a Markdown file and return a list of chunk dicts.

    Each dict has:
      - "text": the chunk text (with heading breadcrumb and optional quarter prefix)
      - "metadata": full Qdrant payload dict (from build_metadata)
    """
    file_path = Path(file_path)
    source_file = file_path.name
    raw = file_path.read_text(encoding="utf-8")

    sections = _split_sections(raw)

    # Detect quarter from filename or first H1
    first_h1 = sections[0]["section_h1"] if sections else ""
    quarter = _extract_quarter(source_file, first_h1)

    raw_chunks: list[dict] = []
    for section in sections:
        for text in _split_section_text(section, quarter=quarter):
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
        if quarter:
            extra["quarter"] = quarter

        metadata = build_metadata(
            source_file=source_file,
            chunk_index=idx,
            total_chunks=total,
            extra=extra,
        )
        result.append({"text": chunk["text"], "metadata": metadata})

    return result
