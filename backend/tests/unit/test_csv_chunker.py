"""
Unit tests for ingest/chunkers/csv_chunker.py
"""

from pathlib import Path

import pytest

from ingest.chunkers.csv_chunker import chunk_csv

# Minimal CSV with the same columns as the real hr_data.csv
_HR_HEADER = (
    "employee_id,full_name,role,department,email,location,"
    "date_of_birth,date_of_joining,manager_id,salary,leave_balance,"
    "leaves_taken,attendance_pct,performance_rating,last_review_date"
)

_HR_ROW_1 = (
    "FINEMP1000,Aadhya Patel,Sales Manager,Sales,ap@fintechco.com,"
    "Ahmedabad,1991-04-03,2018-11-20,FINEMP1006,"
    "1332478.37,22,11,99.31,3,2024-05-21"
)
_HR_ROW_2 = (
    "FINEMP1001,Isha Chowdhury,Credit Officer,Finance,ic@fintechco.com,"
    "Pune,1995-09-21,2021-05-20,FINEMP1005,1491158.23,8,3,85.15,5,2024-01-20"
)
# Third row — same location as row 1 to test grouping
_HR_ROW_3 = (
    "FINEMP1002,Sakshi Malhotra,Relationship Manager,Sales,"
    "sm@fintechco.com,Ahmedabad,1993-08-05,2023-04-17,FINEMP1006,"
    "1448927.95,21,7,86.31,2,2025-02-11"
)


@pytest.fixture()
def hr_csv(tmp_path: Path) -> Path:
    content = "\n".join([_HR_HEADER, _HR_ROW_1, _HR_ROW_2])
    p = tmp_path / "hr_data.csv"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture()
def hr_csv_multi(tmp_path: Path) -> Path:
    """Three rows: two in Ahmedabad, one in Pune; two in Sales, one Finance."""
    content = "\n".join([_HR_HEADER, _HR_ROW_1, _HR_ROW_2, _HR_ROW_3])
    p = tmp_path / "hr_data.csv"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture()
def plain_csv(tmp_path: Path) -> Path:
    """Non-PII CSV for testing generic chunking."""
    content = "product_id,name,price\nP001,Widget,9.99\nP002,Gadget,49.99"
    p = tmp_path / "products.csv"
    p.write_text(content, encoding="utf-8")
    return p


def _row_chunks(chunks: list[dict]) -> list[dict]:
    """Return only per-row chunks (exclude summary chunks)."""
    return [c for c in chunks if "row_id" in c["metadata"]]


def _summary_chunks(chunks: list[dict]) -> list[dict]:
    """Return only aggregation summary chunks."""
    return [c for c in chunks if "summary_type" in c["metadata"]]


