"""
Input guard orchestrator (RC-79).

Runs all input checks in order: injection → scope → PII.
First block wins. Returns a GuardResult to the caller.

Raises GuardBlockedError when the pipeline should be short-circuited so
that chat/router.py can map it to an HTTP 400 response.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.guardrails.injection import check_injection
from app.guardrails.pii import check_pii_input
from app.guardrails.scope import check_scope

# ---------------------------------------------------------------------------
# Human-readable messages per block reason
# ---------------------------------------------------------------------------

_MESSAGES: dict[str, str] = {
    "prompt_injection_blocked": (
        "Your query contains content that cannot be processed."
    ),
    "out_of_scope_rejected": (
        "This assistant is designed for FinSolve internal documents only. "
        "I'm not able to help with that query."
    ),
    "pii_blocked": (
        "This query appears to request bulk personal data and cannot be processed."
    ),
}


# ---------------------------------------------------------------------------
# Exception raised when the pipeline should be halted
# ---------------------------------------------------------------------------

class GuardBlockedError(Exception):
    """Raised by run_rag() when an input guard blocks the query."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


# ---------------------------------------------------------------------------
# Result dataclass (returned when no block occurs)
# ---------------------------------------------------------------------------

@dataclass
class GuardResult:
    blocked: bool
    reason: str | None = None
    message: str | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def check_input(query: str, role: str) -> GuardResult:  # noqa: ARG001
    """Run all input guards in sequence and return the first block result.

    Pipeline: injection → scope → PII.

    Args:
        query: The raw user query string.
        role: Authenticated user role (reserved for future role-aware guards).

    Returns:
        :class:`GuardResult` with ``blocked=False`` when the query is safe,
        or ``blocked=True`` with a populated ``reason`` and ``message``.
    """
    # 1. Prompt injection
    injection = check_injection(query)
    if injection.blocked:
        reason = injection.reason or "prompt_injection_blocked"
        return GuardResult(
            blocked=True,
            reason=reason,
            message=_MESSAGES.get(reason, _MESSAGES["prompt_injection_blocked"]),
        )

    # 2. Out-of-scope
    scope = check_scope(query)
    if scope.blocked:
        reason = scope.reason or "out_of_scope_rejected"
        return GuardResult(
            blocked=True,
            reason=reason,
            message=_MESSAGES.get(reason, _MESSAGES["out_of_scope_rejected"]),
        )

    # 3. Bulk PII extraction
    pii = check_pii_input(query)
    if pii.blocked:
        reason = pii.reason or "pii_blocked"
        return GuardResult(
            blocked=True,
            reason=reason,
            message=_MESSAGES.get(reason, _MESSAGES["pii_blocked"]),
        )

    return GuardResult(blocked=False)
