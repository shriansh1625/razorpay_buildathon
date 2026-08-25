"""M13.10 official benchmark seal — manifest without execution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from revive.benchmark.official.config import official_benchmark_config
from revive.benchmark.official.freeze import check_freeze_prerequisites
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.config.policy_pack import official_sealed_policy_pack


@dataclass(frozen=True, slots=True)
class SealResult:
    config_hash: str
    freeze_complete: bool
    manifest_path: Path
    blocked_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_hash": self.config_hash,
            "freeze_complete": self.freeze_complete,
            "manifest_path": str(self.manifest_path),
            "blocked_reasons": list(self.blocked_reasons),
        }


def build_freeze_manifest(
    config,
    config_hash: str,
) -> dict[str, Any]:
    gen = config.generator_config
    return {
        "benchmark_version": config.benchmark_version,
        "benchmark_id": config.benchmark_id,
        "config_hash": config_hash,
        "PolicyPack_version": config.policy_pack_version,
        "PolicyPack_hash": config.policy_pack_hash,
        "PolicyPack_status": config.policy_pack_status,
        "generator_version": config.generator_version,
        "generator_config_hash": gen.config_hash(),
        "predictor_version": config.predictor_version,
        "allocator_version": config.allocator_version,
        "approver_version": config.approver_model_version,
        "B1_version": config.b1_schedule_version,
        "metric_version": config.metric_version,
        "horizon_days": config.simulation_horizon_days,
        "opportunity_count": gen.opportunity_count,
        "customer_count": gen.customer_count,
        "cycle_length_minutes": config.cycle_length_minutes,
        "profiles": [p.value for p in config.profile_set],
        "seed_set": list(config.seed_set),
        "epsilon_paise": config.epsilon_paise,
        "llm_mode": config.llm_mode,
        "allocator_mode": config.allocator_mode,
        "policy_set": list(config.policy_set),
        "code_revision": config.code_revision,
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "contains_results": False,
    }


def seal_official_benchmark(
    output_dir: Path | None = None,
) -> SealResult:
    """
    Write freeze manifest and verify prerequisites.

    Does NOT execute the official benchmark.
    """
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    config_hash = official_benchmark_config_hash(config)
    freeze = check_freeze_prerequisites(config, policy_pack=pack)

    manifest = build_freeze_manifest(config, config_hash)
    root = output_dir or Path("artefacts/benchmark/official")
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "freeze-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (root / "config_hash.txt").write_text(config_hash, encoding="utf-8")

    return SealResult(
        config_hash=config_hash,
        freeze_complete=freeze.complete,
        manifest_path=manifest_path,
        blocked_reasons=freeze.blocked_reasons,
    )
