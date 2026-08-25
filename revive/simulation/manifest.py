"""Dataset manifest — observable metadata only."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone

from revive.db.schema import SCHEMA_VERSION
from revive.simulation.config import GENERATOR_VERSION, GeneratorConfig
from revive.simulation.world import SyntheticWorld


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_id: str
    seed: int
    generator_version: str
    schema_version: int
    generation_profile: str
    simulation_window_days: int
    entity_counts: dict[str, int]
    config_hash: str
    dataset_hash: str
    created_at: str
    adversarial_case_ids: tuple[str, ...]
    disclosure: str = (
        "SYNTHETIC DATA — UNVERIFIED fidelity. No benchmark claims from development data."
    )

    def to_dict(self) -> dict:
        return {
            "dataset_id": self.dataset_id,
            "seed": self.seed,
            "generator_version": self.generator_version,
            "schema_version": self.schema_version,
            "generation_profile": self.generation_profile,
            "simulation_window_days": self.simulation_window_days,
            "entity_counts": self.entity_counts,
            "config_hash": self.config_hash,
            "dataset_hash": self.dataset_hash,
            "created_at": self.created_at,
            "adversarial_case_ids": list(self.adversarial_case_ids),
            "disclosure": self.disclosure,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)


def build_manifest(
    config: GeneratorConfig,
    world: SyntheticWorld,
    dataset_hash: str,
) -> DatasetManifest:
    return DatasetManifest(
        dataset_id=f"ds_{config.seed}_{config.profile.value}",
        seed=config.seed,
        generator_version=GENERATOR_VERSION,
        schema_version=SCHEMA_VERSION,
        generation_profile=config.profile.value,
        simulation_window_days=config.simulation_window_days,
        entity_counts=world.entity_counts(),
        config_hash=config.config_hash(),
        dataset_hash=dataset_hash,
        created_at=datetime.now(timezone.utc).isoformat(),
        adversarial_case_ids=tuple(world.adversarial_case_ids),
    )
