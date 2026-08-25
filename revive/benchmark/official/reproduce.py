"""Benchmark reproduction check — M13 §33, F-6."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from revive.benchmark.official.runner import execute_benchmark
from revive.benchmark.official.config import BenchmarkMode, OfficialBenchmarkConfig


@dataclass(frozen=True, slots=True)
class ReproductionResult:
    identical: bool
    first_hash: str
    second_hash: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "identical": self.identical,
            "first_aggregate_fingerprint": self.first_hash,
            "second_aggregate_fingerprint": self.second_hash,
            "details": self.details,
        }


def _aggregate_fingerprint(result) -> str:
    import hashlib
    import json

    payload = result.aggregate.to_dict()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def reproduce_benchmark(
    config: OfficialBenchmarkConfig | None = None,
    *,
    mode: BenchmarkMode = BenchmarkMode.DEVELOPMENT,
) -> ReproductionResult:
    """Run benchmark twice and compare aggregate fingerprints."""
    r1 = execute_benchmark(mode=mode, output_dir=None, config=config)
    r2 = execute_benchmark(mode=mode, output_dir=None, config=config)
    h1 = _aggregate_fingerprint(r1)
    h2 = _aggregate_fingerprint(r2)
    return ReproductionResult(
        identical=h1 == h2 and not r1.blocked,
        first_hash=h1,
        second_hash=h2,
        details={
            "blocked": r1.blocked,
            "run_count_first": len(r1.aggregate.per_run),
            "run_count_second": len(r2.aggregate.per_run),
        },
    )
