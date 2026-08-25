"""Lagrangian relaxation allocator — docs/10 §5.1 (M13.12 performance path)."""

from __future__ import annotations

from revive.domain.enums import ActionCode, DecisionOutcome
from revive.allocation.config import AllocatorConfig
from revive.allocation.models import (
    AllocationAssignment,
    AllocatorMode,
    PortfolioItem,
    PricedCandidate,
    ResourceState,
)
from revive.allocation.resources import can_reserve, clear_usage_cache, reserve, usage_dict
from revive.allocation.tiebreak import sort_key_candidate, sort_key_opportunity


_RESOURCE_KEYS = (
    "retry_slots",
    "message_capacity",
    "voice_minutes",
    "human_review_slots",
    "incentive_budget",
    "contact_allowance",
)


def _capacity_vector(state: ResourceState) -> dict[str, int]:
    caps = state.capacities
    return {
        "retry_slots": caps.retry_slots,
        "message_capacity": caps.message_capacity,
        "voice_minutes": caps.voice_minutes,
        "human_review_slots": caps.human_review_slots,
        "incentive_budget": caps.incentive_budget_paise,
        "contact_allowance": caps.contact_allowance_per_customer,
    }


def _eligible_candidates(
    item: PortfolioItem,
    epsilon_paise: int,
) -> tuple[PricedCandidate, ...]:
    """Positive-ENRV, non-A00 candidates — immutable per allocation call."""
    eligible: list[PricedCandidate] = []
    for pc in item.candidates:
        if pc.action_code == ActionCode.A00:
            continue
        if pc.enrv_paise <= epsilon_paise:
            continue
        eligible.append(pc)
    return tuple(eligible)


def _reduced_value_paise(
    pc: PricedCandidate,
    lambdas: dict[str, float],
    customer_id: str | None,
) -> int:
    usage = usage_dict(pc)
    penalty = 0.0
    for resource, qty in usage.items():
        if resource == "contact_allowance" and customer_id is not None:
            penalty += lambdas.get("contact_allowance", 0.0) * qty
        else:
            penalty += lambdas.get(resource, 0.0) * qty
    return int(round(pc.enrv_paise - penalty))


def _best_action_eligible(
    item: PortfolioItem,
    eligible: tuple[PricedCandidate, ...],
    lambdas: dict[str, float],
) -> tuple[PricedCandidate | None, int]:
    best: PricedCandidate | None = None
    best_rv = 0
    best_key: tuple[int, int, str, str] | None = None
    for pc in eligible:
        rv = _reduced_value_paise(pc, lambdas, item.customer_id)
        if rv <= 0:
            continue
        key = sort_key_candidate(item, pc, rv)
        if best is None or key < best_key:
            best = pc
            best_rv = rv
            best_key = key
    return best, best_rv


def _accumulate_usage(
    picks: dict[str, PricedCandidate | None],
) -> dict[str, int]:
    usage: dict[str, int] = {k: 0 for k in _RESOURCE_KEYS}
    for pc in picks.values():
        if pc is None:
            continue
        for resource, qty in usage_dict(pc).items():
            usage[resource] = usage.get(resource, 0) + qty
    return usage


def _contact_violation_from_picks(
    picks: dict[str, PricedCandidate | None],
    item_by_id: dict[str, PortfolioItem],
    allowance: int,
) -> int:
    contacts: dict[str, int] = {}
    for opp_id, pc in picks.items():
        if pc is None:
            continue
        item = item_by_id[opp_id]
        if item.customer_id is None:
            continue
        contact_qty = usage_dict(pc).get("contact_allowance", 0)
        if contact_qty:
            contacts[item.customer_id] = contacts.get(item.customer_id, 0) + contact_qty
    violation = 0
    for count in contacts.values():
        if count > allowance:
            violation += count - allowance
    return violation


