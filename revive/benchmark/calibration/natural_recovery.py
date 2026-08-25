"""Natural recovery distribution analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.simulation.generator import generate_dataset


@dataclass
class NaturalRecoveryReport:
    per_profile_rates: dict[str, list[float]] = field(default_factory=dict)
    overall_min_rate: float = 0.0
    overall_max_rate: float = 0.0
    overall_std: float = 0.0
    low_incremental_cells: int = 0
    high_incremental_cells: int = 0
    classification: str = "UNKNOWN"
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "rationale": self.rationale,
            "per_profile_rates": self.per_profile_rates,
            "overall_min_rate": self.overall_min_rate,
            "overall_max_rate": self.overall_max_rate,
            "overall_std": self.overall_std,
            "low_incremental_cells": self.low_incremental_cells,
            "high_incremental_cells": self.high_incremental_cells,
        }


def run_natural_recovery_analysis(env_cells: list) -> NaturalRecoveryReport:
    rates = [c.natural_recovery_rate for c in env_cells]
    per_profile: dict[str, list[float]] = {}
    low_inc = 0
    high_inc = 0

    for c in env_cells:
        per_profile.setdefault(c.profile, []).append(c.natural_recovery_rate)
        sensitive = c.intervention_sensitive_count
        natural = c.natural_recovery_count
        if sensitive <= natural * 0.5:
            low_inc += 1
        if sensitive >= c.opportunity_count - natural:
            high_inc += 1

    if not rates:
        return NaturalRecoveryReport(
            classification="COLLAPSED",
            rationale="no environment cells",
        )

    min_r = min(rates)
    max_r = max(rates)
    mean_r = sum(rates) / len(rates)
    variance = sum((r - mean_r) ** 2 for r in rates) / len(rates)
    std = variance ** 0.5

    if std >= 0.12 and (max_r - min_r) >= 0.2:
        classification = "HEALTHY"
        rationale = f"std={std:.3f}, range=[{min_r:.2f},{max_r:.2f}]"
    elif std >= 0.05 or (max_r - min_r) >= 0.1:
        classification = "WEAK"
        rationale = f"limited variation std={std:.3f}"
    else:
        classification = "COLLAPSED"
        rationale = f"natural recovery nearly constant std={std:.3f}"

    return NaturalRecoveryReport(
        per_profile_rates=per_profile,
        overall_min_rate=min_r,
        overall_max_rate=max_r,
        overall_std=std,
        low_incremental_cells=low_inc,
        high_incremental_cells=high_inc,
        classification=classification,
        rationale=rationale,
    )
