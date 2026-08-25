"""B3 vs REVIVE allocation differentiation diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.allocation import allocate_portfolio, default_allocator_config, default_resource_state
from revive.allocation.resources import usage_dict
from revive.config.policy_pack import default_draft_policy_pack
from revive.domain.enums import ActionCode, DecisionOutcome
from revive.recovery.context.assemble import assemble_context
from revive.recovery.candidates.generate import generate_candidates
from revive.recovery.diagnosis.diagnose import diagnose
from revive.recovery.sentinel.detect import detect
from revive.recovery.valuation.price import price_candidates
from revive.simulation.generator import generate_dataset
from revive.simulation.observation import get_observable_state
from revive.simulation.types import GenerationProfile

from revive.benchmark.calibration.scarcity import capacities_from_profile


@dataclass
class B3ReviveCellReport:
    seed: int
    profile: str
    opportunity_count: int
    b3_selections: dict[str, str]
    revive_selections: dict[str, str]
    differing_opportunities: int
    identical_opportunities: int
    b3_only_selected: int
    revive_only_selected: int
    b3_total_enrv_paise: int = 0
    revive_total_enrv_paise: int = 0
    b3_retry_slots_used: int = 0
    b3_message_capacity_used: int = 0
    revive_retry_slots_used: int = 0
    revive_message_capacity_used: int = 0
    revive_deferred_count: int = 0
    revive_shadow_prices: dict[str, float] = field(default_factory=dict)
    retry_capacity: int = 0
    message_capacity: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "profile": self.profile,
            "opportunity_count": self.opportunity_count,
            "differing_opportunities": self.differing_opportunities,
            "identical_opportunities": self.identical_opportunities,
            "b3_only_selected": self.b3_only_selected,
            "revive_only_selected": self.revive_only_selected,
            "b3_total_enrv_paise": self.b3_total_enrv_paise,
            "revive_total_enrv_paise": self.revive_total_enrv_paise,
            "b3_retry_slots_used": self.b3_retry_slots_used,
            "b3_message_capacity_used": self.b3_message_capacity_used,
            "revive_retry_slots_used": self.revive_retry_slots_used,
            "revive_message_capacity_used": self.revive_message_capacity_used,
            "revive_deferred_count": self.revive_deferred_count,
            "revive_shadow_prices": self.revive_shadow_prices,
            "retry_capacity": self.retry_capacity,
            "message_capacity": self.message_capacity,
            "b3_selections": self.b3_selections,
            "revive_selections": self.revive_selections,
        }


@dataclass
class B3ReviveReport:
    cells: list[B3ReviveCellReport] = field(default_factory=list)
    classification: str = "UNKNOWN"
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "rationale": self.rationale,
            "cells": [c.to_dict() for c in self.cells],
        }


def b3_greedy_selection(items, state, epsilon_paise: int) -> tuple[dict[str, str], int]:
    """B3-style raw ENRV greedy — returns selections and total ENRV."""
    from revive.allocation.resources import can_reserve, reserve

    ranked: list[tuple[int, str, object, object]] = []
    for item in items:
        best = None
        best_enrv = epsilon_paise
        for pc in item.candidates:
            if pc.action_code == ActionCode.A00:
                continue
            if pc.enrv_paise > best_enrv:
                best_enrv = pc.enrv_paise
                best = pc
        if best is not None:
            ranked.append((best_enrv, item.opportunity_id, item, best))
    ranked.sort(key=lambda t: (-t[0], t[1]))

    selected: dict[str, str] = {}
    total_enrv = 0
    for enrv, opp_id, item, pc in ranked:
        if opp_id in selected:
            continue
        usage = usage_dict(pc)
        if can_reserve(state, usage, item.customer_id):
            if reserve(state, usage, item.customer_id):
                selected[opp_id] = pc.action_code.value
                total_enrv += enrv
    return selected, total_enrv


def build_portfolio_items(dataset, now_micros: int):
    view = get_observable_state(dataset.world)
    sentinel = detect(view, now_micros)
    pack = default_draft_policy_pack()
    items = []
    for opp in sentinel.opportunities:
        ctx = assemble_context(opp, view, now_micros)
        dx = diagnose(opp, ctx, view, now_micros, "cal")
        cand_set = generate_candidates(
            opp, dx.observable_context, dx, now_micros, "cal", policy=pack
        )
        val_result = price_candidates(
            opp, dx.observable_context, dx, cand_set, now_micros, policy=pack
        )
        from revive.allocation import portfolio_item_from_valuation

        items.append(
            portfolio_item_from_valuation(
                opp.opportunity_id,
                opp.customer_id,
                opp.value_at_risk_paise,
                cand_set.candidates,
                val_result.valuations,
            )
        )
    return items, len(sentinel.opportunities)


def analyze_b3_revive_cell(dataset) -> B3ReviveCellReport:
    config = dataset.config
    profile = config.profile
    now_micros = config.simulation_window_days * 24 * 60 * 60 * 1_000_000 // 2
    items, opp_count = build_portfolio_items(dataset, now_micros)

    caps = capacities_from_profile(profile)
    pack = default_draft_policy_pack()

    b3_state = default_resource_state(caps)
    b3_sel, b3_enrv = b3_greedy_selection(items, b3_state, pack.epsilon_paise)

    revive_state = default_resource_state(caps)
    alloc = allocate_portfolio(
        tuple(items),
        revive_state,
        now_micros,
        "cal_b3",
        policy=pack,
        config=default_allocator_config(),
    )
    revive_sel: dict[str, str] = {}
    revive_enrv = 0
    deferred = 0
    for a in alloc.assignments:
        if a.outcome == DecisionOutcome.DEFERRED:
            deferred += 1
        if a.outcome == DecisionOutcome.SELECTED and a.action_code != ActionCode.A00:
            revive_sel[a.opportunity_id] = a.action_code.value
            revive_enrv += a.enrv_paise

    all_opps = {i.opportunity_id for i in items}
    differing = 0
    identical = 0
    b3_only = 0
    revive_only = 0

    for opp_id in all_opps:
        b3_action = b3_sel.get(opp_id)
        rev_action = revive_sel.get(opp_id)
        if b3_action == rev_action:
            identical += 1
        else:
            differing += 1
        if b3_action and not rev_action:
            b3_only += 1
        if rev_action and not b3_action:
            revive_only += 1

    return B3ReviveCellReport(
        seed=config.seed,
        profile=profile.value,
        opportunity_count=opp_count,
        b3_selections=b3_sel,
        revive_selections=revive_sel,
        differing_opportunities=differing,
        identical_opportunities=identical,
        b3_only_selected=b3_only,
        revive_only_selected=revive_only,
        b3_total_enrv_paise=b3_enrv,
        revive_total_enrv_paise=revive_enrv,
        b3_retry_slots_used=b3_state.retry_slots_used,
        b3_message_capacity_used=b3_state.message_capacity_used,
        revive_retry_slots_used=revive_state.retry_slots_used,
        revive_message_capacity_used=revive_state.message_capacity_used,
        revive_deferred_count=deferred,
        revive_shadow_prices=dict(alloc.shadow_prices),
        retry_capacity=caps.retry_slots,
        message_capacity=caps.message_capacity,
    )


def classify_b3_revive(cells: list[B3ReviveCellReport]) -> tuple[str, str]:
    if not cells:
        return "COLLAPSED", "no cells"

    diff_rates = []
    for c in cells:
        total = max(1, c.opportunity_count)
        diff_rates.append(c.differing_opportunities / total)

    avg_diff = sum(diff_rates) / len(diff_rates)
    strong_cells = sum(1 for r in diff_rates if r >= 0.15)
    acceptable_cells = sum(1 for r in diff_rates if 0.03 <= r < 0.15)
    weak_cells = sum(1 for r in diff_rates if 0 < r < 0.03)

    scarce_cells = [c for c in cells if c.profile == "SCARCE"]
    scarce_diff = (
        sum(c.differing_opportunities for c in scarce_cells) / max(1, len(scarce_cells))
        if scarce_cells
        else 0.0
    )

    if avg_diff >= 0.15 or strong_cells >= len(cells) * 0.25:
        label = "STRONG"
    elif avg_diff >= 0.03 or acceptable_cells >= len(cells) * 0.15 or scarce_diff >= 1.0:
        label = "ACCEPTABLE"
    elif avg_diff > 0 or weak_cells > 0:
        label = "WEAK"
    else:
        label = "COLLAPSED"

    rationale = (
        f"avg_diff_rate={avg_diff:.3f}, strong={strong_cells}, "
        f"acceptable={acceptable_cells}, weak={weak_cells}, scarce_avg_diff={scarce_diff:.2f}"
    )
    return label, rationale


def run_b3_revive_diagnostics(
    seeds: tuple[int, ...],
    profiles: tuple,
    config_factory=None,
) -> B3ReviveReport:
    from revive.benchmark.calibration.config import calibration_config

    factory = config_factory or calibration_config
    cells: list[B3ReviveCellReport] = []
    for seed in seeds:
        for profile in profiles:
            if not isinstance(profile, GenerationProfile):
                profile = GenerationProfile(profile)
            dataset = generate_dataset(factory(seed, profile))
            cells.append(analyze_b3_revive_cell(dataset))

    classification, rationale = classify_b3_revive(cells)
    return B3ReviveReport(
        cells=cells,
        classification=classification,
        rationale=rationale,
    )
