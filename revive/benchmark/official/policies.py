"""Benchmark policy identifiers — M13 §14–15."""

from __future__ import annotations

from enum import Enum

from revive.benchmark.types import BaselinePolicyId


class BenchmarkPolicyId(str, Enum):
    B0 = "B0"
    B1 = "B1"
    B2 = "B2"
    B3 = "B3"
    REVIVE = "REVIVE"


ALL_BENCHMARK_POLICIES: tuple[BenchmarkPolicyId, ...] = (
    BenchmarkPolicyId.B0,
    BenchmarkPolicyId.B1,
    BenchmarkPolicyId.B2,
    BenchmarkPolicyId.B3,
    BenchmarkPolicyId.REVIVE,
)


def to_baseline_id(policy: BenchmarkPolicyId) -> BaselinePolicyId | None:
    if policy == BenchmarkPolicyId.REVIVE:
        return None
    return BaselinePolicyId(policy.value)
