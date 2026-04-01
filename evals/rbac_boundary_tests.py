"""RBAC boundary test suite — 25 cross-role access tests.

For each of the 5 roles, runs 5 queries that probe document boundaries:
- Restricted roles (finance, hr, marketing, engineering): 5 queries
  targeting forbidden document sets. PASS = sources == [] (RBAC filtered
  all chunks; no forbidden data leaked).
- Executive role: 5 positive-access queries across all doc sets.
  PASS = sources != [] (chunks retrieved; executive can see everything).

Exit code:
    0  all 25 tests pass
    1  one or more tests fail — deployment blocked

Usage (from project root):
    cd backend && uv run --extra evals python ../evals/rbac_boundary_tests.py
    cd backend && uv run --extra evals python ../evals/rbac_boundary_tests.py \\
        --base-url http://localhost:8000

RC-42, RC-121
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.utils import CREDENTIALS, chat_raw, login  # noqa: E402

# ---------------------------------------------------------------------------
# 25 hardcoded cross-role test cases
# Format: (role, question, forbidden_doc_set_hint, expect_denial)
#   expect_denial=True  → pass requires sources == []
#   expect_denial=False → pass requires sources != []  (executive positive tests)
# ---------------------------------------------------------------------------

BOUNDARY_TESTS: list[tuple[str, str, str, bool]] = [
    # --- Finance (5) — forbidden: HR, marketing, engineering ---
    ("finance", "What is the maternity leave policy?",
     "hr/employee_handbook.md", True),
    ("finance", "Who are the top performers in the Sales department?",
     "hr/hr_data.csv", True),
    ("finance", "What was the Q3 2024 marketing campaign ROI?",
     "marketing/marketing_report_q3_2024.md", True),
    ("finance", "What is the API rate limiting strategy in engineering?",
     "engineering/engineering_master_doc.md", True),
    ("finance", "How many days of paternity leave are employees entitled to?",
     "hr/employee_handbook.md", True),

    # --- HR (5) — forbidden: finance, marketing, engineering ---
    ("hr", "What was FinSolve's total revenue in 2024?",
     "finance/quarterly_financial_report.md", True),
    ("hr", "What were the Q4 gross margin figures?",
     "finance/quarterly_financial_report.md", True),
    ("hr", "What marketing campaigns ran in Q2 2024?",
     "marketing/marketing_report_q2_2024.md", True),
    ("hr", "What database does FinSolve use for primary storage?",
     "engineering/engineering_master_doc.md", True),
    ("hr", "What was the vendor expense breakdown in 2024?",
     "finance/financial_summary.md", True),

    # --- Marketing (5) — forbidden: finance, HR, engineering ---
    ("marketing", "What was FinSolve's net income in Q4 2024?",
     "finance/quarterly_financial_report.md", True),
    ("marketing", "List all employees in the Technology department.",
     "hr/hr_data.csv", True),
    ("marketing", "What is the notice period policy for resignation?",
     "hr/employee_handbook.md", True),
    ("marketing", "What are FinSolve's RTO and RPO targets?",
     "engineering/engineering_master_doc.md", True),
    ("marketing", "What were the operating cash flow figures for 2024?",
     "finance/quarterly_financial_report.md", True),

    # --- Engineering (5) — forbidden: finance, HR, marketing ---
    ("engineering", "What was the total annual revenue for 2024?",
     "finance/quarterly_financial_report.md", True),
    ("engineering", "What are the HR sick leave policies?",
     "hr/employee_handbook.md", True),
    ("engineering", "Who are the highest paid employees at FinSolve?",
     "hr/hr_data.csv", True),
    ("engineering", "What was Q3 marketing campaign ROI?",
     "marketing/marketing_report_q3_2024.md", True),
    ("engineering", "What was the gross margin trend across 2024?",
     "finance/quarterly_financial_report.md", True),

    # --- Executive (5) — positive access: should retrieve from all doc sets ---
    ("executive", "What was FinSolve's total revenue in 2024?",
     "finance/quarterly_financial_report.md", False),
    ("executive", "What is the notice period for employee resignation?",
     "hr/employee_handbook.md", False),
    ("executive", "What was the Q4 marketing campaign performance?",
     "marketing/market_report_q4_2024.md", False),
    ("executive", "What is FinSolve's primary database strategy?",
     "engineering/engineering_master_doc.md", False),
    ("executive", "What are the key financial risks identified for 2024?",
     "finance/financial_summary.md", False),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run 25 RBAC boundary tests (5 roles × 5 queries).")
    p.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the running backend (default: http://localhost:8000)",
    )
    return p.parse_args()


def acquire_tokens(base_url: str) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for role, (username, password) in CREDENTIALS.items():
        try:
            tokens[role] = login(base_url, username, password)
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            sys.exit(f"ERROR: Could not authenticate role '{role}': {exc}")
    return tokens


def run(base_url: str) -> bool:
    total = len(BOUNDARY_TESTS)
    print(f"\nRunning {total} RBAC boundary tests against {base_url}\n")

    tokens = acquire_tokens(base_url)

    results: list[tuple[int, str, str, bool, str]] = []
    current_role = None

    for idx, (role, question, doc_hint, expect_denial) in enumerate(BOUNDARY_TESTS, start=1):
        if role != current_role:
            current_role = role
            label = "deny forbidden docs" if expect_denial else "verify full access"
            print(f"  [{role.upper()}] ({label})")

        session_id = str(uuid.uuid4())
        short_q = question[:60] + ("..." if len(question) > 60 else "")
        print(f"    [{idx:02d}/25] {short_q}", end=" ", flush=True)

        try:
            resp = chat_raw(base_url, question, tokens[role], session_id)
        except httpx.RequestError as exc:
            print(f"ERROR (connection: {exc})")
            results.append((idx, role, question, False, f"connection error: {exc}"))
            continue

        if resp.status_code != 200:
            # Non-200 is unexpected for boundary tests (guardrails handle 400s)
            passed = False
            reason = f"unexpected HTTP {resp.status_code}"
        else:
            sources = resp.json().get("sources", [])
            if expect_denial:
                passed = sources == []
                reason = (
                    "sources == [] (RBAC denied, no forbidden chunks)"
                    if passed
                    else f"LEAK: sources non-empty = {sources}"
                )
            else:
                passed = sources != []
                reason = (
                    f"sources non-empty = {sources} (access granted)"
                    if passed
                    else "sources == [] (executive should have access — chunks missing?)"
                )

        label_str = "PASS" if passed else "FAIL"
        print(f"{label_str}  ({reason})")
        results.append((idx, role, question, passed, reason))

    # --- summary ---
    passed_count = sum(1 for *_, ok, _ in results if ok)
    print(f"\n{'=' * 60}")
    print(f"Result: {passed_count}/{total} tests passed\n")

    if passed_count < total:
        print("Failed tests:")
        for idx, role, question, ok, reason in results:
            if not ok:
                print(f"  [{idx:02d}] {role}: {question[:65]}")
                print(f"        Reason: {reason}")
        print()

    overall = passed_count == total
    print(f"Overall: {'PASS' if overall else 'FAIL'}")
    return overall


def main() -> None:
    args = parse_args()
    passed = run(args.base_url)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
