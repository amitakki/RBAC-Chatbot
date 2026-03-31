"""
Chunk metadata schema, RBAC access matrix, and metadata builder.

Every chunk stored in Qdrant carries a payload built by build_metadata().
"""

from __future__ import annotations

from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# RBAC Access Matrix — maps source filename → list of roles allowed to read it
# ---------------------------------------------------------------------------
RBAC_ACCESS_MATRIX: dict[str, list[str]] = {
    "financial_summary.md":          ["finance", "executive"],
    "quarterly_financial_report.md": ["finance", "executive"],
    "employee_handbook.md":          ["hr", "executive"],
    "hr_data.csv":                   ["hr", "executive"],
    "engineering_master_doc.md":     ["engineering", "executive"],
    "marketing_report_2024.md":      ["marketing", "executive"],
    "marketing_report_q1_2024.md":   ["marketing", "executive"],
    "marketing_report_q2_2024.md":   ["marketing", "executive"],
    "marketing_report_q3_2024.md":   ["marketing", "executive"],
    "market_report_q4_2024.md":      ["marketing", "executive"],
}

DEPARTMENT_MAP: dict[str, str] = {
    "financial_summary.md":          "finance",
    "quarterly_financial_report.md": "finance",
    "employee_handbook.md":          "hr",
    "hr_data.csv":                   "hr",
    "engineering_master_doc.md":     "engineering",
    "marketing_report_2024.md":      "marketing",
    "marketing_report_q1_2024.md":   "marketing",
    "marketing_report_q2_2024.md":   "marketing",
    "marketing_report_q3_2024.md":   "marketing",
    "market_report_q4_2024.md":      "marketing",
}

SENSITIVITY_MAP: dict[str, str] = {
    "finance":     "high",
    "hr":          "high",
    "engineering": "internal",
    "marketing":   "internal",
}


def get_allowed_roles(source_file: str) -> list[str]:
    """Return roles permitted to access chunks from source_file."""
    return RBAC_ACCESS_MATRIX.get(source_file, [])


def can_access(source_file: str, role: str) -> bool:
    """Return True if role is allowed to access source_file."""
    return role in get_allowed_roles(source_file)


def build_metadata(
    source_file: str,
    chunk_index: int,
    total_chunks: int,
    extra: dict | None = None,
) -> dict:
    """
    Build the full Qdrant payload metadata dict for a single chunk.

    Required fields are always present. Optional type-specific fields
    (section_h1, section_h2, row_id, contains_pii, pii_fields) are
    supplied via the extra dict.
    """
    department = DEPARTMENT_MAP.get(source_file, "unknown")
    sensitivity = SENSITIVITY_MAP.get(department, "internal")
    allowed_roles = get_allowed_roles(source_file)

    base_name = source_file.replace(".", "_")
    doc_id = f"{base_name}_chunk_{chunk_index:03d}"

    payload: dict = {
        "doc_id":        doc_id,
        "source_file":   source_file,
        "allowed_roles": allowed_roles,
        "department":    department,
        "sensitivity":   sensitivity,
        "chunk_index":   chunk_index,
        "total_chunks":  total_chunks,
        "ingested_at":   datetime.now(timezone.utc).isoformat(),
    }

    if extra:
        payload.update(extra)

    return payload
