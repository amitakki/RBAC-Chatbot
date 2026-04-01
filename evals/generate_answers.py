"""Generate answers for the golden evaluation dataset.

Reads the 30 reference-required pairs from data/eval/golden_dataset.json,
logs in as each required role, calls the /chat endpoint, and writes an
answers file to evals/report/answers_<timestamp>.json.

Usage (from project root):
    cd backend && uv run --extra evals python ../evals/generate_answers.py
    cd backend && uv run --extra evals python ../evals/generate_answers.py \\
        --base-url http://staging.example.com \\
        --output-dir ../evals/report

RC-40, RC-118, RC-119
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

# Add evals/ parent to path so `utils` resolves when run from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.utils import (  # noqa: E402
    CREDENTIALS,
    REPORT_DIR,
    chat_raw,
    load_golden_dataset,
    login,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate answers for the golden eval dataset.")
    p.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the running backend (default: http://localhost:8000)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=REPORT_DIR,
        help="Directory to write the answers JSON file (default: evals/report/)",
    )
    p.add_argument(
        "--subset",
        choices=["finance", "hr", "marketing", "engineering", "executive"],
        default=None,
        metavar="ROLE",
        help="Run only pairs for a specific role (default: all roles)",
    )
    return p.parse_args()


def acquire_tokens(base_url: str) -> dict[str, str]:
    """Login once per role and return a {role: token} mapping."""
    tokens: dict[str, str] = {}
    for role, (username, password) in CREDENTIALS.items():
        print(f"  Logging in as {username} ({role})...", end=" ", flush=True)
        try:
            token = login(base_url, username, password)
            tokens[role] = token
            print("OK")
        except httpx.HTTPStatusError as exc:
            print(f"FAILED ({exc.response.status_code})")
            sys.exit(f"ERROR: Could not authenticate role '{role}'. Aborting.")
        except httpx.RequestError as exc:
            print(f"FAILED (connection error: {exc})")
            sys.exit(f"ERROR: Backend at {base_url} is unreachable. Is it running?")
    return tokens


def run(base_url: str, output_dir: Path, subset: str | None = None) -> Path:
    dataset = load_golden_dataset()
    pairs = [p for p in dataset["pairs"] if p["eval_type"] == "reference_required"]
    if subset:
        pairs = [p for p in pairs if p["required_role"] == subset]
        print(f"Subset filter: running only '{subset}' pairs ({len(pairs)} total)")
    total = len(pairs)
    print(f"\nGenerating answers for {total} reference-required pairs against {base_url}\n")

    # --- authenticate ---
    print("Authenticating (one login per role):")
    tokens = acquire_tokens(base_url)
    print()

    # --- generate ---
    results = []
    for idx, pair in enumerate(pairs, start=1):
        role = pair["required_role"]
        token = tokens[role]
        session_id = str(uuid.uuid4())  # fresh session per question

        print(f"[{idx:02d}/{total}] {pair['id']} ({role}): {pair['question'][:70]}...", end=" ", flush=True)

        try:
            resp = chat_raw(base_url, pair["question"], token, session_id)
            if resp.status_code == 200:
                data = resp.json()
                answer = data.get("answer", "")
                contexts = data.get("sources", [])
                status = "ok"
                print(f"OK ({len(contexts)} sources)")
            else:
                answer = ""
                contexts = []
                status = f"http_{resp.status_code}"
                print(f"WARN (HTTP {resp.status_code})")
        except httpx.RequestError as exc:
            answer = ""
            contexts = []
            status = "connection_error"
            print(f"ERROR ({exc})")

        results.append(
            {
                "id": pair["id"],
                "question": pair["question"],
                "ground_truth": pair.get("ground_truth"),
                "required_role": role,
                "source_docs": pair.get("source_docs", []),
                "answer": answer,
                "contexts": contexts,
                "status": status,
            }
        )

    # --- write output ---
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = output_dir / f"answers_{timestamp}.json"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "total": total,
        "ok_count": sum(1 for r in results if r["status"] == "ok"),
        "results": results,
    }
    out_path.write_text(json.dumps(payload, indent=2))

    ok = payload["ok_count"]
    print(f"\nDone: {ok}/{total} answers generated successfully.")
    print(f"Output: {out_path}")

    if ok < total:
        print(f"WARNING: {total - ok} pair(s) failed — check the output file for details.")

    return out_path


def main() -> None:
    args = parse_args()
    run(args.base_url, args.output_dir, subset=args.subset)


if __name__ == "__main__":
    main()