def lagrangian_allocate(
    items: tuple[PortfolioItem, ...],
    state: ResourceState,
    epsilon_paise: int,
    config: AllocatorConfig,
    lambda_warm_start: dict[str, float] | None = None,
) -> tuple[
    dict[str, PricedCandidate | None],
    dict[str, int],
    dict[str, float],
    float | None,
    AllocatorMode,
]:
    clear_usage_cache()
    lambdas = {k: 0.0 for k in _RESOURCE_KEYS}
    if lambda_warm_start:
        for k, v in lambda_warm_start.items():
            lambdas[k] = max(0.0, float(v))

    capacities = _capacity_vector(state)
    ordered_items = sorted(items, key=sort_key_opportunity)
    item_by_id = {item.opportunity_id: item for item in ordered_items}
    eligible_by_id = {
        item.opportunity_id: _eligible_candidates(item, epsilon_paise)
        for item in ordered_items
    }

    picks: dict[str, PricedCandidate | None] = {}
    best_rvs: dict[str, int] = {}
    duality_gap: float | None = None
    mode = AllocatorMode.LAGRANGIAN

    for k in range(1, config.k_max + 1):
        if k > config.iteration_budget:
            mode = AllocatorMode.FALLBACK_GREEDY
            break

        next_picks: dict[str, PricedCandidate | None] = {}
        next_best_rvs: dict[str, int] = {}
        for item in ordered_items:
            best, rv = _best_action_eligible(
                item,
                eligible_by_id[item.opportunity_id],
                lambdas,
            )
            next_picks[item.opportunity_id] = best
            next_best_rvs[item.opportunity_id] = rv if best is not None else 0
        picks = next_picks
        best_rvs = next_best_rvs

        usage = _accumulate_usage(picks)
        contact_v = _contact_violation_from_picks(
            picks,
            item_by_id,
            state.capacities.contact_allowance_per_customer,
        )

        subgrad = {}
        for resource in _RESOURCE_KEYS:
            if resource == "contact_allowance":
                subgrad[resource] = float(contact_v)
            else:
                subgrad[resource] = float(usage.get(resource, 0) - capacities[resource])

        if all(g <= 0 for g in subgrad.values()):
            total_cap = sum(capacities.values()) or 1
            duality_gap = sum(abs(g) for g in subgrad.values()) / total_cap
            if duality_gap <= config.duality_tolerance:
                break

        step = config.step(k)
        for resource in _RESOURCE_KEYS:
            lambdas[resource] = max(0.0, lambdas[resource] + step * subgrad[resource])

    if mode == AllocatorMode.FALLBACK_GREEDY:
        return picks, best_rvs, lambdas, duality_gap, mode

    return picks, best_rvs, lambdas, duality_gap, mode


def primal_recovery(
    items: tuple[PortfolioItem, ...],
    relaxed_picks: dict[str, PricedCandidate | None],
    best_rvs: dict[str, int],
    state: ResourceState,
    epsilon_paise: int,
    lambdas: dict[str, float],
) -> tuple[dict[str, AllocationAssignment], dict[str, float]]:
    """Primal recovery with reservation — docs/10 §5.1 lines 12–19."""
    assignments: dict[str, AllocationAssignment] = {}
    shadow_estimates: dict[str, float] = {k: 0.0 for k in _RESOURCE_KEYS}
    eligible_by_id = {
        item.opportunity_id: _eligible_candidates(item, epsilon_paise)
        for item in items
    }

    candidates_for_primal: list[tuple[int, PortfolioItem, PricedCandidate]] = []
    for item in items:
        pc = relaxed_picks.get(item.opportunity_id)
        if pc is None:
            continue
        rv = best_rvs.get(item.opportunity_id, 0)
        candidates_for_primal.append((rv, item, pc))

    candidates_for_primal.sort(key=lambda t: sort_key_candidate(t[1], t[2], t[0]))

    assigned: set[str] = set()

    for rv, item, pc in candidates_for_primal:
        usage = usage_dict(pc)
        if can_reserve(state, usage, item.customer_id):
            if reserve(state, usage, item.customer_id):
                assigned.add(item.opportunity_id)
                assignments[item.opportunity_id] = AllocationAssignment(
                    opportunity_id=item.opportunity_id,
                    customer_id=item.customer_id,
                    outcome=DecisionOutcome.SELECTED,
                    action_code=pc.action_code,
                    candidate_id=pc.candidate_id,
                    enrv_paise=pc.enrv_paise,
                    reduced_value_paise=rv,
                    reason_code="ALLOCATED_HIGH_REDUCED_VALUE",
                    explanation=("portfolio_adjusted_enrv", f"rv={rv}"),
                )
                continue

        binding = _binding_resource(state, usage, item.customer_id)
        if binding:
            shadow_estimates[binding] = max(shadow_estimates[binding], float(pc.enrv_paise))

        alt = _best_feasible_alternative(
            item,
            eligible_by_id[item.opportunity_id],
            state,
            lambdas,
            assigned,
        )
        if alt is not None:
            alt_usage = usage_dict(alt)
            if can_reserve(state, alt_usage, item.customer_id):
                if reserve(state, alt_usage, item.customer_id):
                    assigned.add(item.opportunity_id)
                    alt_rv = _reduced_value_paise(alt, lambdas, item.customer_id)
                    assignments[item.opportunity_id] = AllocationAssignment(
                        opportunity_id=item.opportunity_id,
                        customer_id=item.customer_id,
                        outcome=DecisionOutcome.SELECTED,
                        action_code=alt.action_code,
                        candidate_id=alt.candidate_id,
                        enrv_paise=alt.enrv_paise,
                        reduced_value_paise=alt_rv,
                        reason_code="ALLOCATED_ALTERNATIVE",
                        explanation=("feasible_alternative",),
                    )
                    continue

        if pc.enrv_paise > epsilon_paise:
            assignments[item.opportunity_id] = AllocationAssignment(
                opportunity_id=item.opportunity_id,
                customer_id=item.customer_id,
                outcome=DecisionOutcome.DEFERRED,
                action_code=ActionCode.A00,
                candidate_id=None,
                enrv_paise=0,
                reduced_value_paise=0,
                reason_code="DEFERRED_BINDING_RESOURCE",
                binding_resource=binding,
                explanation=("capacity_binding", binding or "unknown"),
            )
        else:
            assignments[item.opportunity_id] = AllocationAssignment(
                opportunity_id=item.opportunity_id,
                customer_id=item.customer_id,
                outcome=DecisionOutcome.NO_ACTION,
                action_code=ActionCode.A00,
                candidate_id=None,
                enrv_paise=0,
                reduced_value_paise=0,
                reason_code="BELOW_EPSILON",
                explanation=("no_action_reference",),
            )

    for item in items:
        if item.opportunity_id in assignments:
            continue
        eligible = eligible_by_id[item.opportunity_id]
        positive = len(eligible) > 0
        no_action = _no_action_candidate(item)
        if positive:
            assignments[item.opportunity_id] = AllocationAssignment(
                opportunity_id=item.opportunity_id,
                customer_id=item.customer_id,
                outcome=DecisionOutcome.DEFERRED,
                action_code=ActionCode.A00,
                candidate_id=None,
                enrv_paise=0,
                reduced_value_paise=0,
                reason_code="DEFERRED_BINDING_RESOURCE",
                binding_resource=_most_binding_for_item(item, eligible, state),
                explanation=("positive_enrv_no_capacity",),
            )
        else:
            assignments[item.opportunity_id] = AllocationAssignment(
                opportunity_id=item.opportunity_id,
                customer_id=item.customer_id,
                outcome=DecisionOutcome.NO_ACTION,
                action_code=ActionCode.A00,
                candidate_id=no_action.candidate_id if no_action else None,
                enrv_paise=0,
                reduced_value_paise=0,
                reason_code="NO_ACTION_CYCLE",
                explanation=("no_feasible_positive_enrv",),
            )

    return assignments, shadow_estimates


