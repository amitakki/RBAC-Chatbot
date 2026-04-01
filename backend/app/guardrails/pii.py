"""
PII bulk-extraction detection guard on user input (RC-93, RC-94).

Detects queries that attempt to extract PII in bulk. Single-entity
queries (e.g. "what is Alice's salary?") are NOT blocked here — the
output guard applies redaction to those responses instead.

Block condition (RC-94):
    PII-type term present in query (salary, date of birth, phone, email, …)
    AND at least one aggregation term present (all, list, every, each, bulk, …)

Note: Presidio AnalyzerEngine is designed for detecting actual PII values
(e.g. "DOB: 1990-01-01"), not for intent classification on query text.
Keyword-based detection is used here for reliable request classification.
Presidio is used in output_guard.py to redact PII from LLM responses.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# PII-type keywords — signal a request for personal data
# ---------------------------------------------------------------------------

_PII_TYPE_TERMS: frozenset[str] = frozenset([
    "salary",
    "salaries",
    "date of birth",
    "dates of birth",
    "dob",
    "phone number",
    "phone numbers",
    "mobile number",
    "mobile numbers",
    "contact number",
    "email address",
    "email addresses",
    "personal details",
    "personal data",
    "personal information",
    "home address",
    "addresses",
    "aadhaar",
    "pan number",
    "performance rating",
    "performance ratings",
    "bank account",
    "bank details",
])

# ---------------------------------------------------------------------------
# Aggregation terms — signal bulk/plural intent
# ---------------------------------------------------------------------------

_AGGREGATION_TERMS: frozenset[str] = frozenset([
    "all",
    "list",
    "every",
    "each",
    "bulk",
    "entire",
    "everyone",
    "everybody",
    "all employees",
    "all staff",
    "all members",
])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@dataclass
class PiiInputResult:
    blocked: bool
    reason: str | None = None  # "pii_blocked" when blocked


def check_pii_input(query: str) -> PiiInputResult:
    """Detect bulk PII extraction attempts in the user query.

    Returns :class:`PiiInputResult` with ``blocked=True`` only when a
    PII-type term **and** an aggregation term are both present in the
    query, indicating a bulk personal-data extraction attempt.
    """
    lower = query.lower()

    # Check for aggregation terms first (fast path to skip PII scan)
    has_aggregation = any(term in lower for term in _AGGREGATION_TERMS)
    if not has_aggregation:
        return PiiInputResult(blocked=False)

    # Check for PII-type request terms
    has_pii_term = any(term in lower for term in _PII_TYPE_TERMS)
    if has_pii_term:
        return PiiInputResult(blocked=True, reason="pii_blocked")

    return PiiInputResult(blocked=False)
