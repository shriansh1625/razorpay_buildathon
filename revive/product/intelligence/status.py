"""Machine-readable AI status for overview and System page."""

from __future__ import annotations

from typing import Any

from revive.product.intelligence.config import GROQ_MODEL, AI_SCHEMA_VERSION, ai_configured


def intelligence_status(*, last_status: str | None = None) -> dict[str, Any]:
    configured = ai_configured()
    if not configured:
        return {
            "enabled": False,
            "status": "DETERMINISTIC_FALLBACK",
            "provider": None,
            "model": GROQ_MODEL,
            "role": "diagnosis_and_proposal",
            "fallback": True,
            "execution_authority": "none",
            "schema_version": AI_SCHEMA_VERSION,
            "note": "Set server-side Groq API key to enable contextual diagnosis in the sandbox product layer.",
        }
    status = last_status or "AI_ENABLED"
    return {
        "enabled": True,
        "status": status,
        "provider": "groq",
        "model": GROQ_MODEL,
        "role": "diagnosis_and_proposal",
        "fallback": status in {"DETERMINISTIC_FALLBACK", "AI_UNAVAILABLE"},
        "execution_authority": "none",
        "schema_version": AI_SCHEMA_VERSION,
        "note": "AI proposes diagnosis and candidates. Deterministic economics and guardrails decide execution.",
    }
