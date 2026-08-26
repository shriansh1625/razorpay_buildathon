"""M13.27 production metrics tail performance and equivalence tests."""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.cells.store import metrics_checksum
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.metrics import (
    CONTACT_ACTIONS,
    PolicyRunMetrics,
    compute_policy_metrics,
)
from revive.benchmark.official.policies import BenchmarkPolicyId
from revive.benchmark.official.revive_pipeline import new_revive_state, run_revive_cycle
from revive.benchmark.official.world import clone_shared_world, generate_shared_world
from revive.config.policy_pack import official_sealed_policy_pack
from revive.domain.enums import ActionCode
from revive.execution.models import ExecutionStage
from revive.measurement.aggregate import safety_event_counts
from revive.measurement.models import RecoveryMeasurement
from revive.policy.models import AuthorizationState
from revive.simulation.types import GenerationProfile
from scripts.m13_22_fingerprint import cycle_m6_m7_fingerprint

BASELINE_15 = {
    "m6_hash": "b9af5e6f94cf16997a1fa4be600130396041ac6c379aa672dbaeb1b2d070879f",
    "m7_hash": "bda2c8a45a6c6ad460958bf3f4455470b9ee66b0055e45b8bcd4ee198f1f2e4c",
    "metrics_checksum": "37d9db486094b16b614dfa20230c7e229d23df3e147674c330ada324858755cf",
}


def _caps(profile: str):
    return benchmark_resource_capacities(profile_from_string(profile))


def _compute_policy_metrics_reference(
    policy_id: str,
    seed: int,
    profile: str,
    measurements: tuple[RecoveryMeasurement, ...],
    executions,
    authorizations,
    *,
    incentive_budget_capacity_paise: int,
    retry_capacity: int,
    message_capacity: int,
) -> PolicyRunMetrics:
    """Pre-M13.27 reference implementation for equivalence checks."""
    from revive.measurement.aggregate import aggregate_batch

    batch = aggregate_batch(measurements)
    metrics = PolicyRunMetrics(
        policy_id=policy_id,
        seed=seed,
        profile=profile,
        net_recovered_paise=batch.total_net_recovery_paise,
        gross_recovered_paise=batch.total_gross_recovered_paise,
        natural_recovered_paise=batch.total_natural_recovery_paise,
        incremental_recovered_paise=batch.total_incremental_recovery_paise,
        realized_cost_paise=batch.total_realized_cost_paise,
        intervention_count=len(executions),
    )

    metrics.contact_count = sum(
        1
        for e in executions
        if e.action_code in CONTACT_ACTIONS
        and e.execution_stage == ExecutionStage.SUCCEEDED
    )

    metrics.predicted_enrv_paise = sum(m.predicted_enrv_paise for m in measurements)
    metrics.realized_incremental_paise = sum(m.incremental_recovered_paise for m in measurements)
    metrics.enrv_prediction_error_paise = sum(m.enrv_prediction_error_paise for m in measurements)
    metrics.recovery_prediction_error_paise = sum(
        m.recovery_prediction_error_paise for m in measurements
    )

    if batch.total_at_risk_paise > 0:
        metrics.recovery_rate = batch.total_gross_recovered_paise / batch.total_at_risk_paise

    metrics.unauthorized_executions = sum(
        1
        for a in authorizations
        if a.authorization_state != AuthorizationState.AUTHORIZED
        and any(
            e.authorization_id == a.authorization_id
            and e.execution_stage == ExecutionStage.SUCCEEDED
            for e in executions
        )
    )

    safety = safety_event_counts(executions, ())
    metrics.execution_failures = safety.get("execution_failed", 0)
    metrics.idempotency_conflicts = safety.get("idempotency_duplicates", 0)

    metrics.duplicate_effects = sum(1 for m in measurements if m.duplicate_measurement)

    total_cost = batch.total_realized_cost_paise
    if incentive_budget_capacity_paise > 0:
        metrics.budget_utilization = total_cost / incentive_budget_capacity_paise

    metrics.resource_utilization = {
        "retry_slots": min(1.0, metrics.intervention_count / max(1, retry_capacity)),
        "message_capacity": min(1.0, metrics.contact_count / max(1, message_capacity)),
    }

    if metrics.unauthorized_executions > 0:
        metrics.run_valid = False
        metrics.invalid_reasons.append("M-16: unauthorized_executions > 0")

    return metrics


def _run_revive_cycles(seed: int, profile: str, *, max_cycles: int | None = None):
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen_config = generator_config_for_cell(config, seed, GenerationProfile(profile))
    bundle = generate_shared_world(gen_config)
    cloned = clone_shared_world(bundle)
    caps = _caps(profile)
    state = new_revive_state(cloned, pack, caps)
    cycle_times = cloned.cycle_times_micros
    if max_cycles is not None:
        cycle_times = cycle_times[:max_cycles]
    for idx, now_micros in enumerate(cycle_times):
        run_revive_cycle(state, f"cyc_{idx:04d}", now_micros)
    return (
        tuple(state.measurements),
        tuple(state.executions),
        tuple(state.authorizations),
        caps,
        cloned.seed,
        cloned.profile,
    )


