"""ContextObject and supporting structures — docs/08 C-04, RR-FUNC-013…017."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from revive.domain.enums import EvidenceKind
from revive.simulation.observation import HIDDEN_KEYS


@dataclass(frozen=True, slots=True)
class ContextEvidence:
    evidence_id: str
    kind: EvidenceKind
    feature: str
    value: Any
    source: str
    source_ref: str | None = None


@dataclass(frozen=True, slots=True)
class CustomerContext:
    customer_id: str | None
    segment: str | None
    segment_null_reason: str | None
    tenure_band: str | None
    value_band: str | None
    prior_self_recovery_rate: float | None
    successful_payment_count: int
    failed_payment_count: int
    success_rate: float | None
    average_transaction_value_paise: int | None
    recent_failure_count: int
    previous_recovery_count: int
    previous_contact_count: int


@dataclass(frozen=True, slots=True)
class FatigueContext:
    contacts_last_7d: int
    contacts_last_30d: int
    fatigue_band: str
    null_reason: str | None = None


@dataclass(frozen=True, slots=True)
class InstrumentContext:
    instrument_id: str | None
    method_type: str | None
    expiry_state: str | None
    block_state: str | None
    instrument_success_count: int
    instrument_failure_count: int
    instrument_success_rate: float | None
    null_reason: str | None = None


@dataclass(frozen=True, slots=True)
class PaymentContext:
    transaction_id: str | None
    order_id: str | None
    amount_paise: int | None
    method_type: str | None
    reason_code: str | None
    reason_text: str | None
    attempt_seq: int
    recent_attempt_count: int
    failure_cluster_size: int
    merchant_degradation_observed: bool


@dataclass(frozen=True, slots=True)
class CheckoutContext:
    session_id: str | None
    cart_value_paise: int | None
    stage_reached: str | None
    elapsed_seconds: int | None
    method_selected: str | None
    payment_initiated: bool
    prior_abandonment_count: int
    null_reason: str | None = None


@dataclass(frozen=True, slots=True)
class SubscriptionContext:
    subscription_id: str | None
    cycle_number: int | None
    cycle_amount_paise: int | None
    state: str | None
    successful_debit_count: int
    failed_debit_count: int
    mandate_id: str | None
    mandate_state: str | None
    mandate_expires_at_micros: int | None
    null_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReceivableContext:
    invoice_id: str | None
    issued_amount_paise: int | None
    outstanding_paise: int | None
    ageing_bucket: str | None
    ageing_days: int | None
    prior_overdue_count: int
    prior_payment_count: int
    disputed_amount_paise: int
    null_reason: str | None = None


@dataclass(frozen=True, slots=True)
class TemporalContext:
    now_micros: int
    time_since_event_micros: int | None
    time_since_last_success_micros: int | None
    time_since_last_failure_micros: int | None
    merchant_local_hour: int | None
    day_of_month: int | None
    is_business_day: bool | None
    time_to_window_close_micros: int | None


@dataclass(frozen=True, slots=True)
class DegradationContext:
    degradation_flag: bool
    observed_failure_rate: float | None
    baseline_failure_rate: float | None
    affected_payment_method: str | None
    failure_cluster_size: int
    window_minutes: int


@dataclass(frozen=True, slots=True)
class ContextObject:
    opportunity_id: str
    assembled_at_micros: int
    customer: CustomerContext
    fatigue: FatigueContext
    instrument: InstrumentContext | None
    payment: PaymentContext | None
    checkout: CheckoutContext | None
    subscription: SubscriptionContext | None
    receivable: ReceivableContext | None
    temporal: TemporalContext
    degradation: DegradationContext
    context_degraded: bool
    feature_schema_version: str
    evidence: tuple[ContextEvidence, ...]

    def to_dict(self) -> dict[str, Any]:
        def _slot_dict(obj: Any) -> dict[str, Any]:
            if obj is None:
                return {}
            from dataclasses import fields

            return {f.name: getattr(obj, f.name) for f in fields(obj)}

        return {
            "opportunity_id": self.opportunity_id,
            "assembled_at_micros": self.assembled_at_micros,
            "customer": _slot_dict(self.customer),
            "fatigue": _slot_dict(self.fatigue),
            "instrument": _slot_dict(self.instrument) if self.instrument else None,
            "payment": _slot_dict(self.payment) if self.payment else None,
            "checkout": _slot_dict(self.checkout) if self.checkout else None,
            "subscription": _slot_dict(self.subscription) if self.subscription else None,
            "receivable": _slot_dict(self.receivable) if self.receivable else None,
            "temporal": _slot_dict(self.temporal),
            "degradation": _slot_dict(self.degradation),
            "context_degraded": self.context_degraded,
            "feature_schema_version": self.feature_schema_version,
            "evidence": [
                {
                    "evidence_id": e.evidence_id,
                    "kind": e.kind.value,
                    "feature": e.feature,
                    "value": e.value,
                    "source": e.source,
                    "source_ref": e.source_ref,
                }
                for e in self.evidence
            ],
        }

    def hidden_keys(self) -> list[str]:
        found: list[str] = []
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
