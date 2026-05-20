#!/usr/bin/env python3
"""Smoke-test the local Care Compass loop."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from care_compass.aion import build_aion_context  # noqa: E402
from care_compass.config import (  # noqa: E402
    DEFAULT_ALLOWED_REQUEST,
    DEFAULT_BLOCKED_REQUEST,
    DEFAULT_MODEL,
)
from care_compass.errors import ValidationError  # noqa: E402
from care_compass.model import call_ollama, compact_policy_context  # noqa: E402
from care_compass.records import append_decision_log, forensic_record  # noqa: E402
from care_compass.rules import gate_request  # noqa: E402


def print_artifact_summary(evidence: list[dict]) -> None:
    print("== Aion verification ==")
    for artifact in evidence:
        print(
            f"valid {artifact['artifact']} versions={artifact['version_count']} "
            f"file_id={artifact['file_id']}"
        )


def build_record(
    *,
    model: str,
    user_text: str,
    gate: dict,
    aion_evidence: list[dict],
    model_result: dict | None,
    include_raw: bool,
    include_redacted_preview: bool,
) -> dict:
    return forensic_record(
        model=model,
        user_text=user_text,
        gate=gate,
        aion_evidence=aion_evidence,
        model_result=model_result,
        include_raw=include_raw,
        include_redacted_preview=include_redacted_preview,
    )


def validate_blocked_request(
    args: argparse.Namespace,
    aion_evidence: list[dict],
) -> None:
    blocked_gate = gate_request(args.blocked_request)
    blocked_record = build_record(
        model=args.model,
        user_text=args.blocked_request,
        gate=blocked_gate,
        aion_evidence=aion_evidence,
        model_result=None,
        include_raw=args.include_raw_in_log,
        include_redacted_preview=args.include_redacted_preview,
    )
    print(
        json.dumps(
            {
                "request_sha256": blocked_record["request_evidence"]["sha256"],
                "gate": blocked_gate,
                "decision_id": blocked_record["decision_id"],
            },
            indent=2,
        )
    )
    if blocked_gate["decision"] == "allow":
        raise ValidationError("blocked-request unexpectedly passed the gate")
    if args.decision_log:
        append_decision_log(args.decision_log, blocked_record)
    if args.print_forensic_records:
        print(json.dumps(blocked_record, indent=2, sort_keys=True))


def validate_allowed_request(
    args: argparse.Namespace,
    payloads: dict[str, str],
    aion_evidence: list[dict],
) -> None:
    allowed_gate = gate_request(args.allowed_request)
    print(json.dumps({"gate": allowed_gate}, indent=2))
    if allowed_gate["decision"] != "allow":
        raise ValidationError("allowed-request unexpectedly failed the gate")

    if args.skip_ollama:
        print("\n== Ollama generation skipped ==")
        allowed_record = build_record(
            model=args.model,
            user_text=args.allowed_request,
            gate=allowed_gate,
            aion_evidence=aion_evidence,
            model_result=None,
            include_raw=args.include_raw_in_log,
            include_redacted_preview=args.include_redacted_preview,
        )
    else:
        print(f"\n== Ollama generation ({args.model}) ==")
        response = call_ollama(
            args.model,
            args.allowed_request,
            compact_policy_context(payloads),
        )
        allowed_record = build_record(
            model=args.model,
            user_text=args.allowed_request,
            gate=allowed_gate,
            aion_evidence=aion_evidence,
            model_result=response,
            include_raw=args.include_raw_in_log,
            include_redacted_preview=args.include_redacted_preview,
        )
        print(response["content"].strip())

    if args.decision_log:
        append_decision_log(args.decision_log, allowed_record)
    if args.print_forensic_records:
        print(json.dumps(allowed_record, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--allowed-request", default=DEFAULT_ALLOWED_REQUEST)
    parser.add_argument("--blocked-request", default=DEFAULT_BLOCKED_REQUEST)
    parser.add_argument("--decision-log", type=Path)
    parser.add_argument("--include-raw-in-log", action="store_true")
    parser.add_argument("--include-redacted-preview", action="store_true")
    parser.add_argument("--print-forensic-records", action="store_true")
    parser.add_argument("--skip-ollama", action="store_true")
    args = parser.parse_args()

    payloads, aion_evidence = build_aion_context()
    print_artifact_summary(aion_evidence)
    print("\n== Deterministic gate ==")
    validate_blocked_request(args, aion_evidence)
    validate_allowed_request(args, payloads, aion_evidence)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
