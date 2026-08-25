"""M13.18 — execution bridge repair tests."""

from __future__ import annotations

from collections import Counter

from dataclasses import replace

import pytest

from revive.benchmark.calibration.baseline_separation import _mid_cycle_micros
from revive.benchmark.calibration.config import calibration_config
from revive.benchmark.official.baseline_pipeline import new_baseline_state, run_baseline_cycle_full
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.revive_pipeline import new_revive_state, run_revive_cycle
from revive.benchmark.official.world import clone_shared_world, generate_shared_world
from revive.benchmark.runner import run_baseline_cycle
from revive.benchmark.types import BaselinePolicyId
from revive.config.policy_pack import official_sealed_policy_pack
from revive.domain.enums import ActionCode, ApprovalRequestState, DecisionOutcome
from revive.policy import AuthorizationState, authorize_execution
from revive.policy.config import PolicyRules
from revive.policy.gates import g7_approval_triggers
from revive.policy.simulated_approver import (
    SIMULATED_V1_MODEL,
    authorize_context_with_simulated_approval,
    resolve_simulated_approval_state,
    simulated_v1_approval_state,
)
from revive.recovery.sentinel.detect import detect
from revive.recovery.sentinel.identity_bridge import (
    assert_baseline_identity_invariant,
    index_sentinel_by_natural_key,
    resolve_sentinel_for_world_opportunity_id,
)
from revive.simulation.generator import generate_dataset
from revive.simulation.observation import get_observable_state
from revive.simulation.types import GenerationProfile
from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.policies import BenchmarkPolicyId, to_baseline_id
from revive.benchmark.official.metrics import compute_policy_metrics
from tests.policy.test_authorization_demo import _candidate, _ctx, _decision, _valuation


def _official_seed1_bundle():
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen = generator_config_for_cell(config, 1, GenerationProfile.BALANCED)
    return pack, generate_shared_world(gen)


