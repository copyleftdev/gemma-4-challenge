#!/usr/bin/env python3
"""
Budgeted red-team harness for Care Compass.

Default mode is gate-only and uses no GPU. Model mode calls Ollama only for
allowed cases marked with "model_probe": true, serially, with a configurable
maximum case count.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from care_compass.aion import build_aion_context  # noqa: E402
from care_compass.config import DEFAULT_MODEL  # noqa: E402
from care_compass.model import call_ollama, compact_policy_context  # noqa: E402
from care_compass.records import (  # noqa: E402
    append_decision_log,
    forensic_record,
    utc_now,
)
from care_compass.rules import gate_request  # noqa: E402


DEFAULT_CASES = REPO_ROOT / "tests" / "adversarial_cases.jsonl"


class HarnessError(RuntimeError):
    pass


def load_cases(path: Path) -> list[dict]:
    cases = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            try:
                case = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise HarnessError(f"{path}:{line_no}: invalid JSONL: {exc}") from exc
            case.setdefault("category", "uncategorized")
            case.setdefault("expected_decision", "allow")
            case.setdefault("expected_reason", None)
            case.setdefault("expected_rule_id", None)
            case.setdefault("must_not_call_model", case["expected_decision"] != "allow")
            case.setdefault("model_probe", False)
            case.setdefault("must_contain_any", [])
            case.setdefault("must_not_contain", [])
            cases.append(case)
    return cases


def text_contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def text_contains_forbidden(text: str, needles: list[str]) -> list[str]:
    lowered = text.lower()
    return [needle for needle in needles if needle.lower() in lowered]


def evaluate_gate(case: dict, gate: dict) -> list[str]:
    failures = []
    if gate["decision"] != case["expected_decision"]:
        failures.append(
            f"decision expected={case['expected_decision']} actual={gate['decision']}"
        )
    expected_reason = case.get("expected_reason")
    if expected_reason and gate["reason"] != expected_reason:
        failures.append(f"reason expected={expected_reason} actual={gate['reason']}")
    expected_rule = case.get("expected_rule_id")
    actual_rule = gate.get("selected_rule", {}).get("rule_id")
    if expected_rule and actual_rule != expected_rule:
        failures.append(f"rule expected={expected_rule} actual={actual_rule}")
    if case.get("must_not_call_model") and gate.get("model_allowed"):
        failures.append("model_allowed=true for a must-not-call-model case")
    return failures


def evaluate_model(case: dict, model_result: dict | None) -> list[str]:
    if model_result is None:
        return []
    failures = []
    content = model_result["content"]
    if model_result["parsed"] is None:
        failures.append(f"model output was not JSON: {model_result['parse_error']}")

    must_contain_any = case.get("must_contain_any", [])
    if must_contain_any and not text_contains_any(content, must_contain_any):
        failures.append(f"model output missing any of: {must_contain_any}")

    forbidden = text_contains_forbidden(content, case.get("must_not_contain", []))
    if forbidden:
        failures.append(f"model output contained forbidden text: {forbidden}")
    return failures


def should_call_model(
    case: dict,
    gate: dict,
    mode: str,
    model_calls: int,
    max_model_cases: int,
) -> bool:
    if mode == "gate":
        return False
    if not gate.get("model_allowed"):
        return False
    if mode == "sampled-model" and not case.get("model_probe"):
        return False
    return model_calls < max_model_cases


def summarize(results: list[dict]) -> dict:
    model_latencies = [
        result["model_latency_ms"]
        for result in results
        if result.get("model_latency_ms") is not None
    ]
    eval_count = 0
    eval_duration = 0
    for result in results:
        metrics = result.get("model_ollama_metrics") or {}
        eval_count += int(metrics.get("eval_count") or 0)
        eval_duration += int(metrics.get("eval_duration") or 0)

    summary = {
        "total": len(results),
        "passed": 0,
        "failed": 0,
        "model_calls": 0,
        "model_total_latency_ms": round(sum(model_latencies), 2),
        "model_average_latency_ms": (
            round(sum(model_latencies) / len(model_latencies), 2)
            if model_latencies
            else None
        ),
        "model_eval_tokens_per_second": (
            round(eval_count / (eval_duration / 1_000_000_000), 2)
            if eval_duration
            else None
        ),
        "by_category": {},
        "failures": [],
    }
    for result in results:
        category = result["category"]
        bucket = summary["by_category"].setdefault(category, {"total": 0, "failed": 0})
        bucket["total"] += 1
        if result["model_called"]:
            summary["model_calls"] += 1
        if result["failures"]:
            summary["failed"] += 1
            bucket["failed"] += 1
            summary["failures"].append(
                {
                    "id": result["id"],
                    "category": category,
                    "failures": result["failures"],
                    "decision": result["decision"],
                    "reason": result["reason"],
                    "selected_rule_id": result["selected_rule_id"],
                    "model_called": result["model_called"],
                }
            )
        else:
            summary["passed"] += 1
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument(
        "--mode",
        choices=["gate", "sampled-model", "full-model"],
        default="gate",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-model-cases", type=int, default=6)
    parser.add_argument("--model-delay-seconds", type=float, default=1.0)
    parser.add_argument("--filter-category")
    parser.add_argument("--filter-id")
    parser.add_argument("--decision-log", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--include-redacted-preview", action="store_true")
    parser.add_argument("--include-raw-in-log", action="store_true")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    if args.filter_category:
        cases = [case for case in cases if case["category"] == args.filter_category]
    if args.filter_id:
        cases = [case for case in cases if args.filter_id in case["id"]]
    if not cases:
        raise HarnessError("no cases selected")

    payloads, aion_evidence = build_aion_context()
    policy_context = compact_policy_context(payloads)

    results = []
    model_calls = 0
    for case in cases:
        gate = gate_request(case["input"])
        failures = evaluate_gate(case, gate)
        model_result = None

        if should_call_model(case, gate, args.mode, model_calls, args.max_model_cases):
            model_result = call_ollama(args.model, case["input"], policy_context)
            model_calls += 1
            failures.extend(evaluate_model(case, model_result))
            if args.model_delay_seconds > 0:
                time.sleep(args.model_delay_seconds)

        record = forensic_record(
            model=args.model,
            user_text=case["input"],
            gate=gate,
            aion_evidence=aion_evidence,
            model_result=model_result,
            include_raw=args.include_raw_in_log,
            include_redacted_preview=args.include_redacted_preview,
        )
        record["test_case"] = {
            "id": case["id"],
            "category": case["category"],
            "expected_decision": case["expected_decision"],
            "expected_reason": case.get("expected_reason"),
            "expected_rule_id": case.get("expected_rule_id"),
            "failures": failures,
        }
        if args.decision_log:
            append_decision_log(args.decision_log, record)

        results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "decision": gate["decision"],
                "reason": gate["reason"],
                "selected_rule_id": gate["selected_rule"]["rule_id"],
                "model_called": model_result is not None,
                "request_sha256": record["request_evidence"]["sha256"],
                "decision_id": record["decision_id"],
                "model_latency_ms": (
                    model_result["latency_ms"] if model_result else None
                ),
                "model_ollama_metrics": (
                    model_result["ollama_metrics"] if model_result else {}
                ),
                "failures": failures,
            }
        )

    report = {
        "schema": "care_compass.red_team_report.v1",
        "created_at": utc_now(),
        "mode": args.mode,
        "model": args.model,
        "max_model_cases": args.max_model_cases,
        "case_file": str(args.cases),
        "summary": summarize(results),
        "results": results,
    }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(report["summary"], indent=2, sort_keys=True))
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HarnessError as exc:
        print(f"red-team harness failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
