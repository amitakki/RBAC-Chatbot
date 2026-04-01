"""
Unit tests for app/auth/rbac.py (RC-77).

Verifies that ROLE_DOCUMENT_ACCESS is correctly derived from the authoritative
RBAC_ACCESS_MATRIX, and that get_allowed_docs() / can_access() behave correctly
for all five roles across all ten documents.
"""

from __future__ import annotations

import pytest

from app.auth.rbac import ROLE_DOCUMENT_ACCESS, can_access, get_allowed_docs
from ingest.chunkers.metadata import RBAC_ACCESS_MATRIX

ALL_DOCS = list(RBAC_ACCESS_MATRIX.keys())
ALL_ROLES = ["finance", "hr", "marketing", "engineering", "executive"]


class TestRoleDocumentAccess:
    def test_all_five_roles_present(self):
        for role in ALL_ROLES:
            assert role in ROLE_DOCUMENT_ACCESS, f"Role '{role}' missing from ROLE_DOCUMENT_ACCESS"

    def test_executive_has_access_to_all_ten_docs(self):
        assert len(get_allowed_docs("executive")) == 10

    def test_finance_has_exactly_two_docs(self):
        assert len(get_allowed_docs("finance")) == 2

    def test_hr_has_exactly_two_docs(self):
        assert len(get_allowed_docs("hr")) == 2

    def test_engineering_has_exactly_one_doc(self):
        assert len(get_allowed_docs("engineering")) == 1

    def test_marketing_has_exactly_five_docs(self):
        assert len(get_allowed_docs("marketing")) == 5

    def test_unknown_role_returns_empty_list(self):
        assert get_allowed_docs("superadmin") == []

    def test_role_document_access_consistent_with_matrix(self):
        """ROLE_DOCUMENT_ACCESS must be a faithful inverse of RBAC_ACCESS_MATRIX."""
        for doc, roles in RBAC_ACCESS_MATRIX.items():
            for role in roles:
                assert doc in ROLE_DOCUMENT_ACCESS[role], (
                    f"Doc '{doc}' not in ROLE_DOCUMENT_ACCESS['{role}']"
                )


class TestCanAccess:
    def test_finance_can_access_financial_summary(self):
        assert can_access("financial_summary.md", "finance") is True

    def test_finance_cannot_access_marketing_docs(self):
        assert can_access("marketing_report_2024.md", "finance") is False

    def test_finance_cannot_access_hr_data(self):
        assert can_access("hr_data.csv", "finance") is False

    def test_finance_cannot_access_engineering_doc(self):
        assert can_access("engineering_master_doc.md", "finance") is False

    def test_executive_can_access_all_ten_docs(self):
        for doc in ALL_DOCS:
            assert can_access(doc, "executive") is True, f"executive blocked from {doc}"

    def test_hr_can_access_employee_handbook(self):
        assert can_access("employee_handbook.md", "hr") is True

    def test_hr_cannot_access_engineering_doc(self):
        assert can_access("engineering_master_doc.md", "hr") is False

    def test_marketing_cannot_access_hr_data(self):
        assert can_access("hr_data.csv", "marketing") is False

    def test_engineering_cannot_access_finance_docs(self):
        assert can_access("financial_summary.md", "engineering") is False
        assert can_access("quarterly_financial_report.md", "engineering") is False

    def test_unknown_role_cannot_access_any_doc(self):
        for doc in ALL_DOCS:
            assert can_access(doc, "unknown_role") is False

    def test_unknown_doc_cannot_be_accessed_by_any_role(self):
        for role in ALL_ROLES:
            assert can_access("nonexistent.md", role) is False