def _most_binding_for_item(
    item: PortfolioItem,
    eligible: tuple[PricedCandidate, ...],
    state: ResourceState,
) -> str | None:
    best_resource: str | None = None
    best_enrv = -1
    for pc in eligible:
        usage = usage_dict(pc)
        binding = _binding_resource(state, usage, item.customer_id)
        if binding and pc.enrv_paise > best_enrv:
            best_enrv = pc.enrv_paise
            best_resource = binding
    return best_resource


def _no_action_candidate(item: PortfolioItem) -> PricedCandidate | None:
    for pc in item.candidates:
        if pc.action_code == ActionCode.A00:
            return pc
    return None


def _binding_resource(
    state: ResourceState,
    usage: dict[str, int],
    customer_id: str | None,
) -> str | None:
    if usage.get("retry_slots", 0) > state.remaining_retry_slots():
        return "retry_slots"
    if usage.get("message_capacity", 0) > state.remaining_message_capacity():
        return "message_capacity"
    if usage.get("voice_minutes", 0) > state.remaining_voice_minutes():
        return "voice_minutes"
    if usage.get("human_review_slots", 0) > state.remaining_human_review_slots():
        return "human_review_slots"
    if usage.get("incentive_budget", 0) > state.remaining_incentive_budget_paise():
        return "incentive_budget"
    contact = usage.get("contact_allowance", 0)
    if contact > 0 and customer_id is not None:
        if contact > state.remaining_contacts(customer_id):
            return "contact_allowance"
    return None


def _best_feasible_alternative(
    item: PortfolioItem,
    eligible: tuple[PricedCandidate, ...],
    state: ResourceState,
    lambdas: dict[str, float],
    assigned: set[str],
) -> PricedCandidate | None:
    if item.opportunity_id in assigned:
        return None
    best: PricedCandidate | None = None
    best_key: tuple[int, int, str, str] | None = None
    for pc in eligible:
        usage = usage_dict(pc)
        if not can_reserve(state, usage, item.customer_id):
            continue
        rv = _reduced_value_paise(pc, lambdas, item.customer_id)
        if rv <= 0:
            continue
        key = sort_key_candidate(item, pc, rv)
        if best is None or key < best_key:
            best = pc
            best_key = key
    return best
