"""
Unit tests for app/guardrails/output_guard.py (RC-97, RC-98, RC-99).

Tests verify:
- RC-97: PII in LLM response is redacted by Presidio.
- RC-98: Source files outside the user's role are stripped.
- RC-99: When all sources are stripped, fallback message is returned.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.guardrails.output_guard import (
    _FALLBACK_MESSAGE,
    apply_output_guard,
)

# ---------------------------------------------------------------------------
# Source boundary tests (no external dependencies)
# ---------------------------------------------------------------------------

class TestSourceBoundaryEnforcement:
    def test_finance_role_strips_marketing_source(self):
        result = apply_output_guard(
            answer="Some answer.",
            sources=["marketing_report_2024.md"],
            user_role="finance",
        )
        assert result.sources == []

    def test_finance_role_keeps_financial_source(self):
        result = apply_output_guard(
            answer="Revenue was $9.4B.",
            sources=["financial_summary.md"],
            user_role="finance",
        )
        assert "financial_summary.md" in result.sources

    def test_executive_keeps_all_sources(self):
        sources = ["financial_summary.md", "hr_data.csv", "marketing_report_2024.md"]
        result = apply_output_guard(
            answer="Answer.",
            sources=sources,
            user_role="executive",
        )
        assert set(result.sources) == set(sources)

    def test_hr_role_strips_finance_source(self):
        result = apply_output_guard(
            answer="Some answer.",
            sources=["financial_summary.md"],
            user_role="hr",
        )
        assert result.sources == []

    def test_mixed_sources_only_allowed_kept(self):
        result = apply_output_guard(
            answer="Answer.",
            sources=["financial_summary.md", "hr_data.csv"],
            user_role="finance",
        )
        assert result.sources == ["financial_summary.md"]
        assert "hr_data.csv" not in result.sources


class TestFallbackOnAllSourcesStripped:
    def test_rc99_fallback_appended_when_all_stripped(self):
        result = apply_output_guard(
            answer="Here is what I found about marketing.",
            sources=["marketing_report_2024.md"],
            user_role="finance",
        )
        assert result.answer == _FALLBACK_MESSAGE
        assert result.sources == []

    def test_no_fallback_when_no_sources_provided(self):
        """Empty source list (zero-chunk result) should not trigger fallback."""
        result = apply_output_guard(
            answer="I couldn't find information.",
            sources=[],
            user_role="finance",
        )
        assert result.answer == "I couldn't find information."

    def test_no_fallback_when_some_sources_remain(self):
        result = apply_output_guard(
            answer="Revenue was $9.4B.",
            sources=["financial_summary.md", "marketing_report_2024.md"],
            user_role="finance",
        )
        assert result.answer == "Revenue was $9.4B."
        assert result.sources == ["financial_summary.md"]


# ---------------------------------------------------------------------------
# PII redaction tests (mock Presidio to avoid spacy dependency in unit tests)
# ---------------------------------------------------------------------------

class TestPiiRedaction:
    def _make_analyzer_result(self, entity_type, start, end):
        result = MagicMock()
        result.entity_type = entity_type
        result.start = start
        result.end = end
        result.score = 0.9
        return result

    def test_rc97_salary_value_redacted(self):
        """Response containing a salary figure must be redacted."""
        mock_result = self._make_analyzer_result("SALARY", 10, 17)

        with patch(
            "app.guardrails.output_guard._get_analyzer"
        ) as mock_analyzer_fn, patch(
            "app.guardrails.output_guard._get_anonymizer"
        ) as mock_anonymizer_fn:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = [mock_result]
            mock_analyzer_fn.return_value = mock_analyzer

            mock_anonymizer = MagicMock()
            mock_anon_result = MagicMock()
            mock_anon_result.text = "salary: [REDACTED-SALARY]"
            mock_anonymizer.anonymize.return_value = mock_anon_result
            mock_anonymizer_fn.return_value = mock_anonymizer

            result = apply_output_guard(
                answer="salary: 800,000",
                sources=["hr_data.csv"],
                user_role="hr",
            )

        assert "[REDACTED-SALARY]" in result.answer
        assert result.pii_redacted is True

    def test_no_pii_detected_not_redacted(self):
        with patch(
            "app.guardrails.output_guard._get_analyzer"
        ) as mock_analyzer_fn:
            mock_analyzer = MagicMock()
            mock_analyzer.analyze.return_value = []
            mock_analyzer_fn.return_value = mock_analyzer

            result = apply_output_guard(
                answer="The Q4 revenue was $9.4 billion.",
                sources=["financial_summary.md"],
                user_role="finance",
            )

        assert result.pii_redacted is False
        assert result.answer == "The Q4 revenue was $9.4 billion."

    def test_presidio_error_does_not_raise(self):
        """Redaction errors must never surface to the caller."""
        with patch(
            "app.guardrails.output_guard._get_analyzer",
            side_effect=RuntimeError("spacy unavailable"),
        ):
            result = apply_output_guard(
                answer="Some answer.",
                sources=["financial_summary.md"],
                user_role="finance",
            )
        assert result.answer == "Some answer."
