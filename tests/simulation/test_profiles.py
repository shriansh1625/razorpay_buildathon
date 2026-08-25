"""Profile and configuration tests."""

from revive.simulation import GeneratorConfig, generate_dataset
from revive.simulation.distributions import compute_distributions
from revive.simulation.types import GenerationProfile


def test_profiles_differ_in_natural_recovery():
    scarce = generate_dataset(
        GeneratorConfig(seed=10, profile=GenerationProfile.SCARCE, opportunity_count=25)
    )
    high_nat = generate_dataset(
        GeneratorConfig(seed=10, profile=GenerationProfile.HIGH_NATURAL, opportunity_count=25)
    )
    scarce_rate = compute_distributions(scarce).natural_recovery_rate
    high_rate = compute_distributions(high_nat).natural_recovery_rate
    assert high_rate > scarce_rate


def test_config_hash_stable():
    config = GeneratorConfig(seed=99, profile=GenerationProfile.BALANCED)
    assert config.config_hash() == config.config_hash()


def test_all_profiles_generate():
    for profile in GenerationProfile:
        dataset = generate_dataset(
            GeneratorConfig(seed=1, profile=profile, opportunity_count=10, inject_signal_faults=False)
        )
        assert len(dataset.world.opportunities) == 10
