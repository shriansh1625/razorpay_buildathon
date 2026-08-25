"""Profile-specific benchmark capacity tests — M13.6."""

from revive.benchmark.capacities import (
    benchmark_capacities_digest,
    benchmark_resource_capacities,
    baseline_environment_for_profile,
)
from revive.simulation.types import GenerationProfile


def test_scarce_vs_abundant_different_capacities():
    scarce = benchmark_resource_capacities(GenerationProfile.SCARCE)
    abundant = benchmark_resource_capacities(GenerationProfile.ABUNDANT)
    assert scarce.retry_slots < abundant.retry_slots
    assert scarce.message_capacity < abundant.message_capacity
    assert scarce.incentive_budget_paise < abundant.incentive_budget_paise
    assert scarce.voice_minutes < abundant.voice_minutes
    assert scarce.human_review_slots < abundant.human_review_slots


def test_same_profile_same_seed_reproduces_capacities():
    a = benchmark_resource_capacities(GenerationProfile.BALANCED)
    b = benchmark_resource_capacities(GenerationProfile.BALANCED)
    assert a.retry_slots == b.retry_slots
    assert benchmark_capacities_digest(GenerationProfile.BALANCED) == (
        benchmark_capacities_digest(GenerationProfile.BALANCED)
    )


def test_capacity_digest_changes_with_profile():
    balanced = benchmark_capacities_digest(GenerationProfile.BALANCED)
    scarce = benchmark_capacities_digest(GenerationProfile.SCARCE)
    abundant = benchmark_capacities_digest(GenerationProfile.ABUNDANT)
    assert balanced != scarce
    assert balanced != abundant
    assert scarce != abundant


def test_baseline_environment_matches_capacities():
    profile = GenerationProfile.SCARCE
    caps = benchmark_resource_capacities(profile)
    env = baseline_environment_for_profile(profile)
    assert env.retry_slots_per_cycle == caps.retry_slots
    assert env.message_capacity_per_cycle == caps.message_capacity
    assert env.contact_allowance_per_customer == caps.contact_allowance_per_customer


def test_capacities_policy_neutral_module():
    """Capacity module has no policy identity imports."""
    import inspect
    import revive.benchmark.capacities as mod

    source = inspect.getsource(mod)
    for policy in ("B0", "B1", "B2", "B3", "REVIVE"):
        assert policy not in source
