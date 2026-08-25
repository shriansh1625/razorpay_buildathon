"""Immutable decision store with supersession and release."""

from __future__ import annotations

from dataclasses import dataclass, field

from revive.decision.ledger import ReservationLedger
from revive.decision.models import (
    AllocationDecision,
    DecisionBundle,
    DecisionLifecycleStatus,
    ReconciliationResult,
    StatusTransition,
)
from revive.decision.reconcile import reconcile_decision, transition_for_reconciliation


@dataclass
class DecisionStore:
    """Append-only decision history — projections updated via transitions."""

    ledger: ReservationLedger = field(default_factory=ReservationLedger)
    _decisions: dict[str, AllocationDecision] = field(default_factory=dict)
    _transitions: list[StatusTransition] = field(default_factory=list)
    _reconciliation_cache: dict[str, ReconciliationResult] = field(default_factory=dict)
    _bundles: list[DecisionBundle] = field(default_factory=list)

    def record_bundle(self, bundle: DecisionBundle) -> DecisionBundle:
        if any(b.cycle_id == bundle.cycle_id for b in self._bundles):
            existing = next(b for b in self._bundles if b.cycle_id == bundle.cycle_id)
            if existing.to_dict() == bundle.to_dict():
                return existing
        self._bundles.append(bundle)
        for decision in bundle.decisions:
            if decision.decision_id in self._decisions:
                existing = self._decisions[decision.decision_id]
                if existing.to_dict() != decision.to_dict():
                    raise ValueError(f"decision id collision: {decision.decision_id}")
                continue
            self._decisions[decision.decision_id] = decision
        if bundle.reservations:
            self.ledger.reserve(bundle.reservations)
        return bundle

    def get(self, decision_id: str) -> AllocationDecision | None:
        return self._decisions.get(decision_id)

    def current_status(self, decision_id: str) -> DecisionLifecycleStatus | None:
        decision = self.get(decision_id)
        if decision is None:
            return None
        for transition in reversed(self._transitions):
            if transition.decision_id == decision_id:
                return transition.to_status
        return decision.lifecycle_status

    def apply_transition(self, transition: StatusTransition) -> None:
        if any(
            t.decision_id == transition.decision_id
            and t.to_status == transition.to_status
            and t.reason_code == transition.reason_code
            and t.occurred_at_micros == transition.occurred_at_micros
            for t in self._transitions
        ):
            return
        self._transitions.append(transition)
        if transition.to_status in {
            DecisionLifecycleStatus.STALE,
            DecisionLifecycleStatus.EXPIRED,
            DecisionLifecycleStatus.CANCELLED,
            DecisionLifecycleStatus.SUPERSEDED,
        }:
            self.ledger.release(transition.decision_id)
        self._reconciliation_cache.pop(transition.decision_id, None)

    def reconcile(
        self,
        decision_id: str,
        context,
    ) -> ReconciliationResult:
        decision = self.get(decision_id)
        if decision is None:
            raise KeyError(decision_id)
        cached = self._reconciliation_cache.get(decision_id)
        prior = cached
        result = reconcile_decision(decision, context, prior_result=prior)
        if cached is None:
            self._reconciliation_cache[decision_id] = result
        transition = transition_for_reconciliation(decision, result)
        if transition is not None:
            self.apply_transition(transition)
        return result

    def supersede(self, old_decision_id: str, new_decision: AllocationDecision) -> AllocationDecision:
        old = self.get(old_decision_id)
        if old is None:
            raise KeyError(old_decision_id)
        superseded = AllocationDecision(
            decision_id=old.decision_id,
            cycle_id=old.cycle_id,
            opportunity_id=old.opportunity_id,
            customer_id=old.customer_id,
            outcome=old.outcome,
            action_code=old.action_code,
            candidate_id=old.candidate_id,
            enrv_paise=old.enrv_paise,
            reason_code=old.reason_code,
            idempotency_key=old.idempotency_key,
            created_at_micros=old.created_at_micros,
            expires_at_micros=old.expires_at_micros,
            allocator_version=old.allocator_version,
            allocator_mode=old.allocator_mode,
            policy_pack_version=old.policy_pack_version,
            policy_pack_status=old.policy_pack_status,
            configuration_hash=old.configuration_hash,
            strategy_version=old.strategy_version,
            valuation_version=old.valuation_version,
            allocation_hash=old.allocation_hash,
            snapshot=old.snapshot,
            lifecycle_status=DecisionLifecycleStatus.SUPERSEDED,
            superseded_by=new_decision.decision_id,
            provenance=old.provenance,
        )
        self._decisions[old_decision_id] = superseded
        self.apply_transition(
            StatusTransition(
                decision_id=old_decision_id,
                from_status=old.lifecycle_status,
                to_status=DecisionLifecycleStatus.SUPERSEDED,
                reason_code="SUPERSEDED_BY_REPLAN",
                occurred_at_micros=new_decision.created_at_micros,
            )
        )
        if new_decision.decision_id not in self._decisions:
            self._decisions[new_decision.decision_id] = new_decision
        return superseded

    def transitions_for(self, decision_id: str) -> tuple[StatusTransition, ...]:
        return tuple(t for t in self._transitions if t.decision_id == decision_id)
