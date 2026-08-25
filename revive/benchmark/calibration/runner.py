"""Calibration diagnostic runner — M13.5."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.benchmark.calibration.action_sensitivity import run_action_sensitivity_analysis
from revive.benchmark.calibration.b3_revive import run_b3_revive_diagnostics
from revive.benchmark.calibration.baseline_separation import run_baseline_separation
from revive.benchmark.calibration.config import (
    CALIBRATION_PROFILES,
    CALIBRATION_SEEDS,
    CALIBRATION_VERSION,
)
from revive.benchmark.calibration.environment import run_environment_diagnostics
from revive.benchmark.calibration.freeze_readiness import build_freeze_readiness
from revive.benchmark.calibration.integrity import run_integrity_checks
from revive.benchmark.calibration.natural_recovery import run_natural_recovery_analysis
from revive.benchmark.calibration.parameter_sensitivity import run_parameter_sensitivity
from revive.benchmark.calibration.scarcity import run_scarcity_analysis
from revive.benchmark.official.config import BenchmarkMode
from revive.benchmark.official.reproduce import reproduce_benchmark


@dataclass
class CalibrationReport:
    version: str
    environment_cells: list = field(default_factory=list)
    baseline_separation: Any = None
    scarcity: Any = None
    action_sensitivity: Any = None
    natural_recovery: Any = None
    b3_revive: Any = None
    parameter_sensitivity: Any = None
    integrity: Any = None
    freeze_readiness: Any = None
    reproduction_identical: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "reproduction_identical": self.reproduction_identical,
            "environment_cells": [c.to_dict() for c in self.environment_cells],
            "baseline_separation": self.baseline_separation.to_dict()
            if self.baseline_separation
            else {},
            "scarcity": self.scarcity.to_dict() if self.scarcity else {},
            "action_sensitivity": self.action_sensitivity.to_dict()
            if self.action_sensitivity
            else {},
            "natural_recovery": self.natural_recovery.to_dict()
            if self.natural_recovery
            else {},
            "b3_revive": self.b3_revive.to_dict() if self.b3_revive else {},
            "parameter_sensitivity": self.parameter_sensitivity.to_dict()
            if self.parameter_sensitivity
            else {},
            "integrity": self.integrity.to_dict() if self.integrity else {},
            "freeze_readiness": self.freeze_readiness.to_dict()
            if self.freeze_readiness
            else {},
        }


def run_calibration_diagnostics(
    *,
    seeds: tuple[int, ...] = CALIBRATION_SEEDS,
    profiles: tuple = CALIBRATION_PROFILES,
    skip_reproduction: bool = False,
) -> CalibrationReport:
    env_cells = run_environment_diagnostics(seeds, profiles)
    baseline = run_baseline_separation(seeds, profiles)
    scarcity = run_scarcity_analysis(seeds, profiles)
    action = run_action_sensitivity_analysis(seeds, profiles)
    natural = run_natural_recovery_analysis(env_cells)
    b3_revive = run_b3_revive_diagnostics(seeds, profiles)
    params = run_parameter_sensitivity()
    integrity = run_integrity_checks()

    repro_identical = True
    if not skip_reproduction:
        rep = reproduce_benchmark(mode=BenchmarkMode.DEVELOPMENT)
        repro_identical = rep.identical

    freeze = build_freeze_readiness(
        env_cells,
        baseline,
        scarcity,
        action,
        natural,
        b3_revive,
        integrity,
        params,
        repro_identical,
    )

    return CalibrationReport(
        version=CALIBRATION_VERSION,
        environment_cells=env_cells,
        baseline_separation=baseline,
        scarcity=scarcity,
        action_sensitivity=action,
        natural_recovery=natural,
        b3_revive=b3_revive,
        parameter_sensitivity=params,
        integrity=integrity,
        freeze_readiness=freeze,
        reproduction_identical=repro_identical,
    )
