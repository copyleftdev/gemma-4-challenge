"""Local Ollama integration for Gemma."""

from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request

from .config import OLLAMA_HOST, PROJECT_ROOT
from .errors import ValidationError
from .hashing import sha256_text


def compact_policy_context(payloads: dict[str, str]) -> str:
    selected = {
        "scope_of_practice": payloads["scope_of_practice.aion"],
        "escalation_policy": payloads["escalation_policy.aion"],
        "navigation_rules": payloads["navigation_rules.aion"],
        "resource_directory_seed": payloads["resource_directory_seed.aion"],
    }
    return "\n\n".join(
        f"--- {name} verified payload excerpt ---\n{text[:2600]}"
        for name, text in selected.items()
    )


def ollama_status(host: str = OLLAMA_HOST) -> dict:
    try:
        request = urllib.request.Request(f"{host.rstrip('/')}/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=3) as response:
            body = json.loads(response.read().decode("utf-8"))
        return {
            "available": True,
            "detail": f"HTTP {host}",
            "models": [model.get("name", "") for model in body.get("models", [])],
        }
    except (TimeoutError, json.JSONDecodeError, urllib.error.URLError):
        pass

    try:
        proc = subprocess.run(
            ["ollama", "ps"],
            cwd=PROJECT_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=4,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "detail": str(exc), "models": []}

    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    return {
        "available": proc.returncode == 0,
        "detail": proc.stdout.strip(),
        "models": lines[1:] if len(lines) > 1 else [],
    }


def call_ollama(
    model: str,
    user_text: str,
    policy_context: str,
    host: str = OLLAMA_HOST,
) -> dict:
    system_prompt = f"""
You are Care Compass, a community health navigation assistant.

Use the verified Aion policy excerpts below as the source of truth. Do not
diagnose, recommend treatment, change medication, determine benefits
eligibility, or invent resources. Keep the response practical and concise.

Return JSON with these keys:
- answer
- suggested_resources
- questions_to_ask
- policy_basis
- safety_note

Return only a compact JSON object. Do not wrap it in markdown.
Keep `answer` under 90 words, `suggested_resources` to at most 3 items,
`questions_to_ask` to at most 5 items, `policy_basis` to one sentence, and
`safety_note` to one sentence.

{policy_context}
""".strip()

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": 8192,
            "num_predict": 700,
        },
    }
    request = urllib.request.Request(
        f"{host}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        started = time.perf_counter()
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
    except urllib.error.URLError as exc:
        raise ValidationError(f"failed to call Ollama local API: {exc}") from exc

    message = body.get("message", {})
    content = message.get("content") or body.get("response") or ""
    if not content.strip():
        raise ValidationError(f"Ollama returned an empty response body: {body}")

    parsed = None
    parse_error = None
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        parse_error = str(exc)

    return {
        "content": content,
        "parsed": parsed,
        "parse_error": parse_error,
        "request_payload_sha256": sha256_text(json.dumps(payload, sort_keys=True)),
        "policy_context_sha256": sha256_text(policy_context),
        "api_body_keys": sorted(body.keys()),
        "latency_ms": latency_ms,
        "ollama_metrics": {
            key: body.get(key)
            for key in (
                "total_duration",
                "load_duration",
                "prompt_eval_count",
                "prompt_eval_duration",
                "eval_count",
                "eval_duration",
            )
            if key in body
        },
    }
