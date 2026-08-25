"""Profile parameter overlays — docs/19 §2.3."""

from __future__ import annotations

from dataclasses import dataclass

from revive.simulation.types import GenerationProfile


@dataclass(frozen=True, slots=True)
class ProfileParameters:
    """Meaningful profile differences beyond dataset size."""

    natural_recovery_multiplier: float
    capacity_scarcity_factor: float
    adversarial_injection: bool
    degradation_intensity: float
    value_recoverability_correlation: float
    high_value_natural_concentration: float
    description: str


PROFILE_PARAMETERS: dict[GenerationProfile, ProfileParameters] = {
    GenerationProfile.BALANCED: ProfileParameters(
        natural_recovery_multiplier=1.0,
        capacity_scarcity_factor=1.0,
        adversarial_injection=False,
        degradation_intensity=1.0,
        value_recoverability_correlation=-0.3,
        high_value_natural_concentration=0.4,
        description="Mixed classes, moderate scarcity — primary benchmark profile.",
    ),
    GenerationProfile.HIGH_NATURAL: ProfileParameters(
        natural_recovery_multiplier=2.2,
        capacity_scarcity_factor=1.0,
        adversarial_injection=False,
        degradation_intensity=0.8,
        value_recoverability_correlation=-0.5,
        high_value_natural_concentration=0.75,
        description="Many opportunities self-recover; punishes over-contacting.",
    ),
    GenerationProfile.SCARCE: ProfileParameters(
        natural_recovery_multiplier=0.85,
        capacity_scarcity_factor=2.5,
        adversarial_injection=False,
        degradation_intensity=1.0,
        value_recoverability_correlation=-0.45,
        high_value_natural_concentration=0.35,
        description="Severe budget/capacity limits; stresses allocation.",
    ),
    GenerationProfile.ABUNDANT: ProfileParameters(
        natural_recovery_multiplier=1.0,
        capacity_scarcity_factor=0.2,
        adversarial_injection=False,
        degradation_intensity=0.9,
        value_recoverability_correlation=-0.15,
        high_value_natural_concentration=0.3,
        description="Near-unlimited capacity; expected to shrink allocator advantage.",
    ),
    GenerationProfile.HOSTILE: ProfileParameters(
        natural_recovery_multiplier=0.9,
        capacity_scarcity_factor=1.2,
        adversarial_injection=True,
        degradation_intensity=1.1,
        value_recoverability_correlation=-0.35,
        high_value_natural_concentration=0.4,
        description="Heavy adversarial injection; tests guardrails and stopping.",
    ),
    GenerationProfile.DEGRADED: ProfileParameters(
        natural_recovery_multiplier=0.95,
        capacity_scarcity_factor=1.0,
        adversarial_injection=False,
        degradation_intensity=2.5,
        value_recoverability_correlation=-0.3,
        high_value_natural_concentration=0.4,
        description="Provider outage windows; timing-sensitive recovery.",
    ),
}


def profile_parameters(profile: GenerationProfile) -> ProfileParameters:
    return PROFILE_PARAMETERS[profile]
