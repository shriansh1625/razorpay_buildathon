"""Benchmark integrity validation — M13 §44–45."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.benchmark.official.aggregate import BenchmarkAggregate
from revive.benchmark.official.config import OfficialBenchmarkConfig
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.benchmark.official.metrics import PolicyRunMetrics
from revive.benchmark.official.policies import ALL_BENCHMARK_POLICIES


@dataclass
class ValidationResult:
    valid: bool
    status: str
    reasons: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "valid": self.valid,
            "reasons": self.reasons,
            "checks": self.checks,
        }


def validate_benchmark_result(
    config: OfficialBenchmarkConfig,
    config_hash: str,
    aggregate: BenchmarkAggregate,
    expected_runs: int,
) -> ValidationResult:
    reasons: list[str] = []
    checks: dict[str, bool] = {}

    expected_hash = official_benchmark_config_hash(config)
    checks["configuration_hash_match"] = config_hash == expected_hash
    if not checks["configuration_hash_match"]:
        reasons.append("configuration hash mismatch")

    checks["all_policies_present"] = all(
        pid.value in aggregate.per_policy for pid in ALL_BENCHMARK_POLICIES
    )
    if not checks["all_policies_present"]:
        reasons.append("missing policy in results")

    checks["all_profiles_present"] = all(
        p.value in aggregate.per_profile for p in config.profile_set
    )
    if not checks["all_profiles_present"]:
        reasons.append("missing profile in results")

    checks["run_count_complete"] = len(aggregate.per_run) == expected_runs
    if not checks["run_count_complete"]:
        reasons.append(
            f"expected {expected_runs} runs, got {len(aggregate.per_run)}"
        )

    checks["no_duplicate_runs"] = _no_duplicate_runs(aggregate.per_run)
    if not checks["no_duplicate_runs"]:
        reasons.append("duplicate seed/profile/policy runs detected")

    checks["oracle_isolation"] = _oracle_isolation_ok()
    if not checks["oracle_isolation"]:
        reasons.append("oracle isolation check failed")

    invalid_runs = [m for m in aggregate.per_run if not m.run_valid]
    checks["no_invalid_policy_execution"] = len(invalid_runs) == 0
    if invalid_runs:
        reasons.append(f"{len(invalid_runs)} runs marked invalid")

    valid = all(checks.values()) and not reasons
    status = "BENCHMARK_VALID" if valid else "BENCHMARK_INVALID"
    return ValidationResult(valid=valid, status=status, reasons=reasons, checks=checks)


def _no_duplicate_runs(runs: list[PolicyRunMetrics]) -> bool:
    seen: set[tuple[str, int, str]] = set()
    for m in runs:
        key = (m.policy_id, m.seed, m.profile)
        if key in seen:
            return False
        seen.add(key)
    return True


def _oracle_isolation_ok() -> bool:
    try:
        from revive.integrity import (
            assert_baseline_modules_do_not_import_oracle,
            assert_decision_path_does_not_import_oracle,
        )

        assert_decision_path_does_not_import_oracle()
        assert_baseline_modules_do_not_import_oracle()
        return True
    except AssertionError:
        return False
