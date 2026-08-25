"""Dataset replay — regenerate from configuration + seed."""

from __future__ import annotations

from revive.simulation.config import GeneratorConfig
from revive.simulation.generator import GeneratedDataset, generate_dataset
from revive.simulation.validation import assert_dataset_valid


def replay_dataset(config: GeneratorConfig) -> GeneratedDataset:
    """Recreate dataset from frozen configuration."""
    dataset = generate_dataset(config)
    assert_dataset_valid(dataset)
    return dataset