@pytest.mark.parametrize("policy_id", [BaselinePolicyId.B1, BaselinePolicyId.B2, BaselinePolicyId.B3])
def test_baseline_identity_bridge_matches_sentinel(policy_id: BaselinePolicyId):
    pack, bundle = _official_seed1_bundle()
    view = get_observable_state(bundle.world)
    now = bundle.cycle_times_micros[len(bundle.cycle_times_micros) // 2]
    sentinel = detect(view, now)
    sentinel_index = index_sentinel_by_natural_key(sentinel)

    cycle = run_baseline_cycle(
        policy_id,
        view,
        cycle_id="bridge_test",
        now_micros=now,
        policy_pack=pack,
    )
    selected = [
        d
        for d in cycle.decisions
        if d.outcome == DecisionOutcome.SELECTED and d.action_code != ActionCode.A00
    ]
    assert selected, f"{policy_id.value} should select at mid-cycle"

    matches = 0
    for decision in selected:
        resolved = resolve_sentinel_for_world_opportunity_id(
            decision.opportunity_id,
            view,
            sentinel_index,
        )
        if resolved is None:
            continue
        assert_baseline_identity_invariant(
            decision.opportunity_id,
            view,
            sentinel_index,
        )
        matches += 1

    assert matches > 0


def test_b0_remains_no_action():
    pack, bundle = _official_seed1_bundle()
    view = get_observable_state(bundle.world)
    now = bundle.cycle_times_micros[100]
    cycle = run_baseline_cycle(
        BaselinePolicyId.B0,
        view,
        cycle_id="b0",
        now_micros=now,
        policy_pack=pack,
    )
    selected = [d for d in cycle.decisions if d.outcome == DecisionOutcome.SELECTED]
    assert selected == []


def test_simulated_v1_no_approval_required_returns_none():
    rules = PolicyRules(approval_value_threshold_paise=999_999_999)
    ctx = _ctx(value_at_risk_paise=1000)
    decision = _decision(enrv=1000, value=1000)
    state = resolve_simulated_approval_state(
        model_version=SIMULATED_V1_MODEL,
        master_seed=1,
        decision=decision,
        action=ActionCode.A05,
        ctx=ctx,
        rules=rules,
        enrv_paise=1000,
        enrv_lo_paise=990,
        enrv_hi_paise=1010,
    )
    assert state is None


def test_simulated_v1_approval_required_can_approve():
    rules = PolicyRules(
        approval_value_threshold_paise=1000,
        approval_uncertainty_ratio=0.5,
    )
    ctx = _ctx(value_at_risk_paise=5000)
    decision = _decision(enrv=5000, value=5000)
    triggers = g7_approval_triggers(
        ActionCode.A05, ctx, rules, 5000, 4900, 5100
    )
    assert triggers
    approved = simulated_v1_approval_state(
        master_seed=1,
        idempotency_key="idem_0",
        triggers=triggers,
        ctx=ctx,
    )
    assert approved == ApprovalRequestState.APPROVED


def test_simulated_v1_approval_required_can_deny_by_draw():
    rules = PolicyRules(approval_value_threshold_paise=1000)
    ctx = _ctx(value_at_risk_paise=5000)
    triggers = ("VALUE_THRESHOLD",)
    denied = simulated_v1_approval_state(
        master_seed=1,
        idempotency_key="idem_2",
        triggers=triggers,
        ctx=ctx,
    )
    assert denied == ApprovalRequestState.REJECTED


def test_simulated_v1_approval_required_can_deny_on_risk_flags():
    rules = PolicyRules(approval_value_threshold_paise=1000)
    ctx = _ctx(value_at_risk_paise=5000, risk_flags=frozenset({"FRAUD"}))
    triggers = ("VALUE_THRESHOLD",)
    denied = simulated_v1_approval_state(
        master_seed=1,
        idempotency_key="idem_any",
        triggers=triggers,
        ctx=ctx,
    )
    assert denied == ApprovalRequestState.REJECTED


def test_simulated_v1_wiring_authorizes_when_required():
    rules = PolicyRules(approval_value_threshold_paise=8_000_000)
    decision = replace(_decision(enrv=9000, value=8_000_000), idempotency_key="idem_0")
    cand = _candidate(ActionCode.A05)
    val = _valuation(9000)
    base_ctx = _ctx(value_at_risk_paise=8_000_000)
    auth_ctx = authorize_context_with_simulated_approval(
        base_ctx,
        model_version=SIMULATED_V1_MODEL,
        master_seed=1,
        decision=decision,
        action=ActionCode.A05,
        rules=rules,
        enrv_paise=val.enrv_paise,
        enrv_lo_paise=val.enrv_lo_paise,
        enrv_hi_paise=val.enrv_hi_paise,
    )
    assert auth_ctx.approval_state == ApprovalRequestState.APPROVED
    auth = authorize_execution(decision, cand, val, auth_ctx, rules=rules)
    assert auth.authorization_state == AuthorizationState.AUTHORIZED


def test_m10_safety_discount_still_blocks():
    decision = _decision(ActionCode.A10, enrv=8000)
    cand = _candidate(ActionCode.A10, incentive_tier="TIER_3", incentive_pct=10.0)
    val = _valuation(8000, ActionCode.A10)
    auth_ctx = authorize_context_with_simulated_approval(
        _ctx(),
        model_version=SIMULATED_V1_MODEL,
        master_seed=1,
        decision=decision,
        action=ActionCode.A10,
        rules=PolicyRules(max_incentive_pct=5.0),
        enrv_paise=val.enrv_paise,
        enrv_lo_paise=val.enrv_lo_paise,
        enrv_hi_paise=val.enrv_hi_paise,
    )
    auth = authorize_execution(
        decision, cand, val, auth_ctx, rules=PolicyRules(max_incentive_pct=5.0)
    )
    assert auth.authorization_state == AuthorizationState.BLOCKED
    assert auth.blocking_gate_id == "G5"


def test_representative_execution_path_reachability():
    pack, bundle = _official_seed1_bundle()
    profile = profile_from_string(bundle.profile)
    caps = benchmark_resource_capacities(profile)
    mid_idx = len(bundle.cycle_times_micros) // 2
    now = bundle.cycle_times_micros[mid_idx]

    for policy in (BenchmarkPolicyId.B1, BenchmarkPolicyId.B2, BenchmarkPolicyId.B3):
        baseline_id = to_baseline_id(policy)
        assert baseline_id is not None
        cloned = clone_shared_world(bundle)
        state = new_baseline_state(cloned, baseline_id, pack)
        run_baseline_cycle_full(state, f"cyc_{mid_idx:04d}", now)
        assert len(state.authorizations) > 0, policy.value
        assert any(
            a.authorization_state == AuthorizationState.AUTHORIZED
            for a in state.authorizations
        ), policy.value

    cloned = clone_shared_world(bundle)
    revive_state = new_revive_state(cloned, pack, caps)
    run_revive_cycle(revive_state, f"cyc_{mid_idx:04d}", now)
    auth_states = Counter(a.authorization_state for a in revive_state.authorizations)
    assert revive_state.authorizations, "REVIVE should reach M10"
    assert auth_states[AuthorizationState.AUTHORIZED] > 0


def test_representative_b1_partial_run_has_interventions():
    pack, bundle = _official_seed1_bundle()
    cloned = clone_shared_world(bundle)
    state = new_baseline_state(cloned, BaselinePolicyId.B1, pack)
    mid_idx = len(cloned.cycle_times_micros) // 2
    run_baseline_cycle_full(state, f"cyc_{mid_idx:04d}", cloned.cycle_times_micros[mid_idx])
    profile = profile_from_string(cloned.profile)
    caps = benchmark_resource_capacities(profile)
    partial = compute_policy_metrics(
        "B1",
        1,
        "BALANCED",
        tuple(state.measurements),
        tuple(state.executions),
        tuple(state.authorizations),
        incentive_budget_capacity_paise=caps.incentive_budget_paise,
        retry_capacity=caps.retry_slots,
        message_capacity=caps.message_capacity,
    )
    assert partial.intervention_count > 0


def test_calibration_scale_bridge_nonzero():
    dataset = generate_dataset(calibration_config(1, GenerationProfile.BALANCED))
    view = get_observable_state(dataset.world)
    now = _mid_cycle_micros(dataset.config)
    sentinel = detect(view, now)
    sentinel_index = index_sentinel_by_natural_key(sentinel)
    cycle = run_baseline_cycle(
        BaselinePolicyId.B1,
        view,
        cycle_id="cal",
        now_micros=now,
        policy_pack=official_sealed_policy_pack(),
    )
    selected = [
        d
        for d in cycle.decisions
        if d.outcome == DecisionOutcome.SELECTED and d.action_code != ActionCode.A00
    ]
    matched = sum(
        1
        for d in selected
        if resolve_sentinel_for_world_opportunity_id(
            d.opportunity_id, view, sentinel_index
        )
        is not None
    )
    assert matched > 0
