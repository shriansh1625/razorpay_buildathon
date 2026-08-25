"""M13.5 calibration configuration — development scale, not official."""

from __future__ import annotations

from revive.simulation.config import GeneratorConfig
from revive.simulation.types import GenerationProfile

CALIBRATION_VERSION = "0.13.5-m13.5"
M13_6_VERSION = "0.13.6-m13.6"
CALIBRATION_SEEDS: tuple[int, ...] = (1, 2, 3, 4, 5)
M13_6_OFFICIAL_SCALE_SEEDS: tuple[int, ...] = (1, 2, 3)
CALIBRATION_PROFILES: tuple[GenerationProfile, ...] = tuple(GenerationProfile)


def calibration_config(
    seed: int,
    profile: GenerationProfile,
) -> GeneratorConfig:
    """Medium development scale for discriminative diagnostics."""
    return GeneratorConfig(
        seed=seed,
        profile=profile,
        merchant_count=1,
        customer_count=25,
        opportunity_count=40,
        simulation_window_days=21,
        cycle_interval_minutes=15,
        inject_signal_faults=True,
        inject_adversarial_cases=False,
        privacy_canary_count=2,
    )


def tiny_reference_config(
    seed: int = 1,
    profile: GenerationProfile = GenerationProfile.BALANCED,
) -> GeneratorConfig:
    """M13 tiny config for zero-result root-cause comparison."""
    from revive.simulation.fixtures import tiny_config

    return tiny_config(seed=seed, profile=profile)


def official_scale_config(
    seed: int,
    profile: GenerationProfile,
    *,
    opportunity_count: int = 500,
    customer_count: int = 100,
) -> GeneratorConfig:
    """Documented official-scale proposal — ADR-012 not frozen."""
    return GeneratorConfig(
        seed=seed,
        profile=profile,
        merchant_count=1,
        customer_count=customer_count,
        opportunity_count=opportunity_count,
        simulation_window_days=30,
        cycle_interval_minutes=15,
        inject_signal_faults=True,
        inject_adversarial_cases=False,
        privacy_canary_count=3,
    )


def scale_sensitivity_config(
    seed: int,
    profile: GenerationProfile,
    opportunity_count: int,
) -> GeneratorConfig:
    """Generator scale sweep for contention analysis."""
    customer_count = max(20, opportunity_count // 5)
    return GeneratorConfig(
        seed=seed,
        profile=profile,
        merchant_count=1,
        customer_count=customer_count,
        opportunity_count=opportunity_count,
        simulation_window_days=21,
        cycle_interval_minutes=15,
        inject_signal_faults=True,
        inject_adversarial_cases=False,
        privacy_canary_count=2,
    )
