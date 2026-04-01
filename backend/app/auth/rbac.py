"""
RBAC enforcement helpers — role-keyed document access map (RC-76).

ROLE_DOCUMENT_ACCESS is the inverse view of ingest/chunkers/metadata.py's
RBAC_ACCESS_MATRIX (which is doc-keyed).  We build it from that single source
of truth at module load so there is no duplication.
"""

from __future__ import annotations

from ingest.chunkers.metadata import RBAC_ACCESS_MATRIX

# ---------------------------------------------------------------------------
# Build the role → [allowed source files] map from the authoritative matrix
# ---------------------------------------------------------------------------
ROLE_DOCUMENT_ACCESS: dict[str, list[str]] = {}

for _doc, _roles in RBAC_ACCESS_MATRIX.items():
    for _role in _roles:
        ROLE_DOCUMENT_ACCESS.setdefault(_role, []).append(_doc)

# Sort each list for deterministic ordering in tests / logs
for _role in ROLE_DOCUMENT_ACCESS:
    ROLE_DOCUMENT_ACCESS[_role].sort()


def get_allowed_docs(role: str) -> list[str]:
    """Return the list of source filenames accessible to *role*.

    Returns an empty list for unknown roles.
    """
    return ROLE_DOCUMENT_ACCESS.get(role, [])


def can_access(source_file: str, role: str) -> bool:
    """Return True if *role* is allowed to read chunks from *source_file*."""
    return source_file in get_allowed_docs(role)