def _metrics_kwargs(
    measurements,
    executions,
    authorizations,
    caps,
    seed: int,
    profile: str,
) -> dict:
    return {
        "policy_id": BenchmarkPolicyId.REVIVE.value,
        "seed": seed,
        "profile": profile,
        "measurements": measurements,
        "executions": executions,
        "authorizations": authorizations,
        "incentive_budget_capacity_paise": caps.incentive_budget_paise,
        "retry_capacity": caps.retry_slots,
        "message_capacity": caps.message_capacity,
    }


@pytest.fixture(scope="module")
def abundant_seed1_population():
    return _run_revive_cycles(1, "ABUNDANT")


def test_reference_matches_optimized_empty_inputs():
    caps = _caps("BALANCED")
    kwargs = _metrics_kwargs((), (), (), caps, 1, "BALANCED")
    assert _compute_policy_metrics_reference(**kwargs).to_dict() == compute_policy_metrics(**kwargs).to_dict()


def test_reference_matches_optimized_mid_cycle_balanced():
    measurements, executions, authorizations, caps, seed, profile = _run_revive_cycles(
        1, "BALANCED", max_cycles=128
    )
    kwargs = _metrics_kwargs(measurements, executions, authorizations, caps, seed, profile)
    ref = _compute_policy_metrics_reference(**kwargs)
    opt = compute_policy_metrics(**kwargs)
    assert ref.to_dict() == opt.to_dict()


@pytest.mark.parametrize("profile", ["BALANCED", "SCARCE", "HOSTILE"])
def test_reference_matches_optimized_mid_cycle_profiles(profile: str):
    measurements, executions, authorizations, caps, seed, prof = _run_revive_cycles(
        1, profile, max_cycles=64
    )
    kwargs = _metrics_kwargs(measurements, executions, authorizations, caps, seed, prof)
    assert _compute_policy_metrics_reference(**kwargs).to_dict() == compute_policy_metrics(**kwargs).to_dict()


def test_unauthorized_matching_set_equivalent_synthetic():
    executions = tuple(
        SimpleNamespace(
            authorization_id=f"auth_{i}",
            execution_stage=ExecutionStage.SUCCEEDED,
            action_code=ActionCode.A04,
            duplicate=False,
        )
        for i in range(20_000)
    )
    authorizations = tuple(
        SimpleNamespace(
            authorization_id=f"auth_{i}",
            authorization_state=(
                AuthorizationState.BLOCKED if i % 97 == 0 else AuthorizationState.AUTHORIZED
            ),
        )
        for i in range(25_000)
    )
    caps = _caps("ABUNDANT")
    kwargs = _metrics_kwargs((), executions, authorizations, caps, 1, "ABUNDANT")
    ref = _compute_policy_metrics_reference(**kwargs)
    opt = compute_policy_metrics(**kwargs)
    assert ref.unauthorized_executions == opt.unauthorized_executions
    assert ref.to_dict() == opt.to_dict()


def test_abundant_metrics_deterministic(abundant_seed1_population):
    kwargs = _metrics_kwargs(*abundant_seed1_population)
    first = compute_policy_metrics(**kwargs)
    second = compute_policy_metrics(**kwargs)
    assert first.to_dict() == second.to_dict()
    assert metrics_checksum(first.to_dict()) == metrics_checksum(second.to_dict())


def test_abundant_population_counts(abundant_seed1_population):
    measurements, executions, authorizations, caps, seed, profile = abundant_seed1_population
    metrics = compute_policy_metrics(**_metrics_kwargs(measurements, executions, authorizations, caps, seed, profile))
    assert metrics.intervention_count == len(executions)
    assert metrics.intervention_count > 300_000
    assert len(authorizations) > metrics.intervention_count
    assert metrics.unauthorized_executions == 0
    assert metrics.run_valid is True


def test_abundant_metrics_tail_bounded(abundant_seed1_population):
    kwargs = _metrics_kwargs(*abundant_seed1_population)
    t0 = time.perf_counter()
    compute_policy_metrics(**kwargs)
    elapsed = time.perf_counter() - t0
    assert elapsed < 5.0


def test_reference_matches_optimized_hostile_mid_cycle():
    measurements, executions, authorizations, caps, seed, profile = _run_revive_cycles(
        1, "HOSTILE", max_cycles=96
    )
    kwargs = _metrics_kwargs(measurements, executions, authorizations, caps, seed, profile)
    assert _compute_policy_metrics_reference(**kwargs).to_dict() == compute_policy_metrics(**kwargs).to_dict()


def test_m13_22_seed2_balanced_15_cycle_fingerprints_unchanged():
    result = cycle_m6_m7_fingerprint(2, "BALANCED", cycles=15)
    assert result["m6_hash"] == BASELINE_15["m6_hash"]
    assert result["m7_hash"] == BASELINE_15["m7_hash"]
    assert result["metrics_checksum"] == BASELINE_15["metrics_checksum"]
