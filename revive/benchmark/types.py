"""Baseline policy types — docs/20 §2."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from revive.domain.enums import ActionCode, DecisionOutcome


class BaselinePolicyId(str, Enum):
    B0 = "B0"
    B1 = "B1"
    B2 = "B2"
    B3 = "B3"


BASELINE_NAMES: dict[BaselinePolicyId, str] = {
    BaselinePolicyId.B0: "NO_ACTION",
    BaselinePolicyId.B1: "FIXED_RETRY",
    BaselinePolicyId.B2: "CONTACT_ALL",
    BaselinePolicyId.B3: "GREEDY_ENRV",
}


@dataclass(frozen=True, slots=True)
class ObservableOpportunity:
    """Opportunity view for baseline decisions — observable fields only."""

    opportunity_id: str
    merchant_id: str
    customer_id: str
    risk_class: str
    value_at_risk_paise: int
    addressable: bool
    state: str
    first_detected_at_micros: int
    recovery_window_expires_at_micros: int
    attempt_seq: int
    contacts_made: int
    next_eligible_at_micros: int | None = None
    in_degradation_window: bool = False
    prior_self_recovery_rate: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any], customer_lookup: dict[str, dict]) -> ObservableOpportunity:
        customer = customer_lookup.get(data["customer_id"], {})
        return cls(
            opportunity_id=data["opportunity_id"],
            merchant_id=data["merchant_id"],
            customer_id=data["customer_id"],
            risk_class=data["risk_class"],
            value_at_risk_paise=data["value_at_risk_paise"],
            addressable=bool(data["addressable"]),
            state=data["state"],
            first_detected_at_micros=data["first_detected_at_micros"],
            recovery_window_expires_at_micros=data["recovery_window_expires_at_micros"],
            attempt_seq=data.get("attempt_seq", 0),
            contacts_made=data.get("contacts_made", 0),
            next_eligible_at_micros=data.get("next_eligible_at_micros"),
            in_degradation_window=bool(data.get("in_degradation_window", False)),
            prior_self_recovery_rate=float(customer.get("prior_self_recovery_rate", 0.0)),
        )


@dataclass(frozen=True, slots=True)
class BaselineDecision:
    """Structured baseline decision — no free-form authoritative text."""

    policy_id: BaselinePolicyId
    policy_name: str
    strategy_version: str
    cycle_id: str
    opportunity_id: str
    action_code: ActionCode
    outcome: DecisionOutcome
    reason_code: str
    decision_at_micros: int
    enrv_estimate_paise: int | None = None
    rank: int | None = None
    observable_features: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id.value,
            "policy_name": self.policy_name,
            "strategy_version": self.strategy_version,
            "cycle_id": self.cycle_id,
            "opportunity_id": self.opportunity_id,
            "action_code": self.action_code.value,
            "outcome": self.outcome.value,
            "reason_code": self.reason_code,
            "decision_at_micros": self.decision_at_micros,
            "enrv_estimate_paise": self.enrv_estimate_paise,
            "rank": self.rank,
            "observable_features": self.observable_features,
        }


@dataclass
class BaselineCycleContext:
    """Shared cycle context — identical constraints for all baselines."""

    cycle_id: str
    now_micros: int
    epsilon_paise: int
    contact_allowance_per_customer: int
    retry_slots_per_cycle: int
    message_capacity_per_cycle: int
    assigned_opportunity_ids: set[str] = field(default_factory=set)
    customer_contacts: dict[str, int] = field(default_factory=dict)
    retry_slots_used: int = 0
    message_capacity_used: int = 0

    def contacts_for(self, customer_id: str) -> int:
        return self.customer_contacts.get(customer_id, 0)

    def can_contact(self, customer_id: str) -> bool:
        return self.contacts_for(customer_id) < self.contact_allowance_per_customer

    def reserve_contact(self, customer_id: str) -> bool:
        if not self.can_contact(customer_id):
            return False
        self.customer_contacts[customer_id] = self.contacts_for(customer_id) + 1
        return True

    def can_use_retry_slot(self) -> bool:
        return self.retry_slots_used < self.retry_slots_per_cycle

    def reserve_retry_slot(self) -> bool:
        if not self.can_use_retry_slot():
            return False
        self.retry_slots_used += 1
        return True

    def can_use_message_capacity(self) -> bool:
        return self.message_capacity_used < self.message_capacity_per_cycle

    def reserve_message_capacity(self) -> bool:
        if not self.can_use_message_capacity():
            return False
        self.message_capacity_used += 1
        return True


@dataclass(frozen=True, slots=True)
class BaselineCycleResult:
    policy_id: BaselinePolicyId
    cycle_id: str
    decisions: tuple[BaselineDecision, ...]

    def to_trace(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self.decisions]
