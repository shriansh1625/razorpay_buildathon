"""Action outcome sensitivity from oracle partition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.domain.enums import ActionCode
from revive.simulation.generator import generate_dataset


@dataclass
class ActionSensitivityReport:
    avg_recovering_actions_per_opp: float = 0.0
    avg_action_outcome_variance: float = 0.0
    action_recovery_rates: dict[str, float] = field(default_factory=dict)
    classification: str = "UNKNOWN"
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "rationale": self.rationale,
            "avg_recovering_actions_per_opp": self.avg_recovering_actions_per_opp,
            "avg_action_outcome_variance": self.avg_action_outcome_variance,
            "action_recovery_rates": self.action_recovery_rates,
        }


def run_action_sensitivity_analysis(
    seeds: tuple[int, ...],
    profiles: tuple,
) -> ActionSensitivityReport:
    from revive.benchmark.calibration.config import calibration_config
    from revive.simulation.types import GenerationProfile

    recovering_counts: list[int] = []
    action_totals: dict[str, int] = {}
    action_success: dict[str, int] = {}
    variance_samples: list[float] = []

    for seed in seeds:
        for profile in profiles:
            if not isinstance(profile, GenerationProfile):
                profile = GenerationProfile(profile)
            dataset = generate_dataset(calibration_config(seed, profile))
            partition = dataset.oracle_partition

            for row in partition.rows.values():
                recovering = 0
                outcomes: list[float] = []
                for code, resp in row.per_action_response.items():
                    if code == ActionCode.A00.value:
                        continue
                    action_totals[code] = action_totals.get(code, 0) + 1
                    if resp.would_recover:
                        action_success[code] = action_success.get(code, 0) + 1
                        recovering += 1
                    outcomes.append(1.0 if resp.would_recover else 0.0)
                recovering_counts.append(recovering)
                if outcomes:
                    mean = sum(outcomes) / len(outcomes)
                    var = sum((x - mean) ** 2 for x in outcomes) / len(outcomes)
                    variance_samples.append(var)

    avg_recovering = (
        sum(recovering_counts) / len(recovering_counts) if recovering_counts else 0.0
    )
    avg_var = (
        sum(variance_samples) / len(variance_samples) if variance_samples else 0.0
    )
    action_rates = {
        code: action_success.get(code, 0) / max(1, action_totals.get(code, 1))
        for code in sorted(action_totals.keys())
    }

    if avg_recovering >= 2.0 and avg_var >= 0.08:
        classification = "HIGH"
        rationale = f"avg_recovering_actions={avg_recovering:.2f}, variance={avg_var:.3f}"
    elif avg_recovering >= 1.2 or avg_var >= 0.04:
        classification = "MODERATE"
        rationale = f"avg_recovering_actions={avg_recovering:.2f}, variance={avg_var:.3f}"
    else:
        classification = "LOW"
        rationale = f"actions behave similarly avg_recovering={avg_recovering:.2f}"

    return ActionSensitivityReport(
        avg_recovering_actions_per_opp=avg_recovering,
        avg_action_outcome_variance=avg_var,
        action_recovery_rates=action_rates,
        classification=classification,
        rationale=rationale,
    )
