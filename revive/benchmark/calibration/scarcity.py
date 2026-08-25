"""Scarcity and resource-competition diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.allocation import allocate_portfolio, default_resource_state, ResourceCapacities
from revive.allocation.resources import portfolio_item_from_valuation, usage_dict
from revive.config.policy_pack import default_draft_policy_pack
from revive.domain.enums import ActionCode
from revive.recovery.context.assemble import assemble_context
from revive.recovery.candidates.generate import generate_candidates
from revive.recovery.diagnosis.diagnose import diagnose
from revive.recovery.sentinel.detect import detect
from revive.recovery.valuation.price import price_candidates
from revive.simulation.generator import generate_dataset
from revive.simulation.observation import get_observable_state
from revive.benchmark.capacities import benchmark_resource_capacities
from revive.simulation.profiles import profile_parameters
from revive.simulation.types import GenerationProfile


@dataclass
class ScarcityCellReport:
    seed: int
    profile: str
    opportunity_count: int
    positive_enrv_candidates: int
    total_retry_demand: int
    total_message_demand: int
    total_contact_demand: int
    retry_capacity: int
    message_capacity: int
    competition_ratio_retry: float
    competition_ratio_message: float
    candidates_per_retry_slot: float
    profile_scarcity_factor: float
    capacities_profile_adjusted: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "profile": self.profile,
            "opportunity_count": self.opportunity_count,
            "positive_enrv_candidates": self.positive_enrv_candidates,
            "total_retry_demand": self.total_retry_demand,
            "total_message_demand": self.total_message_demand,
            "total_contact_demand": self.total_contact_demand,
            "retry_capacity": self.retry_capacity,
            "message_capacity": self.message_capacity,
            "competition_ratio_retry": self.competition_ratio_retry,
            "competition_ratio_message": self.competition_ratio_message,
            "candidates_per_retry_slot": self.candidates_per_retry_slot,
            "profile_scarcity_factor": self.profile_scarcity_factor,
            "capacities_profile_adjusted": self.capacities_profile_adjusted,
        }


@dataclass
class ScarcityReport:
    cells: list[ScarcityCellReport] = field(default_factory=list)
    classification: str = "UNKNOWN"
    rationale: str = ""
    benchmark_wires_profile_capacities: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "rationale": self.rationale,
            "benchmark_wires_profile_capacities": self.benchmark_wires_profile_capacities,
            "cells": [c.to_dict() for c in self.cells],
        }


def capacities_from_profile(profile: GenerationProfile) -> ResourceCapacities:
    """Profile-adjusted capacities — same path as official benchmark runner."""
    return benchmark_resource_capacities(profile)


def analyze_scarcity_cell(dataset, *, use_profile_capacities: bool = True) -> ScarcityCellReport:
    config = dataset.config
    profile = config.profile
    world = dataset.world
    now_micros = config.simulation_window_days * 24 * 60 * 60 * 1_000_000 // 2

    view = get_observable_state(world)
    sentinel = detect(view, now_micros)
    pack = default_draft_policy_pack()

    positive_enrv = 0
    retry_demand = 0
    message_demand = 0
    contact_demand = 0
    portfolio_items = []

    for opp in sentinel.opportunities:
        ctx = assemble_context(opp, view, now_micros)
        dx = diagnose(opp, ctx, view, now_micros, "cal")
        cand_set = generate_candidates(opp, dx.observable_context, dx, now_micros, "cal", policy=pack)
        val_result = price_candidates(
            opp, dx.observable_context, dx, cand_set, now_micros, policy=pack
        )
        item = portfolio_item_from_valuation(
            opp.opportunity_id,
            opp.customer_id,
            opp.value_at_risk_paise,
            cand_set.candidates,
            val_result.valuations,
        )
        portfolio_items.append(item)

        for pc in item.candidates:
            if pc.action_code == ActionCode.A00 or pc.enrv_paise <= pack.epsilon_paise:
                continue
            positive_enrv += 1
            usage = usage_dict(pc)
            retry_demand += usage.get("retry_slots", 0)
            message_demand += usage.get("message_capacity", 0)
            contact_demand += usage.get("contact_allowance", 0)

    caps = (
        capacities_from_profile(profile)
        if use_profile_capacities
        else ResourceCapacities()
    )

    retry_cap = caps.retry_slots
    message_cap = caps.message_capacity
    competition_retry = retry_demand / max(1, retry_cap)
    competition_message = message_demand / max(1, message_cap)
    candidates_per_retry = positive_enrv / max(1, retry_cap)

    return ScarcityCellReport(
        seed=config.seed,
        profile=profile.value,
        opportunity_count=len(sentinel.opportunities),
        positive_enrv_candidates=positive_enrv,
        total_retry_demand=retry_demand,
        total_message_demand=message_demand,
        total_contact_demand=contact_demand,
        retry_capacity=retry_cap,
        message_capacity=message_cap,
        competition_ratio_retry=competition_retry,
        competition_ratio_message=competition_message,
        candidates_per_retry_slot=candidates_per_retry,
        profile_scarcity_factor=profile_parameters(profile).capacity_scarcity_factor,
        capacities_profile_adjusted=use_profile_capacities,
    )


def classify_scarcity(cells: list[ScarcityCellReport]) -> tuple[str, str]:
    if not cells:
        return "LOW SCARCITY", "no cells"

    ratios = [max(c.competition_ratio_retry, c.competition_ratio_message) for c in cells]
    avg_ratio = sum(ratios) / len(ratios)
    high_cells = sum(1 for r in ratios if r >= 2.0)
    mod_cells = sum(1 for r in ratios if 1.0 <= r < 2.0)

    if avg_ratio >= 2.0 or high_cells >= len(cells) * 0.4:
        return "HIGH SCARCITY", f"avg_competition_ratio={avg_ratio:.2f}, high_cells={high_cells}"
    if avg_ratio >= 1.0 or mod_cells >= len(cells) * 0.3:
        return "MODERATE SCARCITY", f"avg_competition_ratio={avg_ratio:.2f}, moderate_cells={mod_cells}"
    return "LOW SCARCITY", f"avg_competition_ratio={avg_ratio:.2f}"


def run_scarcity_analysis(
    seeds: tuple[int, ...],
    profiles: tuple,
    config_factory=None,
) -> ScarcityReport:
    from revive.benchmark.calibration.config import calibration_config
    from revive.simulation.types import GenerationProfile

    factory = config_factory or calibration_config
    cells: list[ScarcityCellReport] = []
    for seed in seeds:
        for profile in profiles:
            if not isinstance(profile, GenerationProfile):
                profile = GenerationProfile(profile)
            dataset = generate_dataset(factory(seed, profile))
            cells.append(analyze_scarcity_cell(dataset, use_profile_capacities=True))

    classification, rationale = classify_scarcity(cells)
    return ScarcityReport(
        cells=cells,
        classification=classification,
        rationale=rationale,
        benchmark_wires_profile_capacities=True,
    )
