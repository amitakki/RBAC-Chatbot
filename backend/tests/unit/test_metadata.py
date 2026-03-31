"""
Unit tests for ingest/chunkers/metadata.py

RC-77: finance cannot access marketing docs; executive can access all 10 docs.
"""

import pytest

from ingest.chunkers.metadata import (
    RBAC_ACCESS_MATRIX,
    build_metadata,
    can_access,
    get_allowed_roles,
)

ALL_DOCS = list(RBAC_ACCESS_MATRIX.keys())


class TestGetAllowedRoles:
    def test_finance_docs_include_finance_and_executive(self):
        roles = get_allowed_roles("financial_summary.md")
        assert "finance" in roles
        assert "executive" in roles

    def test_hr_doc_excludes_finance(self):
        roles = get_allowed_roles("hr_data.csv")
        assert "finance" not in roles

    def test_marketing_doc_excludes_hr(self):
        roles = get_allowed_roles("marketing_report_2024.md")
        assert "hr" not in roles

    def test_engineering_doc_only_engineering_and_executive(self):
        roles = get_allowed_roles("engineering_master_doc.md")
        assert set(roles) == {"engineering", "executive"}

    def test_unknown_file_returns_empty(self):
        assert get_allowed_roles("nonexistent.md") == []


class TestCanAccess:
    def test_finance_can_access_financial_summary(self):
        assert can_access("financial_summary.md", "finance") is True

    def test_finance_cannot_access_marketing_docs(self):
        assert can_access("marketing_report_2024.md", "finance") is False

    def test_executive_can_access_all_ten_docs(self):
        for doc in ALL_DOCS:
            assert can_access(doc, "executive") is True, f"executive blocked from {doc}"

    def test_hr_can_access_employee_handbook(self):
        assert can_access("employee_handbook.md", "hr") is True

    def test_hr_cannot_access_engineering_doc(self):
        assert can_access("engineering_master_doc.md", "hr") is False

    def test_marketing_cannot_access_hr_data(self):
        assert can_access("hr_data.csv", "marketing") is False


class TestBuildMetadata:
    def test_required_fields_present(self):
        meta = build_metadata("financial_summary.md", chunk_index=0, total_chunks=10)
        for field in (
            "doc_id", "source_file", "allowed_roles", "department",
            "sensitivity", "chunk_index", "total_chunks", "ingested_at",
        ):
            assert field in meta, f"Missing field: {field}"

    def test_doc_id_includes_chunk_index(self):
        meta = build_metadata("financial_summary.md", chunk_index=3, total_chunks=10)
        assert "003" in meta["doc_id"]

    def test_source_file_preserved(self):
        meta = build_metadata("hr_data.csv", chunk_index=0, total_chunks=5)
        assert meta["source_file"] == "hr_data.csv"

    def test_sensitivity_high_for_finance(self):
        meta = build_metadata("quarterly_financial_report.md", chunk_index=0, total_chunks=1)
        assert meta["sensitivity"] == "high"

    def test_sensitivity_internal_for_engineering(self):
        meta = build_metadata("engineering_master_doc.md", chunk_index=0, total_chunks=1)
        assert meta["sensitivity"] == "internal"

    def test_extra_fields_merged(self):
        meta = build_metadata(
            "financial_summary.md",
            chunk_index=1,
            total_chunks=5,
            extra={"section_h1": "Overview"},
        )
        assert meta["section_h1"] == "Overview"

    def test_allowed_roles_correct_for_hr(self):
        meta = build_metadata("hr_data.csv", chunk_index=0, total_chunks=1)
        assert set(meta["allowed_roles"]) == {"hr", "executive"}
