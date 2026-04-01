"""Shared utilities for the FinSolve evaluation suite.

All eval scripts import from here for HTTP helpers, static credentials,
and the golden dataset path.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Static test credentials (matches backend/app/auth/service.py _USER_STORE)
# ---------------------------------------------------------------------------

CREDENTIALS: dict[str, tuple[str, str]] = {
    "finance":     ("alice_finance",     "finance123"),
    "hr":          ("bob_hr",            "hr123"),
    "marketing":   ("charlie_marketing", "marketing123"),
    "engineering": ("diana_engineering", "engineering123"),
    "executive":   ("eve_executive",     "executive123"),
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

GOLDEN_DATASET_PATH = Path(__file__).parent.parent / "data" / "eval" / "golden_dataset.json"
REPORT_DIR = Path(__file__).parent / "report"


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def login(base_url: str, username: str, password: str) -> str:
    """POST /auth/login and return the access_token string.

    Raises httpx.HTTPStatusError on non-2xx responses.
    """
    resp = httpx.post(
        f"{base_url}/auth/login",
        json={"username": username, "password": password},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def chat(
    base_url: str,
    question: str,
    token: str,
    session_id: str | None = None,
) -> dict:
    """POST /chat with Bearer token and return the full response dict.

    Returns the parsed JSON on HTTP 200.
    Raises httpx.HTTPStatusError on non-2xx responses (callers handle 400/429).
    """
    payload: dict = {"question": question}
    if session_id is not None:
        payload["session_id"] = session_id

    resp = httpx.post(
        f"{base_url}/chat/",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def chat_raw(
    base_url: str,
    question: str,
    token: str,
    session_id: str | None = None,
) -> httpx.Response:
    """POST /chat and return the raw httpx.Response (no raise_for_status).

    Use this when you need to inspect non-200 status codes.
    """
    payload: dict = {"question": question}
    if session_id is not None:
        payload["session_id"] = session_id

    return httpx.post(
        f"{base_url}/chat/",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )


def load_golden_dataset() -> dict:
    """Load and return the parsed golden_dataset.json."""
    with GOLDEN_DATASET_PATH.open() as fh:
        return json.load(fh)
