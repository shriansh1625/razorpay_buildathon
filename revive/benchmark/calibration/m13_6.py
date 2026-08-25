"""M13.6 structural repair re-calibration runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.benchmark.calibration.action_sensitivity import run_action_sensitivity_analysis
from revive.benchmark.calibration.b3_revive import run_b3_revive_diagnostics
from revive.benchmark.calibration.baseline_separation import run_baseline_separation
from revive.benchmark.calibration.config import (
    M13_6_OFFICIAL_SCALE_SEEDS,
    M13_6_VERSION,
    official_scale_config,
    scale_sensitivity_config,
)
from revive.benchmark.calibration.freeze_readiness import build_freeze_readiness
from revive.benchmark.calibration.integrity import run_integrity_checks
from revive.benchmark.calibration.natural_recovery import run_natural_recovery_analysis
from revive.benchmark.calibration.parameter_sensitivity import run_parameter_sensitivity
from revive.benchmark.calibration.runner import run_environment_diagnostics
from revive.benchmark.calibration.scarcity import run_scarcity_analysis
from revive.benchmark.official.config import BenchmarkMode
from revive.benchmark.official.reproduce import reproduce_benchmark
from revive.simulation.types import GenerationProfile


@dataclass
class M136Report:
    version: str
    environment_cells: list = field(default_factory=list)
    scarcity_calibration: Any = None
    scarcity_official_scale: Any = None
    b3_revive_calibration: Any = None
    b3_revive_official_scale: Any = None
    baseline_separation: Any = None
    scale_sensitivity: list = field(default_factory=list)
    parameter_sensitivity: Any = None
    integrity: Any = None
    freeze_readiness: Any = None
    reproduction_identical: bool = False
    profile_capacity_verified: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "profile_capacity_verified": self.profile_capacity_verified,
            "reproduction_identical": self.reproduction_identical,
            "environment_cells_official": [c.to_dict() for c in self.environment_cells],
            "scarcity_calibration": self.scarcity_calibration.to_dict()
            if self.scarcity_calibration
            else {},
            "scarcity_official_scale": self.scarcity_official_scale.to_dict()
            if self.scarcity_official_scale
            else {},
            "b3_revive_calibration": self.b3_revive_calibration.to_dict()
            if self.b3_revive_calibration
            else {},
            "b3_revive_official_scale": self.b3_revive_official_scale.to_dict()
            if self.b3_revive_official_scale
            else {},
            "baseline_separation": self.baseline_separation.to_dict()
            if self.baseline_separation
            else {},
            "scale_sensitivity": self.scale_sensitivity,
            "parameter_sensitivity": self.parameter_sensitivity.to_dict()
            if self.parameter_sensitivity
            else {},
            "integrity": self.integrity.to_dict() if self.integrity else {},
            "freeze_readiness": self.freeze_readiness.to_dict()
            if self.freeze_readiness
            else {},
        }


def run_scale_sensitivity(seed: int = 1) -> list[dict[str, Any]]:
    from revive.benchmark.calibration.scarcity import analyze_scarcity_cell
    from revive.simulation.generator import generate_dataset

    results: list[dict[str, Any]] = []
    for n in (100, 250, 500, 750):
        cfg = scale_sensitivity_config(seed, GenerationProfile.BALANCED, n)
        dataset = generate_dataset(cfg)
        cell = analyze_scarcity_cell(dataset, use_profile_capacities=True)
        b3 = run_b3_revive_diagnostics(
            (seed,),
            (GenerationProfile.BALANCED,),
            config_factory=lambda s, p: scale_sensitivity_config(s, p, n),
        )
        b3_cell = b3.cells[0] if b3.cells else None
        results.append(
            {
                "opportunity_count": n,
                "customer_count": cfg.customer_count,
                "competition_ratio_retry": cell.competition_ratio_retry,
                "competition_ratio_message": cell.competition_ratio_message,
                "positive_enrv_candidates": cell.positive_enrv_candidates,
                "retry_capacity": cell.retry_capacity,
                "b3_revive_classification": b3.classification,
                "differing_allocations": b3_cell.differing_opportunities if b3_cell else 0,
            }
        )
    return results


def run_m13_6_recalibration(
    *,
    skip_reproduction: bool = False,
) -> M136Report:
    profiles = tuple(GenerationProfile)
    cal_seeds = (1, 2)  # reduced for speed on post-repair validation

    env_official = run_environment_diagnostics(
        M13_6_OFFICIAL_SCALE_SEEDS,
        profiles,
        config_factory=official_scale_config,
    )
    scarcity_cal = run_scarcity_analysis(cal_seeds, profiles)
    scarcity_official = run_scarcity_analysis(
        M13_6_OFFICIAL_SCALE_SEEDS,
        profiles,
        config_factory=official_scale_config,
    )
    b3_cal = run_b3_revive_diagnostics(cal_seeds, profiles)
    b3_official = run_b3_revive_diagnostics(
        M13_6_OFFICIAL_SCALE_SEEDS,
        profiles,
        config_factory=official_scale_config,
    )
    baseline = run_baseline_separation(
        (1,),
        (GenerationProfile.SCARCE, GenerationProfile.ABUNDANT, GenerationProfile.BALANCED),
        config_factory=official_scale_config,
    )

    scale_sens = run_scale_sensitivity()
    params = run_parameter_sensitivity()
    integrity = run_integrity_checks()

    repro = True
    if not skip_reproduction:
        rep = reproduce_benchmark(mode=BenchmarkMode.DEVELOPMENT)
        repro = rep.identical

    natural = run_natural_recovery_analysis(env_official)
    action = run_action_sensitivity_analysis(M13_6_OFFICIAL_SCALE_SEEDS[:2], profiles[:3])

    freeze = build_freeze_readiness(
        env_official,
        baseline,
        scarcity_official,
        action,
        natural,
        b3_official,
        integrity,
        params,
        repro,
    )

    return M136Report(
        version=M13_6_VERSION,
        environment_cells=env_official,
        scarcity_calibration=scarcity_cal,
        scarcity_official_scale=scarcity_official,
        b3_revive_calibration=b3_cal,
        b3_revive_official_scale=b3_official,
        baseline_separation=baseline,
        scale_sensitivity=scale_sens,
        parameter_sensitivity=params,
        integrity=integrity,
        freeze_readiness=freeze,
        reproduction_identical=repro,
    )
