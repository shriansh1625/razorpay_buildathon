"""Portfolio allocation entry — docs/10."""

from __future__ import annotations

import hashlib
import json

from revive.config.policy_pack import PolicyPack, default_draft_policy_pack
from revive.domain.enums import DecisionOutcome
from revive.allocation.config import AllocatorConfig, default_allocator_config
from revive.allocation.greedy import fallback_greedy_allocate
from revive.allocation.lagrangian import lagrangian_allocate, primal_recovery
from revive.allocation.models import (
    AllocationResult,
    AllocatorMode,
    PortfolioItem,
    ResourceCapacities,
    ResourceState,
)
from revive.allocation.resources import clear_usage_cache, resource_usage_summary
from revive.allocation.tiebreak import sort_key_opportunity


def allocate_portfolio(
    items: tuple[PortfolioItem, ...],
    resource_state: ResourceState,
    now_micros: int,
    cycle_id: str,
    policy: PolicyPack | None = None,
    config: AllocatorConfig | None = None,
    lambda_warm_start: dict[str, float] | None = None,
) -> AllocationResult:
    """Maximize portfolio ENRV under shared resource constraints — no execution."""
    clear_usage_cache()
    pol = policy or default_draft_policy_pack()
    cfg = config or default_allocator_config()
    epsilon = pol.epsilon_paise

    ordered_items = tuple(sorted(items, key=sort_key_opportunity))

    if cfg.force_fallback or cfg.k_max <= 0:
        assignments, shadow_estimates = fallback_greedy_allocate(
            ordered_items, resource_state, epsilon
        )
        mode = AllocatorMode.FALLBACK_GREEDY
        duality_gap = None
        shadow_method = "GREEDY_ESTIMATE"
    else:
        relaxed_picks, _best_rvs_unused, lambdas, duality_gap, mode = lagrangian_allocate(
            ordered_items,
            resource_state,
            epsilon,
            cfg,
            lambda_warm_start=lambda_warm_start,
        )
        if mode == AllocatorMode.FALLBACK_GREEDY:
            assignments, shadow_estimates = fallback_greedy_allocate(
                ordered_items, resource_state, epsilon
            )
            shadow_method = "GREEDY_ESTIMATE"
            duality_gap = None
        else:
            best_rvs = {}
            for item in ordered_items:
                pc = relaxed_picks.get(item.opportunity_id)
                if pc is not None:
                    from revive.allocation.lagrangian import _reduced_value_paise

                    best_rvs[item.opportunity_id] = _reduced_value_paise(
                        pc, lambdas, item.customer_id
                    )
                else:
                    best_rvs[item.opportunity_id] = 0
            assignments, shadow_estimates = primal_recovery(
                ordered_items,
                relaxed_picks,
                best_rvs,
                resource_state,
                epsilon,
                lambdas,
            )
            shadow_method = "LAGRANGIAN_DUAL"
            for resource, value in lambdas.items():
                if value > 0:
                    shadow_estimates[resource] = max(
                        shadow_estimates.get(resource, 0.0), value
                    )

    ordered_assignments = tuple(
        assignments[item.opportunity_id]
        for item in sorted(ordered_items, key=sort_key_opportunity)
    )
    total_enrv = sum(
        a.enrv_paise for a in ordered_assignments if a.outcome == DecisionOutcome.SELECTED
    )
    usage_summary = resource_usage_summary(resource_state)
    constraint_lines = _constraint_summary(resource_state)

    allocation_hash = _allocation_hash(
        ordered_items,
        ordered_assignments,
        pol.config_hash(),
        cfg.allocator_version,
    )

    return AllocationResult(
        cycle_id=cycle_id,
        produced_at_micros=now_micros,
        assignments=ordered_assignments,
        allocator_mode=mode,
        allocator_version=cfg.allocator_version,
        policy_pack_version=pol.version,
        total_allocated_enrv_paise=total_enrv,
        shadow_prices={k: v for k, v in shadow_estimates.items() if v > 0},
        shadow_price_method=shadow_method,
        resource_usage=usage_summary,
        budget_usage_paise=resource_state.incentive_budget_used_paise,
        constraint_summary=tuple(constraint_lines),
        allocation_hash=allocation_hash,
        duality_gap=duality_gap,
    )


def default_resource_state(
    capacities: ResourceCapacities | None = None,
) -> ResourceState:
    return ResourceState(capacities=capacities or ResourceCapacities())


def _constraint_summary(state: ResourceState) -> list[str]:
    caps = state.capacities
    lines = [
        f"retry_slots:{state.retry_slots_used}/{caps.retry_slots}",
        f"message_capacity:{state.message_capacity_used}/{caps.message_capacity}",
        f"voice_minutes:{state.voice_minutes_used}/{caps.voice_minutes}",
        f"human_review_slots:{state.human_review_slots_used}/{caps.human_review_slots}",
        f"incentive_budget:{state.incentive_budget_used_paise}/{caps.incentive_budget_paise}",
    ]
    return lines


def _allocation_hash(
    items: tuple[PortfolioItem, ...],
    assignments: tuple,
    policy_hash: str,
    allocator_version: str,
) -> str:
    payload = {
        "items": [i.opportunity_id for i in items],
        "assignments": [a.to_dict() for a in assignments],
        "policy_hash": policy_hash,
        "allocator_version": allocator_version,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
