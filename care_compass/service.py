"""Application service used by HTTP and CLI surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from .aion import build_aion_context
from .config import (
    CALL_MODEL_DEFAULT,
    DEFAULT_MODEL,
    OLLAMA_HOST,
    PROJECT_ROOT,
    REGISTRY,
)
from .errors import ValidationError
from .hashing import sha256_file
from .model import call_ollama, compact_policy_context, ollama_status
from .records import forensic_record
from .rules import gate_request


@dataclass(frozen=True)
class CareCompassService:
    default_model: str = DEFAULT_MODEL
    call_model_default: bool = CALL_MODEL_DEFAULT
    ollama_host: str = OLLAMA_HOST

    def status_payload(self) -> dict:
        _, evidence = build_aion_context()
        return {
            "ok": True,
            "model": self.default_model,
            "call_model_default": self.call_model_default,
            "ollama_host": self.ollama_host,
            "ollama": ollama_status(self.ollama_host),
            "aion": {
                "registry_path": str(REGISTRY.relative_to(PROJECT_ROOT)),
                "registry_sha256": sha256_file(REGISTRY),
                "artifacts": evidence,
            },
        }

    def decide(self, payload: dict) -> dict:
        user_text = str(payload.get("input") or "").strip()
        if not user_text:
            raise ValidationError("input is required")

        model = str(payload.get("model") or self.default_model)
        call_model_enabled = bool(payload.get("call_model", self.call_model_default))
        include_redacted_preview = bool(payload.get("include_redacted_preview", True))

        payloads, evidence = build_aion_context()
        gate = gate_request(user_text)
        model_result = None
        if call_model_enabled and gate.get("model_allowed"):
            model_result = call_ollama(
                model,
                user_text,
                compact_policy_context(payloads),
                self.ollama_host,
            )

        record = forensic_record(
            model=model,
            user_text=user_text,
            gate=gate,
            aion_evidence=evidence,
            model_result=model_result,
            include_raw=False,
            include_redacted_preview=include_redacted_preview,
        )
        return {
            "ok": True,
            "aion": record["aion_evidence"],
            "gate": gate,
            "model": {
                "called": model_result is not None,
                "parsed": model_result["parsed"] if model_result else None,
                "content": model_result["content"] if model_result else None,
                "output_sha256": record["model_evidence"]["output_sha256"],
                "output_json_valid": record["model_evidence"]["output_json_valid"],
                "request_payload_sha256": record["model_evidence"][
                    "request_payload_sha256"
                ],
                "policy_context_sha256": record["model_evidence"][
                    "policy_context_sha256"
                ],
                "latency_ms": record["model_evidence"]["latency_ms"],
                "ollama_metrics": record["model_evidence"]["ollama_metrics"],
            },
            "forensic_record": record,
        }
