"""Falsification tests F-1 through F-6 — docs/20 §1.2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.benchmark.official.aggregate import BenchmarkAggregate


@dataclass
class FalsificationResult:
    test_id: str
    description: str
    expected_failure_mode: str
    triggered: bool
    actual_result: str
    degraded_safely: bool
    unauthorized_actions: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id,
            "description": self.description,
            "expected_failure_mode": self.expected_failure_mode,
            "triggered": self.triggered,
            "actual_result": self.actual_result,
            "degraded_safely": self.degraded_safely,
            "unauthorized_actions": self.unauthorized_actions,
        }


@dataclass
class FalsificationReport:
    results: list[FalsificationResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tests": [r.to_dict() for r in self.results],
            "any_triggered": any(r.triggered for r in self.results),
        }


def run_falsification_tests(aggregate: BenchmarkAggregate) -> FalsificationReport:
    report = FalsificationReport()

    balanced_runs = [
        m for m in aggregate.per_run
        if m.profile == "BALANCED" and m.policy_id == "REVIVE"
    ]
    revive_balanced_m10 = [
        m.m10_incremental_net_paise or 0 for m in balanced_runs
    ]
    best_baseline_m10 = _best_baseline_m10_balanced(aggregate)
    median_revive = _median(revive_balanced_m10) if revive_balanced_m10 else 0
    f1_triggered = median_revive <= best_baseline_m10
    report.results.append(
        FalsificationResult(
            test_id="F-1",
            description="REVIVE median paired M-10 ≤ best baseline in BALANCED",
            expected_failure_mode="REVIVE does not beat best baseline on primary metric",
            triggered=f1_triggered,
            actual_result=f"median_revive_m10={median_revive}, best_baseline_m10={best_baseline_m10}",
            degraded_safely=True,
            unauthorized_actions=sum(m.unauthorized_executions for m in balanced_runs),
        )
    )

    revive_runs = [m for m in aggregate.per_run if m.policy_id == "REVIVE"]
    best_contact_efficiency = _best_contact_efficiency(aggregate)
    revive_contact = _median_contact_per_m10(revive_runs)
    f2_triggered = revive_contact > best_contact_efficiency if revive_contact else False
    report.results.append(
        FalsificationResult(
            test_id="F-2",
            description="REVIVE contacts per unit recovered worse than best baseline",
            expected_failure_mode="More contacts per unit recovered than best baseline",
            triggered=f2_triggered,
            actual_result=f"revive_contacts_per_rupee={revive_contact}",
            degraded_safely=True,
            unauthorized_actions=sum(m.unauthorized_executions for m in revive_runs),
        )
    )

    f3_triggered = any(
        (m.m10_incremental_net_paise or 0) <= 0 and m.policy_id == "REVIVE"
        for m in aggregate.per_run
    )
    report.results.append(
        FalsificationResult(
            test_id="F-3",
            description="REVIVE net advantage disappears after costs",
            expected_failure_mode="Non-positive M-10 after costs",
            triggered=f3_triggered,
            actual_result="checked per-run M-10 sign",
            degraded_safely=True,
            unauthorized_actions=sum(m.unauthorized_executions for m in revive_runs),
        )
    )

    guardrail_fail = any(
        m.unauthorized_executions > 0
        or m.stopping_rule_violations > 0
        or m.policy_violations > 0
        for m in aggregate.per_run
    )
    report.results.append(
        FalsificationResult(
            test_id="F-4",
            description="Guardrail metrics fail (M-16, M-17, invariant)",
            expected_failure_mode="Non-zero guardrail violations",
            triggered=guardrail_fail,
            actual_result="aggregated guardrail scan",
            degraded_safely=not guardrail_fail,
            unauthorized_actions=sum(m.unauthorized_executions for m in aggregate.per_run),
        )
    )

    f5_triggered = any(
        m.policy_id == "REVIVE"
        and m.net_recovered_paise < _b0_net_for_cell(aggregate, m.seed, m.profile)
        for m in aggregate.per_run
    )
    report.results.append(
        FalsificationResult(
            test_id="F-5",
            description="REVIVE net below B0 in any profile",
            expected_failure_mode="REVIVE loses to natural recovery floor",
            triggered=f5_triggered,
            actual_result="per-cell net vs B0",
            degraded_safely=True,
            unauthorized_actions=sum(m.unauthorized_executions for m in revive_runs),
        )
    )

    report.results.append(
        FalsificationResult(
            test_id="F-6",
            description="Reproducibility — verified by separate reproduction command",
            expected_failure_mode="Byte/numeric mismatch on re-run",
            triggered=False,
            actual_result="deferred to reproduce_benchmark()",
            degraded_safely=True,
            unauthorized_actions=0,
        )
    )

    return report


def _median(values: list[int | float]) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    mid = len(sorted_vals) // 2
    if len(sorted_vals) % 2:
        return float(sorted_vals[mid])
    return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0


def _best_baseline_m10_balanced(aggregate: BenchmarkAggregate) -> float:
    baseline_ids = ("B0", "B1", "B2", "B3")
    best = 0.0
    for pid in baseline_ids:
        runs = [
            m for m in aggregate.per_run
            if m.policy_id == pid and m.profile == "BALANCED"
        ]
        if runs:
            med = _median([m.m10_incremental_net_paise or 0 for m in runs])
            best = max(best, med)
    return best


def _best_contact_efficiency(aggregate: BenchmarkAggregate) -> float:
    efficiencies: list[float] = []
    for m in aggregate.per_run:
        if m.policy_id == "REVIVE":
            continue
        m10_rupees = (m.m10_incremental_net_paise or 0) / 100.0
        if m10_rupees > 0 and m.contact_count > 0:
            efficiencies.append(m.contact_count / m10_rupees)
    return max(efficiencies) if efficiencies else 0.0


def _median_contact_per_m10(runs: list) -> float:
    ratios: list[float] = []
    for m in runs:
        m10_rupees = (m.m10_incremental_net_paise or 0) / 100.0
        if m10_rupees > 0:
            ratios.append(m.contact_count / m10_rupees)
    return _median(ratios) if ratios else 0.0


def _b0_net_for_cell(aggregate: BenchmarkAggregate, seed: int, profile: str) -> int:
    for m in aggregate.per_run:
        if m.policy_id == "B0" and m.seed == seed and m.profile == profile:
            return m.net_recovered_paise
    return 0
