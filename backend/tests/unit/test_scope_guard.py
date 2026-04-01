"""
Unit tests for app/guardrails/scope.py (RC-92).

Tests verify:
- GUARD-005 out-of-scope AI trends query is blocked.
- FinSolve business queries are not blocked.
- Various off-topic domains trigger the blocklist.
"""

from __future__ import annotations

from app.guardrails.scope import check_scope


class TestKeywordBlocking:
    def test_guard005_ai_trends_blocked(self):
        result = check_scope("What are the latest AI trends in the industry?")
        assert result.blocked is True
        assert result.reason == "out_of_scope_rejected"

    def test_sports_cricket_blocked(self):
        result = check_scope("Who won the cricket world cup this year?")
        assert result.blocked is True
        assert result.reason == "out_of_scope_rejected"

    def test_sports_football_blocked(self):
        result = check_scope("What is the football league standings?")
        assert result.blocked is True

    def test_politics_blocked(self):
        result = check_scope("What is the current government policy on taxes?")
        assert result.blocked is True

    def test_weather_blocked(self):
        result = check_scope("What is the weather forecast for tomorrow?")
        assert result.blocked is True

    def test_recipe_blocked(self):
        result = check_scope("Give me a recipe for chocolate cake.")
        assert result.blocked is True

    def test_general_coding_help_blocked(self):
        result = check_scope("Write me a python script to sort a list.")
        assert result.blocked is True

    def test_machine_learning_trends_blocked(self):
        result = check_scope("What are machine learning trends in 2024?")
        assert result.blocked is True

    def test_case_insensitive_match(self):
        result = check_scope("CRICKET world cup results?")
        assert result.blocked is True


class TestInScopeQueries:
    def test_notice_period_not_blocked(self):
        result = check_scope("What is the notice period for employees?")
        assert result.blocked is False
        assert result.reason is None

    def test_q4_revenue_not_blocked(self):
        result = check_scope("What was FinSolve's total revenue in Q4 2024?")
        assert result.blocked is False

    def test_marketing_report_not_blocked(self):
        result = check_scope("What were the marketing campaign results in Q3?")
        assert result.blocked is False

    def test_hr_leave_policy_not_blocked(self):
        result = check_scope("What is the maternity leave policy?")
        assert result.blocked is False

    def test_engineering_architecture_not_blocked(self):
        result = check_scope("How does the engineering team handle system reliability?")
        assert result.blocked is False

    def test_financial_summary_not_blocked(self):
        result = check_scope("What was the net profit margin last quarter?")
        assert result.blocked is False

    def test_employee_handbook_not_blocked(self):
        result = check_scope("What does the employee handbook say about remote work?")
        assert result.blocked is False
