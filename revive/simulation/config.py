"""Centralised generator configuration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from revive.simulation.types import GenerationProfile

GENERATOR_VERSION = "0.2.0-m2"


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    """All tunable generator parameters — development defaults, not benchmark-frozen."""

    seed: int
    profile: GenerationProfile = GenerationProfile.BALANCED
    merchant_count: int = 1
    customer_count: int = 40
    opportunity_count: int = 80
    simulation_window_days: int = 30
    cycle_interval_minutes: int = 15
    opportunity_rate: float = 0.35
    failure_mix_payment: float = 0.35
    failure_mix_checkout: float = 0.20
    failure_mix_subscription: float = 0.20
    failure_mix_receivable: float = 0.20
    failure_mix_mandate: float = 0.05
    abandonment_rate: float = 0.25
    subscription_rate: float = 0.30
    receivable_rate: float = 0.25
    degradation_frequency: float = 0.15
    natural_recovery_horizon_minutes: int = 24 * 60
    default_outcome_horizon_minutes: int = 48 * 60
    inject_signal_faults: bool = True
    inject_adversarial_cases: bool = False
    privacy_canary_count: int = 3
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.seed < 0:
            raise ValueError("seed must be non-negative")
        if self.customer_count < 1:
            raise ValueError("customer_count must be >= 1")
        if self.opportunity_count < 1:
            raise ValueError("opportunity_count must be >= 1")

    def config_hash(self) -> str:
        payload = {
            "generator_version": GENERATOR_VERSION,
            "seed": self.seed,
            "profile": self.profile.value,
            "merchant_count": self.merchant_count,
            "customer_count": self.customer_count,
            "opportunity_count": self.opportunity_count,
            "simulation_window_days": self.simulation_window_days,
            "cycle_interval_minutes": self.cycle_interval_minutes,
            "opportunity_rate": self.opportunity_rate,
            "failure_mix": {
                "payment": self.failure_mix_payment,
                "checkout": self.failure_mix_checkout,
                "subscription": self.failure_mix_subscription,
                "receivable": self.failure_mix_receivable,
                "mandate": self.failure_mix_mandate,
            },
            "abandonment_rate": self.abandonment_rate,
            "subscription_rate": self.subscription_rate,
            "receivable_rate": self.receivable_rate,
            "degradation_frequency": self.degradation_frequency,
            "natural_recovery_horizon_minutes": self.natural_recovery_horizon_minutes,
            "default_outcome_horizon_minutes": self.default_outcome_horizon_minutes,
            "inject_signal_faults": self.inject_signal_faults,
            "inject_adversarial_cases": self.inject_adversarial_cases,
            "privacy_canary_count": self.privacy_canary_count,
            "metadata": self.metadata,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()
