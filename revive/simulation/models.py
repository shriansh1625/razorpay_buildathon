"""DOMAIN-layer entity models for synthetic environment (docs/17 §2)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.domain.enums import OpportunityState, RiskClass
from revive.simulation.types import CheckoutStage, PaymentFailureReason


@dataclass(frozen=True, slots=True)
class MerchantRecord:
    merchant_id: str
    name_token: str
    timezone: str
    net_retention_factor: float
    policy_pack_ref: str


@dataclass(frozen=True, slots=True)
class CustomerRecord:
    customer_id: str
    customer_ref: str
    merchant_id: str
    segment: str
    tenure_band: str
    value_band: str
    # Observable proxy — noisy function of latent intent_to_pay
    prior_self_recovery_rate: float


@dataclass(frozen=True, slots=True)
class PaymentInstrumentRecord:
    instrument_id: str
    customer_id: str
    method_type: str
    network_band: str
    expiry_state: str
    block_state: str
    failure_count: int


@dataclass(frozen=True, slots=True)
class OrderRecord:
    order_id: str
    customer_id: str
    merchant_id: str
    amount_paise: int
    created_at_micros: int
    status: str


@dataclass(frozen=True, slots=True)
class TransactionRecord:
    transaction_id: str
    order_id: str
    customer_id: str
    amount_paise: int
    method_type: str
    instrument_id: str
    attempt_seq: int
    status: str
    reason_code: str | None
    reason_text: str | None
    attempted_at_micros: int


@dataclass(frozen=True, slots=True)
class CheckoutSessionRecord:
    session_id: str
    customer_id: str | None
    merchant_id: str
    cart_value_paise: int
    stage_reached: CheckoutStage
    method_selected: str | None
    abandoned_at_micros: int | None
    created_at_micros: int


@dataclass(frozen=True, slots=True)
class SubscriptionRecord:
    subscription_id: str
    customer_id: str
    mandate_id: str
    cycle_amount_paise: int
    cycle_number: int
    next_charge_at_micros: int
    state: str


@dataclass(frozen=True, slots=True)
class MandateRecord:
    mandate_id: str
    customer_id: str
    instrument_id: str
    state: str
    expires_at_micros: int
    max_amount_paise: int
    presented_count: int


@dataclass(frozen=True, slots=True)
class InvoiceRecord:
    invoice_id: str
    customer_id: str
    merchant_id: str
    issued_amount_paise: int
    paid_amount_paise: int
    credited_amount_paise: int
    written_off_amount_paise: int
    disputed_amount_paise: int
    due_at_micros: int
    terms_days: int
    state: str
    ageing_days: int


@dataclass(frozen=True, slots=True)
class SignalRecord:
    signal_id: str
    signal_type: str
    source_ref: str
    payload: dict[str, Any]
    received_at_micros: int
    occurred_at_micros: int
    dedupe_hash: str
    processed_at_micros: int | None = None
    opportunity_id: str | None = None


@dataclass(frozen=True, slots=True)
class RevenueOpportunityRecord:
    opportunity_id: str
    merchant_id: str
    customer_id: str
    risk_class: RiskClass
    natural_key: str
    value_at_risk_paise: int
    original_value_paise: int
    continuation_value_paise: int
    addressable: bool
    state: OpportunityState
    first_detected_at_micros: int
    recovery_window_expires_at_micros: int
    attempt_seq: int
    contacts_made: int
    linked_refs: dict[str, str] = field(default_factory=dict)
    failure_reason: PaymentFailureReason | None = None
    checkout_stage: CheckoutStage | None = None
    invoice_age_days: int | None = None
    in_degradation_window: bool = False


@dataclass(frozen=True, slots=True)
class DegradationWindow:
    cohort_ref: str
    start_micros: int
    end_micros: int
    severity: float


@dataclass(frozen=True, slots=True)
class PrivacyCanary:
    canary_id: str
    field_name: str
    sentinel_value: str
    planted_in_entity: str
    entity_id: str
