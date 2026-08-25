"""Greedy fallback allocator — docs/10 §5.2."""

from __future__ import annotations

from revive.domain.enums import ActionCode, DecisionOutcome
from revive.allocation.models import AllocationAssignment, PortfolioItem, PricedCandidate, ResourceState
from revive.allocation.resources import can_reserve, normalized_resource_cost, reserve, usage_dict
from revive.allocation.tiebreak import sort_key_candidate, sort_key_opportunity


def fallback_greedy_allocate(
    items: tuple[PortfolioItem, ...],
    state: ResourceState,
    epsilon_paise: int,
) -> tuple[dict[str, AllocationAssignment], dict[str, float]]:
    pool: list[tuple[float, PortfolioItem, PricedCandidate]] = []
    for item in items:
        for pc in item.candidates:
            if pc.action_code == ActionCode.A00:
                continue
            if pc.enrv_paise <= epsilon_paise:
                continue
            usage = usage_dict(pc)
            density = pc.enrv_paise / normalized_resource_cost(usage)
            pool.append((density, item, pc))

    pool.sort(
        key=lambda t: (
            -t[0],
            sort_key_candidate(t[1], t[2], t[2].enrv_paise),
        )
    )

    assignments: dict[str, AllocationAssignment] = {}
    assigned_opps: set[str] = set()
    shadow_estimates: dict[str, float] = {}

    for density, item, pc in pool:
        if item.opportunity_id in assigned_opps:
            continue
        usage = usage_dict(pc)
        if can_reserve(state, usage, item.customer_id):
            if reserve(state, usage, item.customer_id):
                assigned_opps.add(item.opportunity_id)
                assignments[item.opportunity_id] = AllocationAssignment(
                    opportunity_id=item.opportunity_id,
                    customer_id=item.customer_id,
                    outcome=DecisionOutcome.SELECTED,
                    action_code=pc.action_code,
                    candidate_id=pc.candidate_id,
                    enrv_paise=pc.enrv_paise,
                    reduced_value_paise=int(pc.enrv_paise),
                    reason_code="FALLBACK_DENSITY_SELECTED",
                    explanation=("enrv_per_resource_density", f"density={density:.2f}"),
                )
        else:
            binding = _binding_from_usage(state, usage, item.customer_id)
            if binding:
                shadow_estimates[binding] = max(
                    shadow_estimates.get(binding, 0.0),
                    float(pc.enrv_paise),
                )

    for item in sorted(items, key=sort_key_opportunity):
        if item.opportunity_id in assignments:
            continue
        positive = any(
            pc.enrv_paise > epsilon_paise and pc.action_code != ActionCode.A00
            for pc in item.candidates
        )
        no_action = next(
            (pc for pc in item.candidates if pc.action_code == ActionCode.A00),
            None,
        )
        if positive:
            assignments[item.opportunity_id] = AllocationAssignment(
                opportunity_id=item.opportunity_id,
                customer_id=item.customer_id,
                outcome=DecisionOutcome.DEFERRED,
                action_code=ActionCode.A00,
                candidate_id=None,
                enrv_paise=0,
                reduced_value_paise=0,
                reason_code="DEFERRED_CAPACITY",
                binding_resource=_most_binding_resource(item, state, epsilon_paise),
                explanation=("fallback_capacity_exhausted",),
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
                reason_code="BELOW_EPSILON",
                explanation=("no_action_reference",),
            )

    return assignments, shadow_estimates


def _binding_from_usage(
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
    if usage.get("contact_allowance", 0) > 0 and customer_id is not None:
        if usage["contact_allowance"] > state.remaining_contacts(customer_id):
            return "contact_allowance"
    return None


def _most_binding_resource(
    item: PortfolioItem,
    state: ResourceState,
    epsilon_paise: int,
) -> str | None:
    best_resource: str | None = None
    best_enrv = -1
    for pc in item.candidates:
        if pc.enrv_paise <= epsilon_paise or pc.action_code == ActionCode.A00:
            continue
        usage = usage_dict(pc)
        binding = _binding_from_usage(state, usage, item.customer_id)
        if binding and pc.enrv_paise > best_enrv:
            best_enrv = pc.enrv_paise
            best_resource = binding
    return best_resource
