"""Run Ragas evaluation metrics over a generated answers file.

Reads the latest (or specified) answers_<timestamp>.json produced by
generate_answers.py, computes five Ragas metrics using the Groq LLM and
HuggingFace embeddings, checks each metric against a threshold, and
writes a ragas_<timestamp>.json report.

Exit code:
    0  all metrics meet or exceed their thresholds
    1  one or more metrics fall below threshold (CI gate failure)

Usage (from project root):
    cd backend && uv run --extra evals python ../evals/run_ragas.py
    cd backend && uv run --extra evals python ../evals/run_ragas.py \\
        --answers-file ../evals/report/answers_20260401T120000Z.json

RC-41, RC-81, RC-82
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path so `evals.utils` resolves when run from backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.utils import REPORT_DIR  # noqa: E402

# ---------------------------------------------------------------------------
# Threshold definitions (requirements.md §8.2)
# ---------------------------------------------------------------------------

THRESHOLDS: dict[str, float] = {
    "faithfulness":       0.80,
    "answer_relevancy":   0.75,
    "context_precision":  0.70,
    "context_recall":     0.70,
    "answer_correctness": 0.75,
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Ragas metrics over a generated answers file.")
    p.add_argument(
        "--answers-file",
        type=Path,
        default=None,
        help="Path to answers JSON file. If omitted, uses the latest answers_*.json in evals/report/",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=REPORT_DIR,
        help="Directory to write the ragas report JSON (default: evals/report/)",
    )
    return p.parse_args()


def resolve_answers_file(answers_file: Path | None) -> Path:
    if answers_file is not None:
        if not answers_file.exists():
            sys.exit(f"ERROR: answers file not found: {answers_file}")
        return answers_file

    candidates = sorted(REPORT_DIR.glob("answers_*.json"), reverse=True)
    if not candidates:
        sys.exit(
            "ERROR: No answers_*.json found in evals/report/. "
            "Run generate_answers.py first."
        )
    latest = candidates[0]
    print(f"Using latest answers file: {latest}")
    return latest


def load_answers(path: Path) -> list[dict]:
    with path.open() as fh:
        data = json.load(fh)
    results = data.get("results", [])
    # Keep only pairs that have a ground_truth and a non-empty answer
    valid = [r for r in results if r.get("ground_truth") and r.get("answer")]
    skipped = len(results) - len(valid)
    if skipped:
        print(f"  Skipping {skipped} result(s) with missing ground_truth or empty answer.")
    return valid


def build_ragas_dataset(results: list[dict]):
    """Build a ragas EvaluationDataset from the answers list."""
    from ragas import EvaluationDataset
    from ragas.dataset_schema import SingleTurnSample

    samples = []
    for r in results:
        contexts = r.get("contexts", [])
        # Ensure contexts is a non-empty list of strings; fall back to source_docs
        if not contexts:
            contexts = r.get("source_docs", [])
        if not contexts:
            contexts = ["[no context retrieved]"]

        samples.append(
            SingleTurnSample(
                user_input=r["question"],
                response=r["answer"],
                retrieved_contexts=contexts,
                reference=r["ground_truth"],
            )
        )

    return EvaluationDataset(samples=samples)


def build_metrics(llm, embeddings):
    """Instantiate the five Ragas metrics with shared LLM and embeddings."""
    from ragas.metrics import (
        AnswerCorrectness,
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    return [
        Faithfulness(llm=llm),
        AnswerRelevancy(llm=llm, embeddings=embeddings),
        ContextPrecision(llm=llm),
        ContextRecall(llm=llm),
        AnswerCorrectness(llm=llm),
    ]


def run(answers_file_arg: Path | None, output_dir: Path) -> bool:
    answers_path = resolve_answers_file(answers_file_arg)
    print(f"\nLoading answers from: {answers_path}")
    results = load_answers(answers_path)
    print(f"Evaluating {len(results)} samples with Ragas...\n")

    # --- configure LLM and embeddings ---
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        sys.exit("ERROR: GROQ_API_KEY environment variable is not set.")

    from langchain_groq import ChatGroq
    from langchain_huggingface import HuggingFaceEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper

    llm = LangchainLLMWrapper(
        ChatGroq(model="llama-3.3-70b-versatile", api_key=groq_api_key)
    )
    embeddings = LangchainEmbeddingsWrapper(
        HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    )

    # --- build dataset and metrics ---
    from ragas import evaluate

    dataset = build_ragas_dataset(results)
    metrics = build_metrics(llm, embeddings)

    # --- run evaluation ---
    print("Running Ragas evaluate()... (this may take a few minutes)")
    eval_result = evaluate(dataset=dataset, metrics=metrics)

    # --- extract per-metric scores ---
    scores_df = eval_result.to_pandas()
    metric_names = [
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "answer_correctness",
    ]
    scores: dict[str, float] = {}
    for name in metric_names:
        if name in scores_df.columns:
            scores[name] = float(scores_df[name].mean())
        else:
            scores[name] = 0.0
            print(f"  WARNING: metric '{name}' not found in results — defaulting to 0.0")

    # --- threshold check ---
    passed: dict[str, bool] = {m: scores[m] >= THRESHOLDS[m] for m in metric_names}
    overall_pass = all(passed.values())

    # --- print results table ---
    print("\n" + "=" * 60)
    print(f"{'Metric':<25} {'Score':>7}  {'Threshold':>9}  {'Result':>6}")
    print("-" * 60)
    for m in metric_names:
        result_str = "PASS" if passed[m] else "FAIL"
        print(f"{m:<25} {scores[m]:>7.4f}  {THRESHOLDS[m]:>9.2f}  {result_str:>6}")
    print("=" * 60)
    print(f"\nOverall: {'PASS' if overall_pass else 'FAIL'}")

    # --- write report ---
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = output_dir / f"ragas_{timestamp}.json"

    report = {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "answers_file": str(answers_path),
        "num_samples": len(results),
        "scores": scores,
        "thresholds": THRESHOLDS,
        "passed": passed,
        "overall_pass": overall_pass,
    }
    out_path.write_text(json.dumps(report, indent=2))
    print(f"Report written to: {out_path}\n")

    return overall_pass


def main() -> None:
    args = parse_args()
    passed = run(args.answers_file, args.output_dir)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
