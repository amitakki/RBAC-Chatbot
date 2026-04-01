"""
Output guardrails: PII redaction and source boundary enforcement (RC-95–RC-99).

Applied after the LLM generates a response:
1. PII redaction  — Presidio AnonymizerEngine rewrites sensitive entities in
   the response text before it reaches the client (RC-95, RC-96).
2. Source boundary — strips any cited source files that the user's role is
   not permitted to access; appends a fallback message when all sources are
   removed (RC-98, RC-99).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.auth.rbac import can_access

# ---------------------------------------------------------------------------
# Presidio singletons (lazy — heavy spacy model loaded once per process)
# ---------------------------------------------------------------------------

_analyzer = None
_anonymizer = None


def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        from presidio_analyzer import AnalyzerEngine
        _analyzer = AnalyzerEngine()
    return _analyzer


def _get_anonymizer():
    global _anonymizer
    if _anonymizer is None:
        from presidio_anonymizer import AnonymizerEngine
        _anonymizer = AnonymizerEngine()
    return _anonymizer


# ---------------------------------------------------------------------------
# Redaction operator configuration (RC-96)
# ---------------------------------------------------------------------------

_REDACTION_MAP: dict[str, str] = {
    "SALARY":          "[REDACTED-SALARY]",
    "DATE_OF_BIRTH":   "[REDACTED-DOB]",
    "PHONE_NUMBER":    "[REDACTED-PHONE]",
    "EMAIL_ADDRESS":   "[REDACTED-EMAIL]",
    "CREDIT_CARD":     "[REDACTED-FINANCIAL]",
    "IBAN_CODE":       "[REDACTED-FINANCIAL]",
    "US_SSN":          "[REDACTED-ID]",
    "IN_AADHAAR":      "[REDACTED-ID]",
    "IN_PAN":          "[REDACTED-ID]",
}

_ENTITIES_TO_DETECT = list(_REDACTION_MAP.keys())

_FALLBACK_MESSAGE = (
    "I could not find relevant information in your accessible documents."
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class OutputGuardResult:
    answer: str
    sources: list[str]
    pii_redacted: bool = field(default=False)


def apply_output_guard(
    answer: str,
    sources: list[str],
    user_role: str,
) -> OutputGuardResult:
    """Apply PII redaction and source boundary enforcement to an LLM response.

    Args:
        answer: Raw LLM response text.
        sources: List of source file names cited by the pipeline.
        user_role: Authenticated user's role for source boundary check.

    Returns:
        :class:`OutputGuardResult` with the cleaned answer and filtered sources.
    """
    redacted = False

    # ------------------------------------------------------------------
    # 1. PII redaction (RC-95, RC-96)
    # ------------------------------------------------------------------
    try:
        from presidio_anonymizer.entities import OperatorConfig

        analyzer = _get_analyzer()
        anonymizer = _get_anonymizer()

        results = analyzer.analyze(
            text=answer,
            entities=_ENTITIES_TO_DETECT,
            language="en",
        )

        if results:
            operators = {
                entity: OperatorConfig(
                    "replace", {"new_value": replacement}
                )
                for entity, replacement in _REDACTION_MAP.items()
            }
            anonymized = anonymizer.anonymize(
                text=answer,
                analyzer_results=results,
                operators=operators,
            )
            answer = anonymized.text
            redacted = True
    except Exception:
        pass  # redaction is best-effort; never fail the user request

    # ------------------------------------------------------------------
    # 2. Source boundary enforcement (RC-98, RC-99)
    # ------------------------------------------------------------------
    filtered_sources = [s for s in sources if can_access(s, user_role)]

    if sources and not filtered_sources:
        # All cited sources were outside the user's access scope
        answer = _FALLBACK_MESSAGE

    return OutputGuardResult(
        answer=answer,
        sources=filtered_sources,
        pii_redacted=redacted,
    )
