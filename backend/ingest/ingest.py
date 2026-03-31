"""
Data Ingestion CLI — EPIC 2 / RC-64

Usage (from backend/ directory):
    uv run python -m ingest.ingest
    uv run python -m ingest.ingest --reset
    uv run python -m ingest.ingest --dry-run

Also available via Justfile:
    just ingest
    just ingest-reset
    just ingest-dry
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from qdrant_client import QdrantClient

from app.config import settings
from ingest.chunkers.csv_chunker import chunk_csv
from ingest.chunkers.markdown_chunker import chunk_markdown
from ingest.embedder import Embedder
from ingest.qdrant_store import batch_upsert, init_collection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Ordered list of (relative path from data_dir, source filename)
DOCUMENTS: list[tuple[str, str]] = [
    ("finance/financial_summary.md",          "financial_summary.md"),
    ("finance/quarterly_financial_report.md", "quarterly_financial_report.md"),
    ("general/employee_handbook.md",          "employee_handbook.md"),
    ("hr/hr_data.csv",                        "hr_data.csv"),
    ("engineering/engineering_master_doc.md", "engineering_master_doc.md"),
    ("marketing/marketing_report_2024.md",    "marketing_report_2024.md"),
    ("marketing/marketing_report_q1_2024.md", "marketing_report_q1_2024.md"),
    ("marketing/marketing_report_q2_2024.md", "marketing_report_q2_2024.md"),
    ("marketing/marketing_report_q3_2024.md", "marketing_report_q3_2024.md"),
    ("marketing/market_report_q4_2024.md",    "market_report_q4_2024.md"),
]


def _chunk_file(file_path: Path) -> list[dict]:
    suffix = file_path.suffix.lower()
    if suffix == ".md":
        return chunk_markdown(file_path)
    if suffix == ".csv":
        return chunk_csv(file_path)
    raise ValueError(f"Unsupported file type: {suffix}")


def run(reset: bool = False, dry_run: bool = False) -> None:
    data_root = Path(settings.data_dir).resolve()
    collection = settings.qdrant_collection
    embedding_model = settings.embedding_model

    embedder = Embedder(model_name=embedding_model)
    client: QdrantClient | None = None

    if not dry_run:
        client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        init_collection(client, collection, embedding_model, reset=reset)
        log.info(
            "Collection '%s' ready (reset=%s)", collection, reset
        )

    total_chunks = 0
    total_docs = 0
    t0 = time.perf_counter()

    for rel_path, filename in DOCUMENTS:
        file_path = data_root / rel_path
        if not file_path.exists():
            log.warning("File not found, skipping: %s", file_path)
            continue

        chunks = _chunk_file(file_path)
        n = len(chunks)
        total_chunks += n
        total_docs += 1

        if dry_run:
            log.info("[dry-run] %s → %d chunks (no upsert)", filename, n)
            continue

        texts = [c["text"] for c in chunks]
        vectors = embedder.embed_batch(texts)
        upserted = batch_upsert(client, collection, chunks, vectors)  # type: ignore[arg-type]
        log.info("%s → %d chunks embedded & upserted ✓", filename, upserted)

    elapsed = time.perf_counter() - t0
    log.info(
        "Done. docs=%d  chunks=%d  model=%s  collection=%s  elapsed=%.1fs",
        total_docs,
        total_chunks,
        embedding_model,
        collection if not dry_run else "(dry-run)",
        elapsed,
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest FinSolve documents into Qdrant"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the Qdrant collection before ingesting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chunk documents and log counts without writing to Qdrant",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run(reset=args.reset, dry_run=args.dry_run)
