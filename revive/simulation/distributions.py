"""Distribution summaries for reviewer disclosure — docs/19 §9."""

from __future__ import annotations

import json
from dataclasses import dataclass

from revive.simulation.generator import GeneratedDataset


@dataclass(frozen=True, slots=True)
class DistributionSummary:
    natural_recovery_rate: float
    risk_class_counts: dict[str, int]
    value_at_risk_median_paise: int
    profiles: dict[str, float]

    def to_dict(self) -> dict:
        return {
            "natural_recovery_rate": self.natural_recovery_rate,
            "risk_class_counts": self.risk_class_counts,
            "value_at_risk_median_paise": self.value_at_risk_median_paise,
            "profiles": self.profiles,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def compute_distributions(dataset: GeneratedDataset) -> DistributionSummary:
    rows = dataset.oracle_partition.rows.values()
    natural_count = sum(1 for r in rows if r.recovers_naturally)
    natural_rate = natural_count / max(1, len(rows))

    risk_counts: dict[str, int] = {}
    for opp in dataset.world.opportunities:
        key = opp.risk_class.value
        risk_counts[key] = risk_counts.get(key, 0) + 1

    values = sorted(o.value_at_risk_paise for o in dataset.world.opportunities)
    median = values[len(values) // 2] if values else 0

    action_success: dict[str, float] = {}
    for code in dataset.oracle_partition.action_codes_in_partition():
        if code == "A00":
            continue
        successes = 0
        total = 0
        for row in rows:
            resp = row.per_action_response.get(code)
            if resp:
                total += 1
                if resp.would_recover:
                    successes += 1
        if total:
            action_success[code] = successes / total

    return DistributionSummary(
        natural_recovery_rate=natural_rate,
        risk_class_counts=risk_counts,
        value_at_risk_median_paise=median,
        profiles={"per_action_success_rate": action_success},
    )
