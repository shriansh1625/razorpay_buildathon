"""Baseline separation diagnostics — B0–B3 behavior, no modification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.benchmark.runner import run_baseline_cycle
from revive.benchmark.types import BaselinePolicyId
from revive.config.policy_pack import PolicyPack, default_draft_policy_pack
from revive.domain.enums import ActionCode, DecisionOutcome
from revive.simulation.generator import generate_dataset
from revive.simulation.observation import get_observable_state


@dataclass
class BaselineBehaviorSnapshot:
    policy_id: str
    seed: int
    profile: str
    selected_count: int
    deferred_count: int
    no_action_count: int
    action_mix: dict[str, int] = field(default_factory=dict)
    total_enrv_selected_paise: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "seed": self.seed,
            "profile": self.profile,
            "selected_count": self.selected_count,
            "deferred_count": self.deferred_count,
            "no_action_count": self.no_action_count,
            "action_mix": self.action_mix,
            "total_enrv_selected_paise": self.total_enrv_selected_paise,
        }


@dataclass
class BaselineSeparationReport:
    snapshots: list[BaselineBehaviorSnapshot] = field(default_factory=list)
    classification: str = "UNKNOWN"
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "rationale": self.rationale,
            "snapshots": [s.to_dict() for s in self.snapshots],
        }


def _mid_cycle_micros(config) -> int:
    days = config.simulation_window_days
    from revive.benchmark.official.world import DAY_MICROS

    return (days * DAY_MICROS) // 2


def snapshot_baseline(
    policy_id: BaselinePolicyId,
    dataset,
    policy_pack: PolicyPack,
    now_micros: int,
) -> BaselineBehaviorSnapshot:
    view = get_observable_state(dataset.world)
    result = run_baseline_cycle(
        policy_id,
        view,
        cycle_id="cal_mid",
        now_micros=now_micros,
        policy_pack=policy_pack,
    )

    selected = 0
    deferred = 0
    no_action = 0
    action_mix: dict[str, int] = {}
    enrv_sum = 0

    for d in result.decisions:
        if d.outcome == DecisionOutcome.SELECTED:
            selected += 1
            action_mix[d.action_code.value] = action_mix.get(d.action_code.value, 0) + 1
            enrv_sum += d.enrv_estimate_paise or 0
        elif d.outcome == DecisionOutcome.DEFERRED:
            deferred += 1
        else:
            no_action += 1

    return BaselineBehaviorSnapshot(
        policy_id=policy_id.value,
        seed=dataset.config.seed,
        profile=dataset.config.profile.value,
        selected_count=selected,
        deferred_count=deferred,
        no_action_count=no_action,
        action_mix=action_mix,
        total_enrv_selected_paise=enrv_sum,
    )


def classify_baseline_separation(snapshots: list[BaselineBehaviorSnapshot]) -> tuple[str, str]:
    """Per-cell: compare B0–B3 selected counts and action mixes."""
    if not snapshots:
        return "COLLAPSED", "no snapshots"

    by_cell: dict[tuple[int, str], dict[str, BaselineBehaviorSnapshot]] = {}
    for s in snapshots:
        by_cell.setdefault((s.seed, s.profile), {})[s.policy_id] = s

    collapsed_cells = 0
    partial_cells = 0
    clear_cells = 0

    for cell_snaps in by_cell.values():
        policies = ["B0", "B1", "B2", "B3"]
        if not all(p in cell_snaps for p in policies):
            continue
        selected = [cell_snaps[p].selected_count for p in policies]
        mixes = [frozenset(cell_snaps[p].action_mix.items()) for p in policies]

        if selected == [0, 0, 0, 0]:
            collapsed_cells += 1
            continue

        unique_selected = len(set(selected))
        unique_mixes = len(set(mixes))
        if unique_selected >= 3 or unique_mixes >= 3:
            clear_cells += 1
        elif unique_selected >= 2 or unique_mixes >= 2:
            partial_cells += 1
        else:
            collapsed_cells += 1

    total = clear_cells + partial_cells + collapsed_cells
    if total == 0:
        return "COLLAPSED", "no complete baseline cells"

    if clear_cells >= total * 0.5:
        return "CLEARLY_SEPARATED", f"{clear_cells}/{total} cells show clear policy differences"
    if collapsed_cells >= total * 0.5:
        return "COLLAPSED", f"{collapsed_cells}/{total} cells show identical baseline behavior"
    return "PARTIALLY_SEPARATED", f"clear={clear_cells}, partial={partial_cells}, collapsed={collapsed_cells}"


def run_baseline_separation(
    seeds: tuple[int, ...],
    profiles: tuple,
    config_factory=None,
) -> BaselineSeparationReport:
    from revive.benchmark.calibration.config import calibration_config
    from revive.simulation.types import GenerationProfile

    pack = default_draft_policy_pack()
    factory = config_factory or calibration_config
    snapshots: list[BaselineBehaviorSnapshot] = []

    for seed in seeds:
        for profile in profiles:
            if not isinstance(profile, GenerationProfile):
                profile = GenerationProfile(profile)
            dataset = generate_dataset(factory(seed, profile))
            now = _mid_cycle_micros(dataset.config)
            for pid in BaselinePolicyId:
                snapshots.append(snapshot_baseline(pid, dataset, pack, now))

    classification, rationale = classify_baseline_separation(snapshots)
    return BaselineSeparationReport(
        snapshots=snapshots,
        classification=classification,
        rationale=rationale,
    )
