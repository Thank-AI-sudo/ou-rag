r"""Run a small, auditable evaluation of the local OU RAG /api/chat API.

From project root:
  .\.venv\Scripts\python.exe -m backend.evaluation.run_evaluation
  .\.venv\Scripts\python.exe -m backend.evaluation.run_evaluation --all

This script checks citation *format*, not factual accuracy. Manually verify against sources.
"""

import argparse
import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
QUESTIONS_PATH = HERE / "eval_questions.json"
RESULTS_DIR = HERE / "results"
CITATION_RE = re.compile(r"\[(\d+)\]")


def evaluate(question_item: dict, api_url: str, top_k: int, top_n: int, timeout: int) -> dict:
    record = {**question_item, "http_status": None, "latency_seconds": None,
              "answer": "", "sources": [], "reranking_used": None,
              "retrieved_count": None, "citation_numbers": [],
              "invalid_citations": [], "unused_source_numbers": [],
              "citation_structure_ok": False, "error": "",
              "manual_factual_accuracy": "", "manual_groundedness": "",
              "manual_answer_completeness": "", "manual_notes": ""}
    started = time.perf_counter()
    try:
        response = requests.post(
            api_url,
            json={"question": question_item["question"], "top_k": top_k, "top_n": top_n},
            timeout=timeout,
        )
        record["http_status"] = response.status_code
        response.raise_for_status()
        data = response.json()
        record["answer"] = data.get("answer", "")
        record["sources"] = data.get("sources", [])
        record["reranking_used"] = data.get("reranking_used")
        record["retrieved_count"] = data.get("retrieved_count")
        cited = sorted({int(x) for x in CITATION_RE.findall(record["answer"])})
        returned = {s.get("number") for s in record["sources"]}
        record["citation_numbers"] = cited
        record["invalid_citations"] = sorted(set(cited) - returned)
        record["unused_source_numbers"] = sorted(x for x in returned - set(cited) if isinstance(x, int))
        record["citation_structure_ok"] = (
            not record["invalid_citations"] and not record["unused_source_numbers"]
        )
    except (requests.RequestException, ValueError, TypeError) as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        if 'response' in locals() and response is not None:
            record["error"] += " | response: " + response.text[:400]
    finally:
        record["latency_seconds"] = round(time.perf_counter() - started, 3)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate OU RAG answers via local FastAPI")
    parser.add_argument("--all", action="store_true", help="Run all 20 tests (uses API quota)")
    parser.add_argument("--limit", type=int, default=3, help="Tests to run (default: 3)")
    parser.add_argument("--api", default="http://127.0.0.1:8000/api/chat")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--top-n", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between requests")
    args = parser.parse_args()

    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8-sig"))
    count = len(questions) if args.all else max(0, min(args.limit, len(questions)))
    items = questions[:count]
    results = []
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = RESULTS_DIR / f"eval_{stamp}.json"
    csv_path = RESULTS_DIR / f"eval_{stamp}.csv"

    print(f"Running {len(items)} / {len(questions)} evaluation questions")
    for i, question in enumerate(items, start=1):
        result = evaluate(question, args.api, args.top_k, args.top_n, args.timeout)
        results.append(result)
        status = "OK" if result["http_status"] == 200 else "ERROR"
        print(f"[{i}/{len(items)}] {question['id']}: {status} | {result['latency_seconds']}s | citations={result['citation_numbers']}")
        if result["error"]:
            print("  ", result["error"][:300])
        # Save partial progress after each request.
        json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        if i < len(items) and args.delay > 0:
            time.sleep(args.delay)

    columns = ["id", "category", "question", "expected_behavior", "source_hint",
               "http_status", "latency_seconds", "answer", "retrieved_count",
               "reranking_used", "citation_numbers", "invalid_citations",
               "unused_source_numbers", "citation_structure_ok", "source_count",
               "missing_source_url_count", "error", "manual_factual_accuracy",
               "manual_groundedness", "manual_answer_completeness", "manual_notes"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for result in results:
            row = {k: result.get(k, "") for k in columns}
            row["source_count"] = len(result["sources"])
            row["missing_source_url_count"] = sum(not s.get("url") for s in result["sources"])
            for col in ("citation_numbers", "invalid_citations", "unused_source_numbers"):
                row[col] = json.dumps(row[col], ensure_ascii=False)
            writer.writerow(row)

    success = sum(r["http_status"] == 200 for r in results)
    structurally_valid = sum(r["http_status"] == 200 and r["citation_structure_ok"] for r in results)
    print(f"\nHTTP 200: {success}/{len(results)}")
    print(f"Citation structure matches returned sources: {structurally_valid}/{success} successful responses")
    print("Factual accuracy / groundedness require manual review against source documents.")
    print(f"JSON: {json_path}")
    print(f"CSV:  {csv_path}")


if __name__ == "__main__":
    main()
