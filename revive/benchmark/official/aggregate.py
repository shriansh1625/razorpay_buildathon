"""Benchmark aggregation across seeds, profiles, and policies."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from revive.benchmark.official.metrics import PolicyRunMetrics, apply_m10_paired


@dataclass
class BenchmarkAggregate:
    per_run: list[PolicyRunMetrics] = field(default_factory=list)
    per_policy: dict[str, list[PolicyRunMetrics]] = field(default_factory=dict)
    per_profile: dict[str, list[PolicyRunMetrics]] = field(default_factory=dict)
    per_seed: dict[int, list[PolicyRunMetrics]] = field(default_factory=dict)
    revive_vs_b3: dict[str, Any] = field(default_factory=dict)

    def add(self, metrics: PolicyRunMetrics) -> None:
        self.per_run.append(metrics)
        self.per_policy.setdefault(metrics.policy_id, []).append(metrics)
        self.per_profile.setdefault(metrics.profile, []).append(metrics)
        self.per_seed.setdefault(metrics.seed, []).append(metrics)

    def finalize_m10(self) -> None:
        """Apply paired M-10 against B0 per seed/profile cell."""
        b0_lookup: dict[tuple[int, str], int] = {}
        for m in self.per_run:
            if m.policy_id == "B0":
                b0_lookup[(m.seed, m.profile)] = m.net_recovered_paise

        for m in self.per_run:
            b0_net = b0_lookup.get((m.seed, m.profile), 0)
            apply_m10_paired(m, b0_net)

        self._compute_revive_vs_b3()

    def _compute_revive_vs_b3(self) -> None:
        cells: dict[tuple[int, str], dict[str, PolicyRunMetrics]] = {}
        for m in self.per_run:
            key = (m.seed, m.profile)
            cells.setdefault(key, {})[m.policy_id] = m

        lifts: list[int] = []
        for cell_metrics in cells.values():
            revive = cell_metrics.get("REVIVE")
            b3 = cell_metrics.get("B3")
            if revive and b3 and revive.m10_incremental_net_paise is not None:
                lifts.append(
                    revive.m10_incremental_net_paise - (b3.m10_incremental_net_paise or 0)
                )

        if lifts:
            self.revive_vs_b3 = {
                "allocation_lift_m10_paise_mean": statistics.mean(lifts),
                "allocation_lift_m10_paise_median": statistics.median(lifts),
                "cells_compared": len(lifts),
                "label": "comparative outcome under benchmark environment (REVIVE M-10 − B3 M-10)",
            }

    def policy_summary(self, policy_id: str) -> dict[str, Any]:
        runs = self.per_policy.get(policy_id, [])
        if not runs:
            return {}
        m10_values = [r.m10_incremental_net_paise or 0 for r in runs]
        net_values = [r.net_recovered_paise for r in runs]
        return {
            "policy_id": policy_id,
            "run_count": len(runs),
            "M-10_mean_paise": statistics.mean(m10_values),
            "M-10_median_paise": statistics.median(m10_values),
            "M-10_min_paise": min(m10_values),
            "M-10_max_paise": max(m10_values),
            "net_recovered_mean_paise": statistics.mean(net_values),
            "seeds_where_negative_m10": sum(1 for v in m10_values if v < 0),
            "unauthorized_executions_total": sum(r.unauthorized_executions for r in runs),
            "execution_failures_total": sum(r.execution_failures for r in runs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "per_policy": {pid: self.policy_summary(pid) for pid in self.per_policy},
            "per_profile": {
                profile: {
                    "run_count": len(runs),
                    "M-10_mean_paise": statistics.mean(
                        [r.m10_incremental_net_paise or 0 for r in runs]
                    )
                    if runs
                    else 0,
                }
                for profile, runs in self.per_profile.items()
            },
            "revive_vs_b3": self.revive_vs_b3,
            "run_count": len(self.per_run),
        }
