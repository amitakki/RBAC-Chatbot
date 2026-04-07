"""
CSV document chunker.

Produces one chunk per data row, plus aggregation summary chunks for
hr_data.csv. Summary chunks let the RAG pipeline answer aggregation
queries without needing to retrieve every individual row.

Summary types generated for hr_data.csv:
  - location    : employees grouped by office city
  - department  : employees grouped by department
  - role        : employees grouped by job role
  - manager     : direct reports grouped by manager
  - rating      : employees grouped by performance rating (1–5)

hr_data.csv uses natural-language prose serialization for better semantic
embedding quality. All other CSVs fall back to the original tab-separated
header+row format.

hr_data.csv is automatically flagged with contains_pii=True and the
relevant PII field names are listed in pii_fields.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from ingest.chunkers.metadata import build_metadata

# Files that contain PII and which columns are sensitive
_PII_FILES: dict[str, list[str]] = {
    "hr_data.csv": ["salary", "date_of_birth", "performance_rating"],
}

# Files that use natural-language prose serialization instead of TSV
_NL_FILES: set[str] = {"hr_data.csv"}

# Files for which aggregation summary chunks are generated
_SUMMARY_FILES: set[str] = {"hr_data.csv"}

# Column that acts as the row identifier (if present)
_ID_COLUMNS = ("employee_id", "id", "ID")

# Human-readable labels for performance ratings
_RATING_LABELS: dict[str, str] = {
    "1": "Needs Improvement",
    "2": "Below Expectations",
    "3": "Meets Expectations",
    "4": "Exceeds Expectations",
    "5": "Outstanding",
}


# ---------------------------------------------------------------------------
# Row serialisation
# ---------------------------------------------------------------------------

def _row_to_prose(row: dict[str, str]) -> str:
    """Serialize an HR data row as natural-language prose for embedding."""
    return (
        f"Employee {row.get('full_name', '')} "
        f"(ID: {row.get('employee_id', '')}) "
        f"works as {row.get('role', '')} in the "
        f"{row.get('department', '')} department. "
        f"Location: {row.get('location', '')}. "
        f"Joined: {row.get('date_of_joining', '')}. "
        f"Manager ID: {row.get('manager_id', '')}. "
        f"Date of birth: {row.get('date_of_birth', '')}. "
        f"Salary: {row.get('salary', '')}. "
        f"Leave balance: {row.get('leave_balance', '')} days, "
        f"leaves taken: {row.get('leaves_taken', '')}. "
        f"Attendance: {row.get('attendance_pct', '')}%. "
        f"Performance rating: {row.get('performance_rating', '')}. "
        f"Last review: {row.get('last_review_date', '')}."
    )


# ---------------------------------------------------------------------------
# Summary chunk builder
# ---------------------------------------------------------------------------

def _make_summary(
    text: str,
    summary_type: str,
    summary_group: str,
    summary_count: int,
    source_file: str,
    chunk_index: int,
) -> dict:
    """Build a single summary chunk dict (text + metadata)."""
    extra = {
        "summary_type": summary_type,
        "summary_group": summary_group,
        "summary_count": summary_count,
    }
    metadata = build_metadata(
        source_file=source_file,
        chunk_index=chunk_index,
        total_chunks=0,  # patched by caller after all chunks collected
        extra=extra,
    )
    return {"text": text, "metadata": metadata}


def _build_summary_chunks(
    rows: list[dict],
    source_file: str,
    chunk_index_start: int,
) -> list[dict]:
    """Generate all aggregation summary chunks for *rows*.

    Covers five groupings:
      location   — "Employees in Ahmedabad (10 total): ..."
      department — "Employees in the Sales department (15 total): ..."
      role       — "Employees with role Sales Manager (7 total): ..."
      manager    — "Direct reports of Aadhya Patel (12 total): ..."
      rating     — "Employees with performance rating 5 — Outstanding (23 total): ..."

    Args:
        rows: All data rows from the CSV.
        source_file: Original filename — used for RBAC metadata.
        chunk_index_start: Index offset (summaries follow row chunks).

    Returns:
        List of chunk dicts ready to append to the main result list.
    """
    # Build an id→name lookup so manager summaries show names
    id_to_name: dict[str, str] = {
        r.get("employee_id", ""): r.get("full_name", "")
        for r in rows
    }

    by_location:   dict[str, list[dict]] = defaultdict(list)
    by_department: dict[str, list[dict]] = defaultdict(list)
    by_role:       dict[str, list[dict]] = defaultdict(list)
    by_manager:    dict[str, list[dict]] = defaultdict(list)
    by_rating:     dict[str, list[dict]] = defaultdict(list)

    for row in rows:
        loc  = row.get("location", "").strip()
        dept = row.get("department", "").strip()
        role = row.get("role", "").strip()
        mgr  = row.get("manager_id", "").strip()
        rtg  = row.get("performance_rating", "").strip()

        if loc:
            by_location[loc].append(row)
        if dept:
            by_department[dept].append(row)
        if role:
            by_role[role].append(row)
        if mgr:
            by_manager[mgr].append(row)
        if rtg:
            by_rating[rtg].append(row)

    summaries: list[dict] = []

    def _names(members: list[dict]) -> str:
        return ", ".join(
            f"{r.get('full_name', '')} ({r.get('role', '')})"
            for r in members
        )

    def _idx() -> int:
        return chunk_index_start + len(summaries)

    # --- location ---
    for location, members in sorted(by_location.items()):
        text = (
            f"Employees in {location} ({len(members)} total): "
            f"{_names(members)}."
        )
        summaries.append(_make_summary(
            text, "location", location, len(members), source_file, _idx()
        ))

    # --- department ---
    for department, members in sorted(by_department.items()):
        text = (
            f"Employees in the {department} department "
            f"({len(members)} total): {_names(members)}."
        )
        summaries.append(_make_summary(
            text, "department", department, len(members), source_file, _idx()
        ))

    # --- role ---
    for role, members in sorted(by_role.items()):
        text = (
            f"Employees with role {role} ({len(members)} total): "
            f"{_names(members)}."
        )
        summaries.append(_make_summary(
            text, "role", role, len(members), source_file, _idx()
        ))

    # --- manager ---
    for manager_id, members in sorted(by_manager.items()):
        manager_name = id_to_name.get(manager_id, manager_id)
        text = (
            f"Direct reports of {manager_name} (ID: {manager_id}) "
            f"({len(members)} total): {_names(members)}."
        )
        summaries.append(_make_summary(
            text, "manager", manager_id, len(members), source_file, _idx()
        ))

    # --- performance rating ---
    for rating, members in sorted(by_rating.items()):
        label = _RATING_LABELS.get(rating, rating)
        text = (
            f"Employees with performance rating {rating} — {label} "
            f"({len(members)} total): {_names(members)}."
        )
        summaries.append(_make_summary(
            text, "rating", rating, len(members), source_file, _idx()
        ))

    return summaries


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def chunk_csv(file_path: Path | str) -> list[dict]:
    """
    Load a CSV file and return a list of chunk dicts.

    Each dict has:
      - "text": natural-language prose (hr_data.csv) or header+row TSV (others)
      - "metadata": full Qdrant payload dict (from build_metadata)
    """
    file_path = Path(file_path)
    source_file = file_path.name
    pii_fields = _PII_FILES.get(source_file)
    use_prose = source_file in _NL_FILES
    use_summaries = source_file in _SUMMARY_FILES

    rows: list[dict] = []
    with file_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        header_line = "\t".join(fieldnames)
        for row in reader:
            rows.append(dict(row))

    result: list[dict] = []

    for idx, row in enumerate(rows):
        if use_prose:
            text = _row_to_prose(row)
        else:
            data_line = "\t".join(
                str(row.get(col, "")) for col in fieldnames
            )
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

        # total_chunks patched below once summaries are counted
        metadata = build_metadata(
            source_file=source_file,
            chunk_index=idx,
            total_chunks=0,
            extra=extra,
        )
        result.append({"text": text, "metadata": metadata})

    # Append pre-aggregated summary chunks
    if use_summaries:
        summaries = _build_summary_chunks(rows, source_file, len(result))
        result.extend(summaries)

    # Patch total_chunks now that the full list is known
    total = len(result)
    for chunk in result:
        chunk["metadata"]["total_chunks"] = total

    return result
