"""Observable authorization context — no oracle fields."""

from __future__ import annotations

from dataclasses import dataclass, field

from revive.domain.enums import ApprovalRequestState, CauseCode


@dataclass(frozen=True, slots=True)
class AuthorizeContext:
    now_micros: int
    opportunity_state: str
    value_at_risk_paise: int
    customer_id: str | None
    payment_succeeded: bool = False
    recovery_window_expires_at_micros: int = 0
    contacts_today: int = 0
    contacts_7d: int = 0
    contacts_30d: int = 0
    contacts_on_opportunity: int = 0
    retries_on_opportunity: int = 0
    merchant_local_hour: int = 12
    consent_channels: frozenset[str] = frozenset({"SMS", "EMAIL", "PUSH"})
    opted_out: bool = False
    risk_flags: frozenset[str] = field(default_factory=frozenset)
    merchant_halt: bool = False
    opportunity_suppressed: bool = False
    top_cause_code: CauseCode | None = None
    cause_confidence_band: str = "MED"
    approval_state: ApprovalRequestState | None = None
    duplicate_idempotency_claimed: bool = False
    duplicate_semantic_recent: bool = False
    budget_remaining_paise: int = 1_000_000
    message_capacity_remaining: int = 100
    retry_slots_remaining: int = 50
    voice_minutes_remaining: int = 30
    human_review_slots_remaining: int = 10
    configuration_hash: str = ""
    reconciliation_status: str = "VALID"
    transaction_amount_paise: int | None = None
    consecutive_no_action_cycles: int = 0
    channel_degraded: frozenset[str] = field(default_factory=frozenset)
    approval_expired: bool = False
    value_written_off: bool = False
    policy_pack_hash: str = ""
    enrv_interval_width_ratio: float = 0.0
    first_use_action_for_merchant: bool = False
