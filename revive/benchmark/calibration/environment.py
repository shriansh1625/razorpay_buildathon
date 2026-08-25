"""Environment diagnostics — oracle-side, no policy superiority claims."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.simulation.generator import GeneratedDataset, generate_dataset


@dataclass
class EnvironmentCellDiagnostics:
    seed: int
    profile: str
    opportunity_count: int
    gross_value_at_risk_paise: int
    addressable_count: int
    natural_recovery_count: int
    natural_recovery_rate: float
    intervention_sensitive_count: int
    non_recoverable_count: int
    partial_recovery_candidates: int
    risk_class_counts: dict[str, int] = field(default_factory=dict)
    avg_recovering_actions_per_opp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "profile": self.profile,
            "opportunity_count": self.opportunity_count,
            "gross_value_at_risk_paise": self.gross_value_at_risk_paise,
            "addressable_count": self.addressable_count,
            "natural_recovery_count": self.natural_recovery_count,
            "natural_recovery_rate": self.natural_recovery_rate,
            "intervention_sensitive_count": self.intervention_sensitive_count,
            "non_recoverable_count": self.non_recoverable_count,
            "partial_recovery_candidates": self.partial_recovery_candidates,
            "risk_class_counts": self.risk_class_counts,
            "avg_recovering_actions_per_opp": self.avg_recovering_actions_per_opp,
        }


def _intervention_sensitive(row: Any) -> bool:
    action_recovers = any(
        code != "A00" and resp.would_recover
        for code, resp in row.per_action_response.items()
    )
    if not action_recovers:
        return False
    if not row.recovers_naturally:
        return True
    # Natural recovers but action may still matter for timing/attribution diagnostics.
    return True


def _recovering_action_count(row: Any) -> int:
    return sum(
        1
        for code, resp in row.per_action_response.items()
        if code != "A00" and resp.would_recover
    )


def analyze_environment(dataset: GeneratedDataset) -> EnvironmentCellDiagnostics:
    world = dataset.world
    partition = dataset.oracle_partition
    config = dataset.config

    risk_counts: dict[str, int] = {}
    natural_count = 0
    intervention_sensitive = 0
    non_recoverable = 0
    partial_candidates = 0
    recovering_action_counts: list[int] = []
    gross_var = 0
    addressable = 0

    for opp in world.opportunities:
        gross_var += opp.value_at_risk_paise
        if opp.addressable:
            addressable += 1
        risk_counts[opp.risk_class.value] = risk_counts.get(opp.risk_class.value, 0) + 1

        row = partition.get_row(opp.opportunity_id)
        if row is None:
            continue

        if row.recovers_naturally:
            natural_count += 1
        recovering = _recovering_action_count(row)
        recovering_action_counts.append(recovering)

        if _intervention_sensitive(row):
            intervention_sensitive += 1

        any_recovery = row.recovers_naturally or recovering > 0
        if not any_recovery:
            non_recoverable += 1

        if recovering > 0 and row.natural_amount_paise < opp.value_at_risk_paise:
            partial_candidates += 1

    opp_count = len(world.opportunities)
    natural_rate = natural_count / opp_count if opp_count else 0.0
    avg_recovering = (
        sum(recovering_action_counts) / len(recovering_action_counts)
        if recovering_action_counts
        else 0.0
    )

    return EnvironmentCellDiagnostics(
        seed=config.seed,
        profile=config.profile.value,
        opportunity_count=opp_count,
        gross_value_at_risk_paise=gross_var,
        addressable_count=addressable,
        natural_recovery_count=natural_count,
        natural_recovery_rate=natural_rate,
        intervention_sensitive_count=intervention_sensitive,
        non_recoverable_count=non_recoverable,
        partial_recovery_candidates=partial_candidates,
        risk_class_counts=risk_counts,
        avg_recovering_actions_per_opp=avg_recovering,
    )


def run_environment_diagnostics(
    seeds: tuple[int, ...],
    profiles: tuple,
    config_factory=None,
) -> list[EnvironmentCellDiagnostics]:
    from revive.simulation.types import GenerationProfile
    from revive.benchmark.calibration.config import calibration_config

    factory = config_factory or calibration_config
    results: list[EnvironmentCellDiagnostics] = []
    for seed in seeds:
        for profile in profiles:
            if not isinstance(profile, GenerationProfile):
                profile = GenerationProfile(profile)
            dataset = generate_dataset(factory(seed, profile))
            results.append(analyze_environment(dataset))
    return results
