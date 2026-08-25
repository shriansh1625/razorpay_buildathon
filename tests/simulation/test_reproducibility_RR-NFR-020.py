"""M2 generator reproducibility tests."""

from revive.simulation import GeneratorConfig, generate_dataset
from revive.simulation.types import GenerationProfile


def test_same_seed_same_dataset_hash():
    config = GeneratorConfig(seed=42, profile=GenerationProfile.BALANCED, opportunity_count=20)
    a = generate_dataset(config)
    b = generate_dataset(config)
    assert a.dataset_hash == b.dataset_hash
    assert len(a.world.opportunities) == len(b.world.opportunities)


def test_different_seeds_different_hash():
    a = generate_dataset(GeneratorConfig(seed=1, opportunity_count=15))
    b = generate_dataset(GeneratorConfig(seed=2, opportunity_count=15))
    assert a.dataset_hash != b.dataset_hash
