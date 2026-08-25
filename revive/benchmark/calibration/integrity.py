"""Benchmark integrity verification for calibration gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.benchmark.official.world import generate_shared_world
from revive.benchmark.calibration.config import calibration_config
from revive.simulation.types import GenerationProfile


@dataclass
class IntegrityReport:
    oracle_isolation: bool = False
    same_world_across_policies: bool = False
    dataset_hash_stable: bool = False
    checks: dict[str, bool] = field(default_factory=dict)
    classification: str = "UNKNOWN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "classification": self.classification,
            "checks": self.checks,
            "oracle_isolation": self.oracle_isolation,
            "same_world_across_policies": self.same_world_across_policies,
            "dataset_hash_stable": self.dataset_hash_stable,
        }


def run_integrity_checks() -> IntegrityReport:
    checks: dict[str, bool] = {}

    try:
        from revive.integrity import (
            assert_baseline_modules_do_not_import_oracle,
            assert_decision_path_does_not_import_oracle,
        )

        assert_decision_path_does_not_import_oracle()
        assert_baseline_modules_do_not_import_oracle()
        checks["oracle_isolation_static"] = True
    except AssertionError:
        checks["oracle_isolation_static"] = False

    cfg = calibration_config(1, GenerationProfile.BALANCED)
    w1 = generate_shared_world(cfg)
    w2 = generate_shared_world(cfg)
    checks["dataset_hash_identical"] = w1.dataset_hash == w2.dataset_hash
    checks["world_entity_counts_identical"] = (
        w1.world.entity_counts() == w2.world.entity_counts()
    )

    # Policy runs clone world — oracle partition object identity can differ but hash same
    cloned = __import__(
        "revive.benchmark.official.world",
        fromlist=["clone_shared_world"],
    ).clone_shared_world(w1)
    checks["clone_preserves_opportunity_count"] = (
        len(cloned.world.opportunities) == len(w1.world.opportunities)
    )

    oracle_ok = checks.get("oracle_isolation_static", False)
    world_ok = checks.get("dataset_hash_identical", False) and checks.get(
        "clone_preserves_opportunity_count", False
    )

    classification = "READY" if oracle_ok and world_ok else "BLOCKED"

    return IntegrityReport(
        oracle_isolation=oracle_ok,
        same_world_across_policies=world_ok,
        dataset_hash_stable=checks.get("dataset_hash_identical", False),
        checks=checks,
        classification=classification,
    )
