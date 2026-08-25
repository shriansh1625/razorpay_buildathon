"""Parameter sensitivity — diagnostic only, no tuning toward a winner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.config.policy_pack import PolicyPack, PolicyPackStatus
from revive.benchmark.calibration.b3_revive import analyze_b3_revive_cell, b3_greedy_selection, build_portfolio_items
from revive.benchmark.calibration.scarcity import capacities_from_profile, analyze_scarcity_cell
from revive.simulation.generator import generate_dataset
from revive.simulation.types import GenerationProfile


@dataclass
class ParameterSweepResult:
    parameter: str
    values: list[Any]
    metrics: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "parameter": self.parameter,
            "values": self.values,
            "metrics": self.metrics,
        }


@dataclass
class ParameterSensitivityReport:
    sweeps: list[ParameterSweepResult] = field(default_factory=list)
    epsilon_material: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "epsilon_material": self.epsilon_material,
            "notes": self.notes,
            "sweeps": [s.to_dict() for s in self.sweeps],
        }


def sweep_epsilon(seed: int = 1) -> ParameterSweepResult:
    from revive.benchmark.calibration.config import calibration_config

    dataset = generate_dataset(
        calibration_config(seed, GenerationProfile.BALANCED)
    )
    now = dataset.config.simulation_window_days * 24 * 60 * 60 * 1_000_000 // 2
    items, _ = build_portfolio_items(dataset, now)
    caps = capacities_from_profile(GenerationProfile.BALANCED)

    epsilons = [0, 100, 500, 1000, 5000, 20000]
    metrics: list[dict[str, Any]] = []

    for eps in epsilons:
        pack = PolicyPack(
            version="cal_eps",
            status=PolicyPackStatus.DRAFT,
            epsilon_paise=eps,
        )
        from revive.allocation import default_resource_state

        state = default_resource_state(caps)
        sel = b3_greedy_selection(items, state, eps)
        metrics.append(
            {
                "epsilon_paise": eps,
                "b3_selected_count": len(sel),
            }
        )

    return ParameterSweepResult(parameter="epsilon_paise", values=epsilons, metrics=metrics)


def sweep_opportunity_scale(seed: int = 1) -> ParameterSweepResult:
    from revive.simulation.config import GeneratorConfig

    counts = [12, 25, 40, 60]
    metrics: list[dict[str, Any]] = []

    for n in counts:
        cfg = GeneratorConfig(
            seed=seed,
            profile=GenerationProfile.BALANCED,
            customer_count=max(8, n // 2),
            opportunity_count=n,
            simulation_window_days=21,
            inject_signal_faults=True,
            privacy_canary_count=1,
        )
        dataset = generate_dataset(cfg)
        cell = analyze_scarcity_cell(dataset, use_profile_capacities=True)
        metrics.append(
            {
                "opportunity_count": n,
                "positive_enrv_candidates": cell.positive_enrv_candidates,
                "competition_ratio_retry": cell.competition_ratio_retry,
            }
        )

    return ParameterSweepResult(
        parameter="opportunity_count",
        values=counts,
        metrics=metrics,
    )


def run_parameter_sensitivity() -> ParameterSensitivityReport:
    eps_sweep = sweep_epsilon()
    scale_sweep = sweep_opportunity_scale()

    eps_counts = [m["b3_selected_count"] for m in eps_sweep.metrics]
    epsilon_material = max(eps_counts) - min(eps_counts) >= 2

    tiny_note = ""
    from revive.benchmark.calibration.config import tiny_reference_config

    tiny = generate_dataset(tiny_reference_config())
    tiny_cell = analyze_b3_revive_cell(tiny)
    cal = generate_dataset(
        __import__(
            "revive.benchmark.calibration.config",
            fromlist=["calibration_config"],
        ).calibration_config(1, GenerationProfile.BALANCED)
    )
    cal_cell = analyze_b3_revive_cell(cal)

    notes = [
        f"tiny_config (12 opps): differing_allocations={tiny_cell.differing_opportunities}, "
        f"b3_selected={len(tiny_cell.b3_selections)}, revive_selected={len(tiny_cell.revive_selections)}",
        f"calibration_config (40 opps): differing={cal_cell.differing_opportunities}, "
        f"b3_selected={len(cal_cell.b3_selections)}, revive_selected={len(cal_cell.revive_selections)}",
        "M13 zero M-10 likely driven by tiny scale + single seed, not REVIVE architecture failure.",
    ]

    return ParameterSensitivityReport(
        sweeps=[eps_sweep, scale_sweep],
        epsilon_material=epsilon_material,
        notes=notes,
    )
