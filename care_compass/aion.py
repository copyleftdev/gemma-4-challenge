"""Aion artifact verification and payload extraction."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .config import PROJECT_ROOT, REGISTRY, SIGNED_DIR, SIGNED_FILES
from .errors import ValidationError
from .hashing import sha256_file, sha256_text


def run_command(args: list[str]) -> str:
    proc = subprocess.run(
        args,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode != 0:
        raise ValidationError(f"command failed: {' '.join(args)}\n{proc.stdout}")
    return proc.stdout


def parse_json_from_output(output: str) -> dict:
    start = output.find("{")
    end = output.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValidationError(f"expected JSON object in command output:\n{output}")
    return json.loads(output[start : end + 1])


def verify_aion_file(path: Path) -> dict:
    output = run_command(
        [
            "aion",
            "verify",
            "--registry",
            str(REGISTRY),
            "--format",
            "json",
            str(path),
        ]
    )
    report = parse_json_from_output(output)
    if not report.get("is_valid"):
        raise ValidationError(f"{path} failed Aion verification: {report}")
    return report


def extract_rules(path: Path) -> str:
    output = run_command(
        [
            "aion",
            "show",
            "--registry",
            str(REGISTRY),
            "--format",
            "json",
            str(path),
            "rules",
        ]
    ).strip()

    # Current aion CLI emits the payload as hex for this subcommand.
    try:
        return bytes.fromhex(output).decode("utf-8")
    except ValueError:
        return output


def artifact_evidence(filename: str, payload: str, report: dict) -> dict:
    path = SIGNED_DIR / filename
    return {
        "artifact": filename,
        "path": str(path.relative_to(PROJECT_ROOT)),
        "aion_sha256": sha256_file(path),
        "payload_sha256": sha256_text(payload),
        "file_id": report["file_id"],
        "version_count": report["version_count"],
        "structure_valid": report["structure_valid"],
        "integrity_hash_valid": report["integrity_hash_valid"],
        "hash_chain_valid": report["hash_chain_valid"],
        "signatures_valid": report["signatures_valid"],
        "is_valid": report["is_valid"],
    }


def build_aion_context() -> tuple[dict[str, str], list[dict]]:
    payloads: dict[str, str] = {}
    evidence = []
    for filename in SIGNED_FILES:
        path = SIGNED_DIR / filename
        report = verify_aion_file(path)
        payload = extract_rules(path)
        payloads[filename] = payload
        evidence.append(artifact_evidence(filename, payload, report))
    return payloads, evidence

