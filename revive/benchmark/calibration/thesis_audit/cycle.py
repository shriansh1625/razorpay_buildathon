"""Build a single-cycle portfolio snapshot for thesis audit."""

from __future__ import annotations

from dataclasses import dataclass

from revive.allocation import allocate_portfolio, default_allocator_config, default_resource_state
from revive.allocation.models import AllocationResult, PortfolioItem, ResourceCapacities
from revive.benchmark.calibration.b3_revive import b3_greedy_selection, build_portfolio_items
from revive.benchmark.calibration.scarcity import capacities_from_profile
from revive.config.policy_pack import PolicyPack, default_draft_policy_pack
from revive.domain.enums import ActionCode, DecisionOutcome
from revive.simulation.types import GenerationProfile


@dataclass
class CycleSnapshot:
    seed: int
    profile: str
    opportunity_count: int
    customer_count: int
    simulation_window_days: int
    now_micros: int
    items: tuple[PortfolioItem, ...]
    capacities: ResourceCapacities
    policy: PolicyPack
    b3_selections: dict[str, str]
    b3_total_enrv: int
    b3_state: object
    revive_result: AllocationResult
    revive_state: object
    revive_selections: dict[str, str]
    revive_total_enrv: int


def mid_cycle_micros(simulation_window_days: int) -> int:
    return simulation_window_days * 24 * 60 * 60 * 1_000_000 // 2


def build_cycle_snapshot(dataset) -> CycleSnapshot:
    config = dataset.config
    profile = config.profile
    now = mid_cycle_micros(config.simulation_window_days)
    items_list, opp_count = build_portfolio_items(dataset, now)
    items = tuple(items_list)
    caps = capacities_from_profile(profile)
    pack = default_draft_policy_pack()

    b3_state = default_resource_state(caps)
    b3_sel, b3_enrv = b3_greedy_selection(items, b3_state, pack.epsilon_paise)

    revive_state = default_resource_state(caps)
    alloc = allocate_portfolio(
        items,
        revive_state,
        now,
        "thesis_audit",
        policy=pack,
        config=default_allocator_config(),
    )
    revive_sel: dict[str, str] = {}
    revive_enrv = 0
    for a in alloc.assignments:
        if a.outcome == DecisionOutcome.SELECTED and a.action_code != ActionCode.A00:
            revive_sel[a.opportunity_id] = a.action_code.value
            revive_enrv += a.enrv_paise

    return CycleSnapshot(
        seed=config.seed,
        profile=profile.value,
        opportunity_count=opp_count,
        customer_count=config.customer_count,
        simulation_window_days=config.simulation_window_days,
        now_micros=now,
        items=items,
        capacities=caps,
        policy=pack,
        b3_selections=b3_sel,
        b3_total_enrv=b3_enrv,
        b3_state=b3_state,
        revive_result=alloc,
        revive_state=revive_state,
        revive_selections=revive_sel,
        revive_total_enrv=revive_enrv,
    )


def official_scale_dataset(seed: int, profile: GenerationProfile):
    from revive.benchmark.calibration.config import official_scale_config
    from revive.simulation.generator import generate_dataset

    return generate_dataset(official_scale_config(seed, profile))
