"""Allocation models — docs/10, docs/17 Decision subset."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from revive.domain.enums import ActionCode, DecisionOutcome
from revive.recovery.candidates.models import RecoveryCandidate
from revive.recovery.valuation.models import CandidateValuation


class AllocatorMode(str, Enum):
    LAGRANGIAN = "LAGRANGIAN"
    FALLBACK_GREEDY = "FALLBACK_GREEDY"


@dataclass(frozen=True, slots=True)
class ResourceCapacities:
    """Cycle-level resource limits — integer units (paise for incentive_budget)."""

    retry_slots: int = 50
    message_capacity: int = 100
    voice_minutes: int = 30
    human_review_slots: int = 10
    incentive_budget_paise: int = 1_000_000
    contact_allowance_per_customer: int = 2


@dataclass
class ResourceState:
    """Mutable snapshot for one allocation pass — atomic planning decision."""

    capacities: ResourceCapacities
    retry_slots_used: int = 0
    message_capacity_used: int = 0
    voice_minutes_used: int = 0
    human_review_slots_used: int = 0
    incentive_budget_used_paise: int = 0
    customer_contacts: dict[str, int] = field(default_factory=dict)

    def contacts_for(self, customer_id: str) -> int:
        return self.customer_contacts.get(customer_id, 0)

    def remaining_retry_slots(self) -> int:
        return self.capacities.retry_slots - self.retry_slots_used

    def remaining_message_capacity(self) -> int:
        return self.capacities.message_capacity - self.message_capacity_used

    def remaining_voice_minutes(self) -> int:
        return self.capacities.voice_minutes - self.voice_minutes_used

    def remaining_human_review_slots(self) -> int:
        return self.capacities.human_review_slots - self.human_review_slots_used

    def remaining_incentive_budget_paise(self) -> int:
        return self.capacities.incentive_budget_paise - self.incentive_budget_used_paise

    def remaining_contacts(self, customer_id: str) -> int:
        return self.capacities.contact_allowance_per_customer - self.contacts_for(customer_id)


@dataclass(frozen=True, slots=True)
class PricedCandidate:
    candidate: RecoveryCandidate
    valuation: CandidateValuation
    usage: tuple[tuple[str, int], ...]

    @property
    def action_code(self) -> ActionCode:
        return self.candidate.action_code

    @property
    def enrv_paise(self) -> int:
        return self.valuation.enrv_paise

    @property
    def candidate_id(self) -> str:
        return self.candidate.candidate_id


@dataclass(frozen=True, slots=True)
class PortfolioItem:
    opportunity_id: str
    customer_id: str | None
    value_at_risk_paise: int
    candidates: tuple[PricedCandidate, ...]


@dataclass(frozen=True, slots=True)
class AllocationAssignment:
    opportunity_id: str
    customer_id: str | None
    outcome: DecisionOutcome
    action_code: ActionCode
    candidate_id: str | None
    enrv_paise: int
    reduced_value_paise: int
    reason_code: str
    binding_resource: str | None = None
    explanation: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "customer_id": self.customer_id,
            "outcome": self.outcome.value,
            "action_code": self.action_code.value,
            "candidate_id": self.candidate_id,
            "enrv_paise": self.enrv_paise,
            "reduced_value_paise": self.reduced_value_paise,
            "reason_code": self.reason_code,
            "binding_resource": self.binding_resource,
            "explanation": list(self.explanation),
        }


@dataclass(frozen=True, slots=True)
class AllocationResult:
    cycle_id: str
    produced_at_micros: int
    assignments: tuple[AllocationAssignment, ...]
    allocator_mode: AllocatorMode
    allocator_version: str
    policy_pack_version: str
    total_allocated_enrv_paise: int
    shadow_prices: dict[str, float]
    shadow_price_method: str
    resource_usage: dict[str, int]
    budget_usage_paise: int
    constraint_summary: tuple[str, ...]
    allocation_hash: str
    duality_gap: float | None = None
    optimality_gap: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "produced_at_micros": self.produced_at_micros,
            "assignments": [a.to_dict() for a in self.assignments],
            "allocator_mode": self.allocator_mode.value,
            "allocator_version": self.allocator_version,
            "policy_pack_version": self.policy_pack_version,
            "total_allocated_enrv_paise": self.total_allocated_enrv_paise,
            "shadow_prices": dict(self.shadow_prices),
            "shadow_price_method": self.shadow_price_method,
            "resource_usage": dict(self.resource_usage),
            "budget_usage_paise": self.budget_usage_paise,
            "constraint_summary": list(self.constraint_summary),
            "allocation_hash": self.allocation_hash,
            "duality_gap": self.duality_gap,
            "optimality_gap": self.optimality_gap,
        }

    def selected_assignments(self) -> tuple[AllocationAssignment, ...]:
        return tuple(a for a in self.assignments if a.outcome == DecisionOutcome.SELECTED)

    def deferred_assignments(self) -> tuple[AllocationAssignment, ...]:
        return tuple(a for a in self.assignments if a.outcome == DecisionOutcome.DEFERRED)
