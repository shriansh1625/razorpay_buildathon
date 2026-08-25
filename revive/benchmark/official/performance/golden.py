"""Golden REVIVE cell fingerprints — M13.14 semantic regression."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.cells.store import metrics_checksum
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.metrics import compute_policy_metrics
from revive.benchmark.official.policies import BenchmarkPolicyId
from revive.benchmark.official.revive_pipeline import run_revive_cycle, new_revive_state
from revive.benchmark.official.world import clone_shared_world, generate_shared_world
from revive.config.policy_pack import official_sealed_policy_pack
from revive.simulation.types import GenerationProfile

GOLDEN_PATH = Path("tests/benchmark/golden/m13_14_seed2_balanced_revive.json")


@dataclass
class GoldenCellCapture:
    seed: int
    profile: str
    fingerprints: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "profile": self.profile,
            "fingerprints": self.fingerprints,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoldenCellCapture:
        return cls(
            seed=int(data["seed"]),
            profile=str(data["profile"]),
            fingerprints=dict(data.get("fingerprints", {})),
            metadata=dict(data.get("metadata", {})),
        )

    def save(self, path: Path = GOLDEN_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: Path = GOLDEN_PATH) -> GoldenCellCapture:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))


def capture_golden_cell(
    seed: int = 2,
    profile: str = "BALANCED",
    *,
    use_cycle_cache: bool = True,
) -> GoldenCellCapture:
    """Run full REVIVE cell and capture terminal metrics fingerprint."""
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen_config = generator_config_for_cell(config, seed, GenerationProfile(profile))
    bundle = generate_shared_world(gen_config)

    if use_cycle_cache:
        cloned = clone_shared_world(bundle)
        caps = benchmark_resource_capacities(profile_from_string(profile))
        state = new_revive_state(cloned, pack, caps)
        for idx, now_micros in enumerate(cloned.cycle_times_micros):
            run_revive_cycle(state, f"cyc_{idx:04d}", now_micros)
        from revive.benchmark.official.metrics import compute_policy_metrics

        metrics = compute_policy_metrics(
            BenchmarkPolicyId.REVIVE.value,
            cloned.seed,
            cloned.profile,
            tuple(state.measurements),
            tuple(state.executions),
            tuple(state.authorizations),
            incentive_budget_capacity_paise=caps.incentive_budget_paise,
            retry_capacity=caps.retry_slots,
            message_capacity=caps.message_capacity,
        )
    else:
        from revive.benchmark.official.policy_runner import run_policy_on_world

        metrics = run_policy_on_world(bundle, BenchmarkPolicyId.REVIVE, pack)

    metrics_dict = metrics.to_dict()
    cell_hash = metrics_checksum(metrics_dict)
    capture = GoldenCellCapture(
        seed=seed,
        profile=profile,
        fingerprints={"cell_result_hash": cell_hash},
        metadata={
            "cycle_count": len(bundle.cycle_times_micros),
            "intervention_count": metrics.intervention_count,
            "net_recovered_paise": metrics.net_recovered_paise,
            "use_cycle_cache": use_cycle_cache,
        },
    )
    return capture


def assert_golden_match(capture: GoldenCellCapture, reference: GoldenCellCapture | None = None) -> bool:
    ref = reference or GoldenCellCapture.load()
    return capture.fingerprints.get("cell_result_hash") == ref.fingerprints.get("cell_result_hash")
