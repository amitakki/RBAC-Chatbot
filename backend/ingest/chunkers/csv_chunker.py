"""
CSV document chunker.

Produces one chunk per data row. Each chunk text is:
    "<col1>\t<col2>\t...\n<val1>\t<val2>\t..."

hr_data.csv is automatically flagged with contains_pii=True and the
relevant PII field names are listed in pii_fields.
"""

from __future__ import annotations

import csv
from pathlib import Path

from ingest.chunkers.metadata import build_metadata

# Files that contain PII and which columns are sensitive
_PII_FILES: dict[str, list[str]] = {
    "hr_data.csv": ["salary", "date_of_birth", "performance_rating"],
}

# Column that acts as the row identifier (if present)
_ID_COLUMNS = ("employee_id", "id", "ID")


def chunk_csv(file_path: Path | str) -> list[dict]:
    """
    Load a CSV file and return a list of chunk dicts.

    Each dict has:
      - "text": header row + data row as tab-separated strings
      - "metadata": full Qdrant payload dict (from build_metadata)
    """
    file_path = Path(file_path)
    source_file = file_path.name
    pii_fields = _PII_FILES.get(source_file)

    rows: list[dict] = []
    with file_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        header_line = "\t".join(fieldnames)
        for row in reader:
            rows.append(dict(row))

    total = len(rows)
    result: list[dict] = []

    for idx, row in enumerate(rows):
        data_line = "\t".join(str(row.get(col, "")) for col in fieldnames)
        text = f"{header_line}\n{data_line}"

        # Determine row_id
        row_id: str = str(idx)
        for id_col in _ID_COLUMNS:
            if id_col in row and row[id_col]:
                row_id = row[id_col]
                break

        extra: dict = {"row_id": row_id}
        if pii_fields is not None:
            extra["contains_pii"] = True
            extra["pii_fields"] = pii_fields

        metadata = build_metadata(
            source_file=source_file,
            chunk_index=idx,
            total_chunks=total,
            extra=extra,
        )
        result.append({"text": text, "metadata": metadata})

    return result
