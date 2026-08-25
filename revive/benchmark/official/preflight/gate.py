"""M13.19 preflight execution gate — not benchmark evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.benchmark.official.aggregate import BenchmarkAggregate

PREFLIGHT_LABEL = "PREFLIGHT_ONLY — NOT BENCHMARK EVIDENCE"


@dataclass(frozen=True, slots=True)
class PreflightGateResult:
    passed: bool
    label: str = PREFLIGHT_LABEL
    cells_expected: int = 30
    cells_evaluated: int = 0
    failures: tuple[str, ...] = ()
    profile_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "label": self.label,
            "cells_expected": self.cells_expected,
            "cells_evaluated": self.cells_evaluated,
            "failures": list(self.failures),
            "profile_summary": self.profile_summary,
        }


def evaluate_preflight_gate(aggregate: BenchmarkAggregate) -> PreflightGateResult:
    """Verify execution-path reachability across all six profiles (seed=1)."""
    failures: list[str] = []
    profile_summary: dict[str, Any] = {}

    runs_by_key = {(m.seed, m.profile, m.policy_id): m for m in aggregate.per_run}
    profiles = sorted({m.profile for m in aggregate.per_run})
    policies = ("B0", "B1", "B2", "B3", "REVIVE")

    if len(aggregate.per_run) != 30:
        failures.append(f"expected 30 cells, got {len(aggregate.per_run)}")

    for profile in profiles:
        row: dict[str, Any] = {}
        for policy in policies:
            metric = runs_by_key.get((1, profile, policy))
            if metric is None:
                failures.append(f"missing cell seed=1 profile={profile} policy={policy}")
                continue
            row[policy] = {
                "intervention_count": metric.intervention_count,
                "contact_count": metric.contact_count,
                "net_recovered_paise": metric.net_recovered_paise,
                "run_valid": metric.run_valid,
            }
            if not metric.run_valid:
                failures.append(f"{profile}/{policy}: run_valid=false")
            if policy == "B0":
                if metric.intervention_count != 0:
                    failures.append(
                        f"{profile}/B0: expected intervention_count=0, got {metric.intervention_count}"
                    )
            else:
                if metric.intervention_count == 0:
                    failures.append(
                        f"{profile}/{policy}: expected intervention_count>0, got 0"
                    )
        profile_summary[profile] = row

    return PreflightGateResult(
        passed=len(failures) == 0,
        cells_evaluated=len(aggregate.per_run),
        failures=tuple(failures),
        profile_summary=profile_summary,
    )
