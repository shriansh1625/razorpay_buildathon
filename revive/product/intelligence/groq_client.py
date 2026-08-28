"""Groq client — server-side only. Never log the API key."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from revive.product.intelligence.config import (
    GROQ_API_URL,
    GROQ_MODEL,
    MAX_RETRIES,
    PROMPT_VERSION,
    REQUEST_TIMEOUT_S,
    groq_api_key,
)
from revive.product.intelligence.schemas import JSON_SCHEMA


class GroqError(RuntimeError):
    pass


def _post_chat(messages: list[dict[str, str]], *, api_key: str) -> dict[str, Any]:
    body = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_completion_tokens": 1200,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "diagnosis_proposal",
                "strict": True,
                "schema": JSON_SCHEMA,
            },
        },
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        GROQ_API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_S) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise GroqError("invalid Groq response envelope")
    return payload


def complete_structured(messages: list[dict[str, str]]) -> dict[str, Any]:
    key = groq_api_key()
    if not key:
        raise GroqError("GROQ_API_KEY not configured")
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            payload = _post_chat(messages, api_key=key)
            choices = payload.get("choices") or []
            if not choices:
                raise GroqError("empty Groq choices")
            message = choices[0].get("message") or {}
            content = message.get("content")
            if not content:
                raise GroqError("empty Groq content")
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise GroqError("Groq content is not JSON object")
            return parsed
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, GroqError) as exc:
            last_error = exc
            if attempt >= MAX_RETRIES:
                break
            time.sleep(0.25 * (attempt + 1))
    raise GroqError(str(last_error) if last_error else "Groq request failed")


def system_prompt() -> str:
    return (
        "You are PAYVANTA's recovery diagnosis component for a revenue recovery sandbox. "
        "Interpret observed recovery context and return ONLY the required JSON object. "
        "You DO NOT authorize execution. You DO NOT execute actions. "
        "You MUST NOT invent evidence. Separate observed_evidence from inference_notes. "
        "cause_confidence is confidence in the diagnosis, not recovery probability. "
        "Use only cause codes and action_id values supplied in the user message. "
        f"Prompt version: {PROMPT_VERSION}."
    )
