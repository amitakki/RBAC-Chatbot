"""
Unit tests for ingest/chunkers/csv_chunker.py
"""

import csv
import io
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
    "Ahmedabad,1991-04-03,2018-11-20,FINEMP1006,1332478.37,22,11,99.31,3,2024-05-21"
)
_HR_ROW_2 = (
    "FINEMP1001,Isha Chowdhury,Credit Officer,Finance,ic@fintechco.com,"
    "Pune,1995-09-21,2021-05-20,FINEMP1005,1491158.23,8,3,85.15,5,2024-01-20"
)


@pytest.fixture()
def hr_csv(tmp_path: Path) -> Path:
    content = "\n".join([_HR_HEADER, _HR_ROW_1, _HR_ROW_2])
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


class TestChunkCsv:
    def test_one_chunk_per_data_row(self, hr_csv: Path):
        chunks = chunk_csv(hr_csv)
        assert len(chunks) == 2  # two data rows

    def test_chunk_text_contains_header(self, hr_csv: Path):
        chunks = chunk_csv(hr_csv)
        for chunk in chunks:
            assert "employee_id" in chunk["text"]

    def test_chunk_text_contains_row_data(self, hr_csv: Path):
        chunks = chunk_csv(hr_csv)
        assert "FINEMP1000" in chunks[0]["text"]
        assert "FINEMP1001" in chunks[1]["text"]

    def test_row_id_set_to_employee_id(self, hr_csv: Path):
        chunks = chunk_csv(hr_csv)
        assert chunks[0]["metadata"]["row_id"] == "FINEMP1000"
        assert chunks[1]["metadata"]["row_id"] == "FINEMP1001"

    def test_pii_flag_set_for_hr_data(self, hr_csv: Path):
        chunks = chunk_csv(hr_csv)
        for chunk in chunks:
            assert chunk["metadata"]["contains_pii"] is True
            assert "salary" in chunk["metadata"]["pii_fields"]
            assert "date_of_birth" in chunk["metadata"]["pii_fields"]
            assert "performance_rating" in chunk["metadata"]["pii_fields"]

    def test_allowed_roles_hr_and_executive(self, hr_csv: Path):
        chunks = chunk_csv(hr_csv)
        for chunk in chunks:
            assert set(chunk["metadata"]["allowed_roles"]) == {"hr", "executive"}

    def test_non_pii_csv_has_no_pii_flags(self, plain_csv: Path):
        chunks = chunk_csv(plain_csv)
        for chunk in chunks:
            assert "contains_pii" not in chunk["metadata"]

    def test_chunk_index_sequential(self, hr_csv: Path):
        chunks = chunk_csv(hr_csv)
        for i, chunk in enumerate(chunks):
            assert chunk["metadata"]["chunk_index"] == i

    def test_total_chunks_correct(self, hr_csv: Path):
        chunks = chunk_csv(hr_csv)
        for chunk in chunks:
            assert chunk["metadata"]["total_chunks"] == 2

    def test_source_file_in_metadata(self, hr_csv: Path):
        chunks = chunk_csv(hr_csv)
        for chunk in chunks:
            assert chunk["metadata"]["source_file"] == "hr_data.csv"
