"""Decision lifecycle models — docs/09 §4, docs/17 §4.4."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from revive.config.policy_pack import PolicyPackStatus
from revive.domain.enums import ActionCode, DecisionOutcome


class DecisionLifecycleStatus(str, Enum):
    """Allocation decision validity — not gate authorization."""

    PROPOSED = "PROPOSED"
    RESERVED = "RESERVED"
    VALID = "VALID"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    SUPERSEDED = "SUPERSEDED"


class ReservationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    COMMITTED = "COMMITTED"


@dataclass(frozen=True, slots=True)
class AllocationSnapshot:
    """Observable input state at allocation time — no oracle fields."""

    opportunity_id: str
    customer_id: str | None
    value_at_risk_paise: int
    candidate_ids: tuple[str, ...]
    valuation_ids: tuple[str, ...]
    valuation_version: str
    strategy_version: str
    resource_capacities_digest: str
    simulation_time_micros: int
    opportunity_state: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "customer_id": self.customer_id,
            "value_at_risk_paise": self.value_at_risk_paise,
            "candidate_ids": list(self.candidate_ids),
            "valuation_ids": list(self.valuation_ids),
            "valuation_version": self.valuation_version,
            "strategy_version": self.strategy_version,
            "resource_capacities_digest": self.resource_capacities_digest,
            "simulation_time_micros": self.simulation_time_micros,
            "opportunity_state": self.opportunity_state,
        }


@dataclass(frozen=True, slots=True)
class ResourceReservation:
    reservation_id: str
    decision_id: str
    cycle_id: str
    resource_key: str
    quantity: int
    customer_id: str | None
    reserved_at_micros: int
    expires_at_micros: int
    status: ReservationStatus

    def to_dict(self) -> dict[str, Any]:
        return {
            "reservation_id": self.reservation_id,
            "decision_id": self.decision_id,
            "cycle_id": self.cycle_id,
            "resource_key": self.resource_key,
            "quantity": self.quantity,
            "customer_id": self.customer_id,
            "reserved_at_micros": self.reserved_at_micros,
            "expires_at_micros": self.expires_at_micros,
            "status": self.status.value,
        }


@dataclass(frozen=True, slots=True)
class AllocationDecision:
    """Immutable decision record — docs/09 §4."""

    decision_id: str
    cycle_id: str
    opportunity_id: str
    customer_id: str | None
    outcome: DecisionOutcome
    action_code: ActionCode
    candidate_id: str | None
    enrv_paise: int
    reason_code: str
    idempotency_key: str
    created_at_micros: int
    expires_at_micros: int
    allocator_version: str
    allocator_mode: str
    policy_pack_version: str
    policy_pack_status: PolicyPackStatus
    configuration_hash: str
    strategy_version: str
    valuation_version: str
    allocation_hash: str
    snapshot: AllocationSnapshot
    lifecycle_status: DecisionLifecycleStatus
    superseded_by: str | None = None
    provenance: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "cycle_id": self.cycle_id,
            "opportunity_id": self.opportunity_id,
            "customer_id": self.customer_id,
            "outcome": self.outcome.value,
            "action_code": self.action_code.value,
            "candidate_id": self.candidate_id,
            "enrv_paise": self.enrv_paise,
            "reason_code": self.reason_code,
            "idempotency_key": self.idempotency_key,
            "created_at_micros": self.created_at_micros,
            "expires_at_micros": self.expires_at_micros,
            "allocator_version": self.allocator_version,
            "allocator_mode": self.allocator_mode,
            "policy_pack_version": self.policy_pack_version,
            "policy_pack_status": self.policy_pack_status.value,
            "configuration_hash": self.configuration_hash,
            "strategy_version": self.strategy_version,
            "valuation_version": self.valuation_version,
            "allocation_hash": self.allocation_hash,
            "snapshot": self.snapshot.to_dict(),
            "lifecycle_status": self.lifecycle_status.value,
            "superseded_by": self.superseded_by,
            "provenance": list(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class StatusTransition:
    decision_id: str
    from_status: DecisionLifecycleStatus
    to_status: DecisionLifecycleStatus
    reason_code: str
    occurred_at_micros: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "from_status": self.from_status.value,
            "to_status": self.to_status.value,
            "reason_code": self.reason_code,
            "occurred_at_micros": self.occurred_at_micros,
        }


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    decision_id: str
    status: DecisionLifecycleStatus
    execution_ready: bool
    reason_code: str
    reconciled_at_micros: int
    stale_factors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "status": self.status.value,
            "execution_ready": self.execution_ready,
            "reason_code": self.reason_code,
            "reconciled_at_micros": self.reconciled_at_micros,
            "stale_factors": list(self.stale_factors),
        }


@dataclass(frozen=True, slots=True)
class ObservableReconcileContext:
    """Current observable state for reconciliation — no oracle."""

    now_micros: int
    opportunity_state: str
    payment_succeeded: bool = False
    contacts_used_for_customer: int = 0
    contact_allowance_per_customer: int = 2
    message_capacity_used: int = 0
    incentive_budget_used_paise: int = 0
    policy_config_hash: str = ""
    configuration_hash: str = ""


@dataclass(frozen=True, slots=True)
class DecisionBundle:
    cycle_id: str
    configuration_hash: str
    decisions: tuple[AllocationDecision, ...]
    reservations: tuple[ResourceReservation, ...]
    lifecycle_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "configuration_hash": self.configuration_hash,
            "decisions": [d.to_dict() for d in self.decisions],
            "reservations": [r.to_dict() for r in self.reservations],
            "lifecycle_version": self.lifecycle_version,
        }
