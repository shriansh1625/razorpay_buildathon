"""Recovery candidate models — feasibility only, no ENRV (docs/17 §4.3 subset)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.domain.enums import ActionCode, CandidateAvailability
from revive.simulation.observation import HIDDEN_KEYS


@dataclass(frozen=True, slots=True)
class ResourceRequirement:
    resource_key: str
    quantity: int


@dataclass(frozen=True, slots=True)
class RecoveryCandidate:
    """A feasible recovery action — not a selected decision."""

    candidate_id: str
    opportunity_id: str
    cycle_id: str
    action_code: ActionCode
    params: dict[str, Any]
    availability_status: CandidateAvailability
    prerequisites_satisfied: tuple[str, ...]
    prerequisites_failed: tuple[str, ...]
    resource_requirements: tuple[ResourceRequirement, ...]
    nominal_cost_paise: int
    earliest_eligible_at_micros: int | None
    approval_required: bool
    reason_codes: tuple[str, ...]
    provenance: tuple[str, ...]
    policy_pack_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "opportunity_id": self.opportunity_id,
            "cycle_id": self.cycle_id,
            "action_code": self.action_code.value,
            "params": dict(self.params),
            "availability_status": self.availability_status.value,
            "prerequisites_satisfied": list(self.prerequisites_satisfied),
            "prerequisites_failed": list(self.prerequisites_failed),
            "resource_requirements": [
                {"resource_key": r.resource_key, "quantity": r.quantity}
                for r in self.resource_requirements
            ],
            "nominal_cost_paise": self.nominal_cost_paise,
            "earliest_eligible_at_micros": self.earliest_eligible_at_micros,
            "approval_required": self.approval_required,
            "reason_codes": list(self.reason_codes),
            "provenance": list(self.provenance),
            "policy_pack_version": self.policy_pack_version,
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


@dataclass(frozen=True, slots=True)
class CandidateSetResult:
    opportunity_id: str
    cycle_id: str
    produced_at_micros: int
    candidates: tuple[RecoveryCandidate, ...]
    generator_version: str
    policy_pack_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "cycle_id": self.cycle_id,
            "produced_at_micros": self.produced_at_micros,
            "candidates": [c.to_dict() for c in self.candidates],
            "generator_version": self.generator_version,
            "policy_pack_version": self.policy_pack_version,
        }

    def available_candidates(self) -> tuple[RecoveryCandidate, ...]:
        return tuple(
            c
            for c in self.candidates
            if c.availability_status == CandidateAvailability.AVAILABLE
        )


@dataclass
class CandidateCapacityContext:
    """Optional cycle capacity snapshot — affects availability, not optimization."""

    retry_slots_remaining: int = 50
    message_capacity_remaining: int = 100
    voice_minutes_remaining: int = 30
    human_review_slots_remaining: int = 10
    incentive_budget_remaining_paise: int = 1_000_000

    def can_reserve(self, requirements: tuple[ResourceRequirement, ...]) -> bool:
        pools = {
            "retry_slots": self.retry_slots_remaining,
            "message_capacity": self.message_capacity_remaining,
            "voice_minutes": self.voice_minutes_remaining,
            "human_review_slots": self.human_review_slots_remaining,
            "incentive_budget": self.incentive_budget_remaining_paise,
        }
        for req in requirements:
            pool = pools.get(req.resource_key)
            if pool is None:
                continue
            if pool < req.quantity:
                return False
        return True
