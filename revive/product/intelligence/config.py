"""Product-layer AI configuration (sandbox only — never official benchmark)."""

from __future__ import annotations

import os

AI_SCHEMA_VERSION = "ai_diagnosis_v1"
GROQ_MODEL = "openai/gpt-oss-120b"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
REQUEST_TIMEOUT_S = 12.0
MAX_RETRIES = 2
PROMPT_VERSION = "payvanta_diagnosis_v1"


def groq_api_key() -> str | None:
    key = os.environ.get("GROQ_API_KEY", "").strip()
    return key or None


def ai_configured() -> bool:
    return groq_api_key() is not None
