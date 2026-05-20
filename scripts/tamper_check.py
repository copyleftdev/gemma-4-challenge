#!/usr/bin/env python3
"""
Verify that tampering with signed Aion artifacts is detected.

This script copies each .aion file to /tmp, flips one byte, then expects
`aion verify` to fail. It never mutates project files and never calls Ollama.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from care_compass.config import (  # noqa: E402
    PROJECT_ROOT,
    REGISTRY,
    SIGNED_DIR,
    SIGNED_FILES,
)
from care_compass.hashing import sha256_file  # noqa: E402
from care_compass.records import utc_now  # noqa: E402


def run_verify(path: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [
            "aion",
            "verify",
            "--registry",
            str(REGISTRY),
            "--format",
            "json",
            str(path),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.returncode, proc.stdout


def tamper_file(path: Path) -> int:
    data = bytearray(path.read_bytes())
    if len(data) < 16:
        raise RuntimeError(f"file too small to tamper safely: {path}")
    offset = len(data) // 2
    data[offset] ^= 0x01
    path.write_bytes(data)
    return offset


def main() -> int:
    results = []
    with tempfile.TemporaryDirectory(prefix="care-compass-tamper-") as tmp:
        tmpdir = Path(tmp)
        for filename in SIGNED_FILES:
            original = SIGNED_DIR / filename
            original_code, original_output = run_verify(original)
            original_valid = (
                original_code == 0 and '"is_valid": true' in original_output
            )

            copy = tmpdir / filename
            shutil.copy2(original, copy)
            offset = tamper_file(copy)
            tampered_code, tampered_output = run_verify(copy)
            tamper_detected = (
                tampered_code != 0 or '"is_valid": false' in tampered_output
            )

            results.append(
                {
                    "artifact": filename,
                    "original_sha256": sha256_file(original),
                    "original_valid": original_valid,
                    "tampered_offset": offset,
                    "tamper_detected": tamper_detected,
                    "tampered_verify_exit_code": tampered_code,
                }
            )

    summary = {
        "schema": "care_compass.tamper_check.v1",
        "created_at": utc_now(),
        "total": len(results),
        "passed": sum(
            1
            for item in results
            if item["original_valid"] and item["tamper_detected"]
        ),
        "failed": [
            item
            for item in results
            if not item["original_valid"] or not item["tamper_detected"]
        ],
        "results": results,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
