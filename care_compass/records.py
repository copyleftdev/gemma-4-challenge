"""Forensic decision record construction."""

from __future__ import annotations

import datetime as dt
import json
import re
import uuid
from pathlib import Path

from .config import PROJECT_ROOT, REGISTRY
from .hashing import sha256_file, sha256_text


def utc_now() -> str:
    return (
        dt.datetime.now(dt.UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def redact_preview(value: str) -> str:
    redacted = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email]", value)
    redacted = re.sub(r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b", "[ssn]", redacted)
    redacted = re.sub(
        r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "[phone]",
        redacted,
    )
    redacted = re.sub(r"\b\d{9,}\b", "[long-number]", redacted)
    return redacted[:240]


def forensic_record(
    *,
    model: str,
    user_text: str,
    gate: dict,
    aion_evidence: list[dict],
    model_result: dict | None,
    include_raw: bool,
    include_redacted_preview: bool,
) -> dict:
    model_content = model_result["content"] if model_result else ""
    record = {
        "schema": "care_compass.forensic_decision.v1",
        "decision_id": str(uuid.uuid4()),
        "created_at": utc_now(),
        "request_evidence": {
            "sha256": sha256_text(user_text),
            "raw_text_logged": include_raw,
            "redacted_preview": (
                redact_preview(user_text) if include_redacted_preview else None
            ),
        },
        "aion_evidence": {
            "registry_path": str(REGISTRY.relative_to(PROJECT_ROOT)),
            "registry_sha256": sha256_file(REGISTRY),
            "artifacts": aion_evidence,
        },
        "gate_evidence": gate,
        "model_evidence": {
            "provider": "ollama",
            "model": model,
            "called": model_result is not None,
            "output_sha256": sha256_text(model_content) if model_result else None,
            "output_json_valid": bool(
                model_result and model_result["parsed"] is not None
            ),
            "output_json_keys": (
                sorted(model_result["parsed"].keys())
                if model_result and isinstance(model_result["parsed"], dict)
                else []
            ),
            "parse_error": model_result["parse_error"] if model_result else None,
            "request_payload_sha256": (
                model_result["request_payload_sha256"] if model_result else None
            ),
            "policy_context_sha256": (
                model_result["policy_context_sha256"] if model_result else None
            ),
            "latency_ms": model_result["latency_ms"] if model_result else None,
            "ollama_metrics": (
                model_result["ollama_metrics"] if model_result else {}
            ),
            "raw_output_logged": include_raw,
        },
        "final_decision": {
            "decision": gate["decision"],
            "reason": gate["reason"],
            "selected_rule_id": gate["selected_rule"]["rule_id"],
            "selected_policy_artifact": gate["selected_rule"]["policy_artifact"],
            "model_allowed": gate["model_allowed"],
        },
    }
    if include_raw:
        record["request_evidence"]["raw_text"] = user_text
        record["model_evidence"]["raw_output"] = model_content if model_result else None
    return record


def append_decision_log(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
