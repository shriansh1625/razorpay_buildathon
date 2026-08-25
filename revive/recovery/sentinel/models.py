"""Sentinel output records — docs/17 RevenueOpportunity fields used at detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.domain.enums import (
    AgeingBucket,
    NonAddressableReason,
    OpportunityState,
    RiskClass,
)
from revive.simulation.observation import HIDDEN_KEYS


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    signal_ids: tuple[str, ...]
    source_refs: dict[str, str]
    facts: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DetectedOpportunity:
    opportunity_id: str
    merchant_id: str
    customer_id: str | None
    risk_class: RiskClass
    natural_key: str
    value_at_risk_paise: int
    original_value_paise: int
    continuation_value_paise: int
    addressable: bool
    non_addressable_reason: NonAddressableReason | None
    state: OpportunityState
    first_detected_at_micros: int
    recovery_window_expires_at_micros: int
    attempt_seq: int
    ageing_bucket: AgeingBucket | None
    degradation_flag: bool
    evidence: EvidenceRecord
    detector_version: str
    secondary_class: RiskClass | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "merchant_id": self.merchant_id,
            "customer_id": self.customer_id,
            "risk_class": self.risk_class.value,
            "natural_key": self.natural_key,
            "value_at_risk_paise": self.value_at_risk_paise,
            "original_value_paise": self.original_value_paise,
            "continuation_value_paise": self.continuation_value_paise,
            "addressable": self.addressable,
            "non_addressable_reason": (
                self.non_addressable_reason.value if self.non_addressable_reason else None
            ),
            "state": self.state.value,
            "first_detected_at_micros": self.first_detected_at_micros,
            "recovery_window_expires_at_micros": self.recovery_window_expires_at_micros,
            "attempt_seq": self.attempt_seq,
            "ageing_bucket": self.ageing_bucket.value if self.ageing_bucket else None,
            "degradation_flag": self.degradation_flag,
            "evidence": {
                "signal_ids": list(self.evidence.signal_ids),
                "source_refs": dict(self.evidence.source_refs),
                "facts": dict(self.evidence.facts),
            },
            "detector_version": self.detector_version,
            "secondary_class": self.secondary_class.value if self.secondary_class else None,
        }

    def hidden_keys(self) -> list[str]:
        found: list[str] = []
        blob = self.to_dict()
        stack: list[Any] = [blob]
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


@dataclass(frozen=True, slots=True)
class QuarantineRecord:
    signal_id: str | None
    rejection_reason: str
    received_at_micros: int
    raw_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DetectionMetrics:
    opportunities_detected: int
    value_at_risk_total_paise: int
    by_class: dict[str, int]
    quarantine_count: int
    dedupe_merges: int
    signals_ingested: int
    detector_version: str


@dataclass(frozen=True, slots=True)
class SentinelResult:
    opportunities: tuple[DetectedOpportunity, ...]
    quarantined: tuple[QuarantineRecord, ...]
    metrics: DetectionMetrics
    now_micros: int
