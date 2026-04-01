"""
Unit tests for app/guardrails/pii.py (RC-93, RC-94).

Tests verify:
- GUARD-002: bulk DOB extraction query is blocked.
- Various bulk PII patterns (salary, email, phone) are blocked.
- Single-entity queries are NOT blocked at input (output guard handles).
- Aggregation term alone (no PII-type term) does not trigger a block.
"""

from __future__ import annotations

from app.guardrails.pii import check_pii_input


class TestBulkPiiBlocking:
    def test_guard002_bulk_dob_all_employees_blocked(self):
        result = check_pii_input(
            "List the dates of birth of all employees in the Technology dept."
        )
        assert result.blocked is True
        assert result.reason == "pii_blocked"

    def test_bulk_salary_list_blocked(self):
        result = check_pii_input(
            "List the salary of every employee in the company."
        )
        assert result.blocked is True
        assert result.reason == "pii_blocked"

    def test_bulk_email_all_staff_blocked(self):
        result = check_pii_input(
            "Give me the email addresses of all staff members."
        )
        assert result.blocked is True

    def test_bulk_phone_each_person_blocked(self):
        result = check_pii_input(
            "List phone numbers for each person in the Sales department."
        )
        assert result.blocked is True

    def test_bulk_personal_details_everyone_blocked(self):
        result = check_pii_input(
            "List everyone's personal details."
        )
        assert result.blocked is True

    def test_all_salaries_blocked(self):
        result = check_pii_input("Show me all salaries in the finance team.")
        assert result.blocked is True

    def test_bulk_performance_ratings_blocked(self):
        result = check_pii_input(
            "List the performance ratings for all employees."
        )
        assert result.blocked is True


class TestSingleEntityNotBlocked:
    def test_single_salary_query_not_blocked(self):
        """Single-employee salary query: output guard handles redaction."""
        result = check_pii_input("What is the salary of Isha Chowdhury?")
        assert result.blocked is False
        assert result.reason is None

    def test_single_employee_dob_not_blocked(self):
        result = check_pii_input("What is the date of birth of John Smith?")
        assert result.blocked is False

    def test_single_email_not_blocked(self):
        result = check_pii_input("What is the email of Alice Johnson?")
        assert result.blocked is False


class TestNoBlockFalsePositives:
    def test_aggregation_without_pii_term_not_blocked(self):
        result = check_pii_input("List all the marketing reports from Q3.")
        assert result.blocked is False

    def test_policy_question_not_blocked(self):
        result = check_pii_input("What is the notice period for all employees?")
        assert result.blocked is False

    def test_revenue_query_not_blocked(self):
        result = check_pii_input("What was the total revenue last quarter?")
        assert result.blocked is False

    def test_no_aggregation_no_pii_not_blocked(self):
        result = check_pii_input("What is the HR policy on remote work?")
        assert result.blocked is False