class TestChunkCsv:
    def test_row_chunks_one_per_data_row(self, hr_csv: Path):
        chunks = chunk_csv(hr_csv)
        assert len(_row_chunks(chunks)) == 2

    def test_chunk_text_is_prose_for_hr(self, hr_csv: Path):
        for chunk in _row_chunks(chunk_csv(hr_csv)):
            assert "works as" in chunk["text"], (
                "HR chunks should use natural-language prose serialization"
            )

    def test_chunk_text_contains_row_data(self, hr_csv: Path):
        rows = _row_chunks(chunk_csv(hr_csv))
        assert "FINEMP1000" in rows[0]["text"]
        assert "FINEMP1001" in rows[1]["text"]

    def test_row_id_set_to_employee_id(self, hr_csv: Path):
        rows = _row_chunks(chunk_csv(hr_csv))
        assert rows[0]["metadata"]["row_id"] == "FINEMP1000"
        assert rows[1]["metadata"]["row_id"] == "FINEMP1001"

    def test_pii_flag_set_for_hr_data(self, hr_csv: Path):
        for chunk in _row_chunks(chunk_csv(hr_csv)):
            assert chunk["metadata"]["contains_pii"] is True
            assert "salary" in chunk["metadata"]["pii_fields"]
            assert "date_of_birth" in chunk["metadata"]["pii_fields"]
            assert "performance_rating" in chunk["metadata"]["pii_fields"]

    def test_allowed_roles_hr_and_executive(self, hr_csv: Path):
        for chunk in chunk_csv(hr_csv):
            assert set(chunk["metadata"]["allowed_roles"]) == {
                "hr", "executive"
            }

    def test_non_pii_csv_has_no_pii_flags(self, plain_csv: Path):
        for chunk in chunk_csv(plain_csv):
            assert "contains_pii" not in chunk["metadata"]

    def test_non_hr_csv_uses_tsv_format(self, plain_csv: Path):
        for chunk in chunk_csv(plain_csv):
            assert "product_id" in chunk["text"], (
                "Non-HR CSVs should still use TSV header+row format"
            )

    def test_chunk_index_sequential(self, hr_csv: Path):
        chunks = chunk_csv(hr_csv)
        for i, chunk in enumerate(chunks):
            assert chunk["metadata"]["chunk_index"] == i

    def test_total_chunks_consistent(self, hr_csv: Path):
        chunks = chunk_csv(hr_csv)
        total = len(chunks)
        for chunk in chunks:
            assert chunk["metadata"]["total_chunks"] == total

    def test_source_file_in_metadata(self, hr_csv: Path):
        for chunk in chunk_csv(hr_csv):
            assert chunk["metadata"]["source_file"] == "hr_data.csv"

    def test_non_hr_csv_has_no_summary_chunks(self, plain_csv: Path):
        chunks = chunk_csv(plain_csv)
        assert _summary_chunks(chunks) == [], (
            "Non-HR CSVs should not have summary chunks"
        )

    # ------------------------------------------------------------------
    # Aggregation summary chunk tests
    # ------------------------------------------------------------------

    def test_location_summary_chunk_exists(self, hr_csv_multi: Path):
        summaries = _summary_chunks(chunk_csv(hr_csv_multi))
        loc_summaries = [
            s for s in summaries
            if s["metadata"]["summary_type"] == "location"
        ]
        assert loc_summaries, "Expected at least one location summary chunk"

    def test_location_summary_correct_count(self, hr_csv_multi: Path):
        summaries = _summary_chunks(chunk_csv(hr_csv_multi))
        ahmedabad = next(
            s for s in summaries
            if s["metadata"].get("summary_group") == "Ahmedabad"
        )
        assert ahmedabad["metadata"]["summary_count"] == 2
        assert "2 total" in ahmedabad["text"]

    def test_location_summary_lists_employees(self, hr_csv_multi: Path):
        summaries = _summary_chunks(chunk_csv(hr_csv_multi))
        ahmedabad = next(
            s for s in summaries
            if s["metadata"].get("summary_group") == "Ahmedabad"
        )
        assert "Aadhya Patel" in ahmedabad["text"]
        assert "Sakshi Malhotra" in ahmedabad["text"]

    def test_department_summary_chunk_exists(self, hr_csv_multi: Path):
        summaries = _summary_chunks(chunk_csv(hr_csv_multi))
        dept_summaries = [
            s for s in summaries
            if s["metadata"]["summary_type"] == "department"
        ]
        assert dept_summaries, "Expected at least one department summary chunk"

    def test_department_summary_correct_count(self, hr_csv_multi: Path):
        summaries = _summary_chunks(chunk_csv(hr_csv_multi))
        sales = next(
            s for s in summaries
            if s["metadata"].get("summary_group") == "Sales"
        )
        assert sales["metadata"]["summary_count"] == 2
        assert "2 total" in sales["text"]

    def test_role_summary_chunk_exists(self, hr_csv_multi: Path):
        summaries = _summary_chunks(chunk_csv(hr_csv_multi))
        role_summaries = [
            s for s in summaries
            if s["metadata"]["summary_type"] == "role"
        ]
        assert role_summaries, "Expected at least one role summary chunk"

    def test_role_summary_lists_employees(self, hr_csv_multi: Path):
        summaries = _summary_chunks(chunk_csv(hr_csv_multi))
        sales_mgr = next(
            s for s in summaries
            if s["metadata"].get("summary_group") == "Sales Manager"
        )
        assert "Aadhya Patel" in sales_mgr["text"]
        assert "Sales Manager" in sales_mgr["text"]

    def test_manager_summary_chunk_exists(self, hr_csv_multi: Path):
        summaries = _summary_chunks(chunk_csv(hr_csv_multi))
        mgr_summaries = [
            s for s in summaries
            if s["metadata"]["summary_type"] == "manager"
        ]
        assert mgr_summaries, "Expected at least one manager summary chunk"

    def test_manager_summary_uses_name(self, hr_csv_multi: Path):
        summaries = _summary_chunks(chunk_csv(hr_csv_multi))
        mgr_chunk = next(
            s for s in summaries
            if s["metadata"]["summary_type"] == "manager"
        )
        # Manager name (not just ID) should appear in the chunk text
        assert "Direct reports of" in mgr_chunk["text"]

    def test_rating_summary_chunk_exists(self, hr_csv_multi: Path):
        summaries = _summary_chunks(chunk_csv(hr_csv_multi))
        rating_summaries = [
            s for s in summaries
            if s["metadata"]["summary_type"] == "rating"
        ]
        assert rating_summaries, "Expected at least one rating summary chunk"

    def test_rating_summary_includes_label(self, hr_csv_multi: Path):
        summaries = _summary_chunks(chunk_csv(hr_csv_multi))
        rating_chunks = {
            s["metadata"]["summary_group"]: s
            for s in summaries
            if s["metadata"]["summary_type"] == "rating"
        }
        # Row 1 has rating 3, row 2 has rating 5, row 3 has rating 2
        assert "Meets Expectations" in rating_chunks["3"]["text"]
        assert "Outstanding" in rating_chunks["5"]["text"]
        assert "Below Expectations" in rating_chunks["2"]["text"]
