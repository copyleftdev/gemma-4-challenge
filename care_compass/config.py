"""Project paths and runtime defaults."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SIGNED_DIR = PROJECT_ROOT / "care-pack" / "signed"
REGISTRY = SIGNED_DIR / "registry.json"
STATIC_ROOT = PROJECT_ROOT / "app" / "static"

SIGNED_FILES = [
    "scope_of_practice.aion",
    "privacy_policy.aion",
    "escalation_policy.aion",
    "navigation_rules.aion",
    "trusted_health_sources.aion",
    "resource_directory_seed.aion",
]

DEFAULT_MODEL = os.environ.get("CARE_COMPASS_MODEL", "gemma4:e4b")
CALL_MODEL_DEFAULT = os.environ.get("CARE_COMPASS_CALL_MODEL", "1") != "0"
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")

DEFAULT_ALLOWED_REQUEST = (
    "My mom was discharged yesterday. We do not have insurance, she prefers "
    "Spanish, and we need help finding a low-cost clinic and questions to ask "
    "when we call."
)

DEFAULT_BLOCKED_REQUEST = (
    "I have chest pain and I took extra pills. Should I change my medication dose?"
)

