"""
Benchmark resource capacities — profile scarcity wiring (M13.6).

Maps documented `capacity_scarcity_factor` from generation profiles to
ResourceCapacities and baseline environment constraints.

Policy-neutral: capacities depend on profile/environment only, never on
strategy identity.
"""

from __future__ import annotations

import hashlib
import json

from revive.allocation.models import ResourceCapacities
from revive.benchmark.config import BaselineEnvironmentConfig, DEFAULT_ACTION_COSTS_PAISE
from revive.decision.hashing import capacities_digest
from revive.simulation.profiles import profile_parameters
from revive.simulation.types import GenerationProfile

# Documented baseline capacities before profile overlay (BF-4, allocation defaults).
_BASE_CAPACITIES = ResourceCapacities()


def benchmark_resource_capacities(
    profile: GenerationProfile,
    *,
    base: ResourceCapacities | None = None,
) -> ResourceCapacities:
    """
    Apply profile `capacity_scarcity_factor` to cycle resource limits.

    Higher factor → tighter capacity (SCARCE). Lower factor → abundant capacity.
    Semantics: capacity = base / factor (docs/19 profile overlays, M13.5 diagnostic).
    """
    ref = base or _BASE_CAPACITIES
    factor = profile_parameters(profile).capacity_scarcity_factor
    if factor <= 0:
        factor = 1.0

    return ResourceCapacities(
        retry_slots=max(1, int(ref.retry_slots / factor)),
        message_capacity=max(1, int(ref.message_capacity / factor)),
        voice_minutes=max(1, int(ref.voice_minutes / factor)),
        human_review_slots=max(1, int(ref.human_review_slots / factor)),
        incentive_budget_paise=max(1000, int(ref.incentive_budget_paise / factor)),
        contact_allowance_per_customer=ref.contact_allowance_per_customer,
    )


def benchmark_capacities_digest(profile: GenerationProfile) -> str:
    """Deterministic digest for profile-specific benchmark capacities."""
    return capacities_digest(benchmark_resource_capacities(profile))


def baseline_environment_for_profile(profile: GenerationProfile) -> BaselineEnvironmentConfig:
    """Baseline BF-4 constraints aligned with profile-adjusted capacities."""
    caps = benchmark_resource_capacities(profile)
    return BaselineEnvironmentConfig(
        contact_allowance_per_customer=caps.contact_allowance_per_customer,
        retry_slots_per_cycle=caps.retry_slots,
        message_capacity_per_cycle=caps.message_capacity,
        action_costs_paise=dict(DEFAULT_ACTION_COSTS_PAISE),
    )


def profile_from_string(profile: str) -> GenerationProfile:
    return GenerationProfile(profile)
