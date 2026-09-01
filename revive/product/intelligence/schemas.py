"""Structured AI diagnosis contract — ai_diagnosis_v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from revive.domain.enums import ActionCode, CauseCode

AI_SCHEMA_VERSION = "ai_diagnosis_v1"

_VALID_CAUSES = frozenset(c.value for c in CauseCode)
_VALID_ACTIONS = frozenset(a.value for a in ActionCode)


@dataclass(frozen=True, slots=True)
class CandidateActionProposal:
    action_id: str
    reason: str
    expected_context_fit: str = ""


@dataclass(frozen=True, slots=True)
class DiagnosisProposal:
    opportunity_id: str
    primary_cause: str
    cause_confidence: float
    observed_evidence: tuple[str, ...]
    inference_notes: tuple[str, ...] = ()
    candidate_actions: tuple[CandidateActionProposal, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    risk_flags: tuple[str, ...] = ()
    uncertainty: str = ""


@dataclass(frozen=True, slots=True)
class DiagnosisResult:
    proposal: DiagnosisProposal
    source: str  # groq | deterministic_fallback
    status: str  # AI_COMPLETED | DETERMINISTIC_FALLBACK | AI_UNAVAILABLE
    model: str | None
    provider: str | None
    schema_version: str = AI_SCHEMA_VERSION
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        p = self.proposal
        return {
            "schema_version": self.schema_version,
            "source": self.source,
            "status": self.status,
            "provider": self.provider,
            "model": self.model,
            "error": self.error,
            "proposal": {
                "opportunity_id": p.opportunity_id,
                "primary_cause": p.primary_cause,
                "cause_confidence": p.cause_confidence,
                "observed_evidence": list(p.observed_evidence),
                "inference_notes": list(p.inference_notes),
                "candidate_actions": [asdict(c) for c in p.candidate_actions],
                "missing_evidence": list(p.missing_evidence),
                "risk_flags": list(p.risk_flags),
                "uncertainty": p.uncertainty,
            },
        }


JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "opportunity_id": {"type": "string"},
        "primary_cause": {"type": "string"},
        "cause_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "observed_evidence": {"type": "array", "items": {"type": "string"}},
        "inference_notes": {"type": "array", "items": {"type": "string"}},
        "candidate_actions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "action_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "expected_context_fit": {"type": "string"},
                },
                "required": ["action_id", "reason", "expected_context_fit"],
            },
        },
        "missing_evidence": {"type": "array", "items": {"type": "string"}},
        "risk_flags": {"type": "array", "items": {"type": "string"}},
        "uncertainty": {"type": "string"},
    },
    "required": [
        "opportunity_id",
        "primary_cause",
        "cause_confidence",
        "observed_evidence",
        "inference_notes",
        "candidate_actions",
        "missing_evidence",
        "risk_flags",
        "uncertainty",
    ],
}


def _coerce_str_list(raw: Any, *, limit: int = 12) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    for item in raw[:limit]:
        text = str(item).strip()
        if text:
            out.append(text)
    return tuple(out)


_GENERIC_VALUES = frozenset({"none", "true", "false", "yes", "no", "null", "n/a", "na"})


def _flatten_kv(obj: Any, prefix: str = "") -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            pairs.extend(_flatten_kv(value, path))
        return pairs
    if obj is None:
        return pairs
    text = str(obj).strip()
    if text:
        pairs.append((prefix, text))
    return pairs


def grounding_tokens(
    evidence_facts: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    """Tokens that may appear as OBSERVED. Keys alone are not enough."""
    tokens: list[str] = []
    for source in (evidence_facts, context):
        for key, value in _flatten_kv(source or {}):
            short_key = key.split(".")[-1]
            tokens.append(f"{short_key}={value}".lower())
            tokens.append(f"{key}={value}".lower())
            if len(value) >= 4 and value.lower() not in _GENERIC_VALUES:
                tokens.append(value.lower())
    return tuple(dict.fromkeys(tokens))


def claim_is_grounded(claim: str, tokens: tuple[str, ...]) -> bool:
    text = claim.strip().lower()
    if not text:
        return False
    for token in tokens:
        if len(token) < 4:
            continue
        if text == token or token in text:
            return True
        if len(text) >= 8 and text in token:
            return True
    return False


def classify_observed_claims(
    raw_items: Any,
    *,
    evidence_facts: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Split model 'observed' strings into grounded facts vs inference."""
    tokens = grounding_tokens(evidence_facts, context)
    observed: list[str] = []
    inferred: list[str] = []
    for item in _coerce_str_list(raw_items, limit=12):
        if claim_is_grounded(item, tokens):
            observed.append(item)
        else:
            inferred.append(f"Not in evidence (treated as inference): {item}")
    return tuple(observed), tuple(inferred)


def parse_proposal(
    payload: dict[str, Any],
    *,
    expected_opportunity_id: str,
    evidence_facts: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> DiagnosisProposal:
    if not isinstance(payload, dict):
        raise ValueError("proposal must be an object")
    oid = str(payload.get("opportunity_id", "")).strip()
    if oid != expected_opportunity_id:
        raise ValueError("opportunity_id mismatch")
    cause = str(payload.get("primary_cause", "")).strip().upper()
    if cause not in _VALID_CAUSES:
        raise ValueError(f"invalid primary_cause: {cause}")
    try:
        conf = float(payload.get("cause_confidence", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid cause_confidence") from exc
    if not 0.0 <= conf <= 1.0:
        raise ValueError("cause_confidence out of range")
    candidates_raw = payload.get("candidate_actions") or []
    if not isinstance(candidates_raw, list):
        raise ValueError("candidate_actions must be a list")
    candidates: list[CandidateActionProposal] = []
    for item in candidates_raw[:6]:
        if not isinstance(item, dict):
            continue
        action_id = str(item.get("action_id", "")).strip().upper()
        if action_id not in _VALID_ACTIONS:
            raise ValueError(f"invalid action_id: {action_id}")
        reason = str(item.get("reason", "")).strip()
        if not reason:
            raise ValueError("candidate reason required")
        fit = str(item.get("expected_context_fit", "")).strip()
        candidates.append(
            CandidateActionProposal(
                action_id=action_id,
                reason=reason,
                expected_context_fit=fit,
            )
        )
    grounded, downgraded = classify_observed_claims(
        payload.get("observed_evidence"),
        evidence_facts=evidence_facts,
        context=context,
    )
    inferences = list(_coerce_str_list(payload.get("inference_notes")))
    inferences.extend(downgraded)
    return DiagnosisProposal(
        opportunity_id=oid,
        primary_cause=cause,
        cause_confidence=conf,
        observed_evidence=grounded,
        inference_notes=tuple(inferences[:12]),
        candidate_actions=tuple(candidates),
        missing_evidence=_coerce_str_list(payload.get("missing_evidence")),
        risk_flags=_coerce_str_list(payload.get("risk_flags")),
        uncertainty=str(payload.get("uncertainty", "")).strip(),
    )
