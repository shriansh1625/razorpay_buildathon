"""Diagnosis output models — docs/17 §4.2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from revive.domain.enums import CauseCode, ConfidenceBand
from revive.recovery.context.models import ContextObject
from revive.simulation.observation import HIDDEN_KEYS


@dataclass(frozen=True, slots=True)
class RankedCause:
    cause_code: CauseCode
    confidence_band: ConfidenceBand
    evidence_refs: tuple[str, ...]
    supporting_features: tuple[str, ...] = ()
    contradicting_features: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Diagnosis:
    diagnosis_id: str
    opportunity_id: str
    cycle_id: str
    produced_at_micros: int
    ranked_causes: tuple[RankedCause, ...]
    unclassified: bool
    observable_context: ContextObject
    deterministic_mapping_applied: bool
    diagnostic_version: str
    feature_schema_version: str
    llm_used: bool = False
    llm_cache_hit: bool = False
    provenance: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "diagnosis_id": self.diagnosis_id,
            "opportunity_id": self.opportunity_id,
            "cycle_id": self.cycle_id,
            "produced_at_micros": self.produced_at_micros,
            "ranked_causes": [
                {
                    "cause_code": rc.cause_code.value,
                    "confidence_band": rc.confidence_band.value,
                    "evidence_refs": list(rc.evidence_refs),
                    "supporting_features": list(rc.supporting_features),
                    "contradicting_features": list(rc.contradicting_features),
                }
                for rc in self.ranked_causes
            ],
            "unclassified": self.unclassified,
            "deterministic_mapping_applied": self.deterministic_mapping_applied,
            "diagnostic_version": self.diagnostic_version,
            "feature_schema_version": self.feature_schema_version,
            "llm_used": self.llm_used,
            "llm_cache_hit": self.llm_cache_hit,
            "provenance": list(self.provenance),
        }

    def hidden_keys(self) -> list[str]:
        found = list(self.observable_context.hidden_keys())
        stack: list[Any] = [self.to_dict()]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                for key, value in item.items():
                    if key in HIDDEN_KEYS:
                        found.append(key)
                    stack.append(value)
            elif isinstance(item, list):
                stack.extend(item)
        return found

    def contains_forbidden_vocabulary(self) -> list[str]:
        """RR-FUNC-012 — scan diagnosis-facing strings only."""
        parts: list[str] = []
        for rc in self.ranked_causes:
            parts.append(rc.cause_code.value)
            parts.extend(rc.supporting_features)
            parts.extend(rc.contradicting_features)
        parts.extend(self.provenance)
        blob = " ".join(parts).lower()
        forbidden = []
        for phrase in ("caused by", "proven", "root cause is"):
            if phrase in blob:
                forbidden.append(phrase)
        return forbidden

    @property
    def primary_category(self) -> CauseCode | None:
        return self.ranked_causes[0].cause_code if self.ranked_causes else None

    @property
    def uncertainty(self) -> str:
        if self.unclassified:
            return "UNKNOWN"
        if not self.ranked_causes:
            return "UNKNOWN"
        band = self.ranked_causes[0].confidence_band
        if band == ConfidenceBand.LOW:
            return "HEURISTIC_CONFIDENCE"
        return band.value
