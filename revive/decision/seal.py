"""Seal M8 allocation into immutable decision records."""

from __future__ import annotations

from revive.allocation.config import AllocatorConfig, default_allocator_config
from revive.allocation.models import AllocationResult, PortfolioItem, ResourceCapacities
from revive.config.policy_pack import PolicyPack, default_draft_policy_pack
from revive.domain.enums import ActionCode, DecisionOutcome
from revive.decision.config import DecisionLifecycleConfig, default_lifecycle_config
from revive.decision.hashing import (
    capacities_digest,
    configuration_hash,
    decision_id_for,
    idempotency_key_for,
    reservation_id_for,
)
from revive.decision.ledger import ReservationLedger
from revive.decision.models import (
    AllocationDecision,
    AllocationSnapshot,
    DecisionBundle,
    DecisionLifecycleStatus,
    ResourceReservation,
    ReservationStatus,
)
from revive.allocation.resources import usage_dict


def seal_allocation(
    allocation: AllocationResult,
    portfolio_items: tuple[PortfolioItem, ...],
    capacities: ResourceCapacities,
    policy: PolicyPack | None = None,
    allocator_config: AllocatorConfig | None = None,
    lifecycle_config: DecisionLifecycleConfig | None = None,
    opportunity_states: dict[str, str] | None = None,
    attempt_seq: int = 1,
    ledger: ReservationLedger | None = None,
) -> DecisionBundle:
    """Convert M8 allocation into attributable, versioned decision records."""
    pol = policy or default_draft_policy_pack()
    alloc_cfg = allocator_config or default_allocator_config()
    life_cfg = lifecycle_config or default_lifecycle_config()
    item_map = {i.opportunity_id: i for i in portfolio_items}
    states = opportunity_states or {}

    valuation_versions: list[str] = []
    strategy_versions: list[str] = []
    for item in portfolio_items:
        for pc in item.candidates:
            valuation_versions.append(pc.valuation.valuation_version)
            strategy_versions.append(pc.valuation.strategy_version)

    config_hash = configuration_hash(
        pol,
        alloc_cfg,
        tuple(sorted(set(valuation_versions))),
        tuple(sorted(set(strategy_versions))),
        capacities,
    )

    decisions: list[AllocationDecision] = []
    reservations: list[ResourceReservation] = []
    res_ledger = ledger or ReservationLedger()
    cap_digest = capacities_digest(capacities)
    expires_at = allocation.produced_at_micros + life_cfg.allocation_ttl_micros

    for assignment in allocation.assignments:
        item = item_map.get(assignment.opportunity_id)
        if item is None:
            continue

        candidate_ids = tuple(pc.candidate_id for pc in item.candidates)
        valuation_ids = tuple(pc.valuation.valuation_id for pc in item.candidates)
        val_version = item.candidates[0].valuation.valuation_version if item.candidates else ""
        strat_version = item.candidates[0].valuation.strategy_version if item.candidates else ""

        snapshot = AllocationSnapshot(
            opportunity_id=assignment.opportunity_id,
            customer_id=assignment.customer_id,
            value_at_risk_paise=item.value_at_risk_paise,
            candidate_ids=candidate_ids,
            valuation_ids=valuation_ids,
            valuation_version=val_version,
            strategy_version=strat_version,
            resource_capacities_digest=cap_digest,
            simulation_time_micros=allocation.produced_at_micros,
            opportunity_state=states.get(assignment.opportunity_id, "PRICED"),
        )

        decision_id = decision_id_for(
            allocation.cycle_id,
            assignment.opportunity_id,
            allocation.allocation_hash,
            config_hash,
        )
        idem_key = idempotency_key_for(
            assignment.opportunity_id,
            assignment.action_code,
            attempt_seq,
            allocation.cycle_id,
        )

        initial_status = DecisionLifecycleStatus.PROPOSED
        if assignment.outcome == DecisionOutcome.SELECTED:
            initial_status = DecisionLifecycleStatus.RESERVED

        decision = AllocationDecision(
            decision_id=decision_id,
            cycle_id=allocation.cycle_id,
            opportunity_id=assignment.opportunity_id,
            customer_id=assignment.customer_id,
            outcome=assignment.outcome,
            action_code=assignment.action_code,
            candidate_id=assignment.candidate_id,
            enrv_paise=assignment.enrv_paise,
            reason_code=assignment.reason_code,
            idempotency_key=idem_key,
            created_at_micros=allocation.produced_at_micros,
            expires_at_micros=expires_at,
            allocator_version=allocation.allocator_version,
            allocator_mode=allocation.allocator_mode.value,
            policy_pack_version=pol.version,
            policy_pack_status=pol.status,
            configuration_hash=config_hash,
            strategy_version=strat_version,
            valuation_version=val_version,
            allocation_hash=allocation.allocation_hash,
            snapshot=snapshot,
            lifecycle_status=initial_status,
            provenance=(
                f"lifecycle_version={life_cfg.lifecycle_version}",
                f"allocation_hash={allocation.allocation_hash}",
            ),
        )
        decisions.append(decision)

        if assignment.outcome != DecisionOutcome.SELECTED or assignment.candidate_id is None:
            continue

        priced = next(
            (pc for pc in item.candidates if pc.candidate_id == assignment.candidate_id),
            None,
        )
        if priced is None:
            continue

        usage = usage_dict(priced)
        decision_reservations: list[ResourceReservation] = []
        for resource_key, quantity in usage.items():
            if quantity <= 0:
                continue
            res = ResourceReservation(
                reservation_id=reservation_id_for(decision_id, resource_key),
                decision_id=decision_id,
                cycle_id=allocation.cycle_id,
                resource_key=resource_key,
                quantity=quantity,
                customer_id=assignment.customer_id if resource_key == "contact_allowance" else None,
                reserved_at_micros=allocation.produced_at_micros,
                expires_at_micros=expires_at,
                status=ReservationStatus.ACTIVE,
            )
            decision_reservations.append(res)

        if decision_reservations:
            sealed = res_ledger.reserve(tuple(decision_reservations))
            reservations.extend(sealed)

    return DecisionBundle(
        cycle_id=allocation.cycle_id,
        configuration_hash=config_hash,
        decisions=tuple(decisions),
        reservations=tuple(reservations),
        lifecycle_version=life_cfg.lifecycle_version,
    )
