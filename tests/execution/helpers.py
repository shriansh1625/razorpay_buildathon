"""Shared builders for execution tests."""

from __future__ import annotations

from revive.config.policy_pack import PolicyPackStatus
from revive.decision.models import (
    AllocationDecision,
    AllocationSnapshot,
    DecisionLifecycleStatus,
)
from revive.domain.enums import ActionCode, CandidateAvailability, DecisionOutcome
from revive.policy import AuthorizeContext, authorize_execution
from revive.policy.config import PolicyRules
from revive.policy.models import ExecutionAuthorization
from revive.recovery.candidates.models import RecoveryCandidate, ResourceRequirement
from revive.recovery.valuation.models import CandidateValuation
from revive.simulation.fixtures import action_variation_fixture
from revive.simulation.oracle._partition import OraclePartition

NOW = 1_000_000
MINUTE_MICROS = 60 * 1_000_000


def fixture_partition() -> OraclePartition:
    return action_variation_fixture()


def decision_for(
    opportunity_id: str = "opp_var",
    action: ActionCode = ActionCode.A01,
    enrv: int = 5000,
    decision_id: str = "dec_test123456789012345678901",
) -> AllocationDecision:
    snap = AllocationSnapshot(
        opportunity_id=opportunity_id,
        customer_id="cust_var",
        value_at_risk_paise=5000,
        candidate_ids=("cand_1",),
        valuation_ids=("val_1",),
        valuation_version="0.7.0-m7",
        strategy_version="strat_m7_dev",
        resource_capacities_digest="abc",
        simulation_time_micros=NOW,
        opportunity_state="AUTHORISED",
    )
    return AllocationDecision(
        decision_id=decision_id,
        cycle_id="cyc_1",
        opportunity_id=opportunity_id,
        customer_id="cust_var",
        outcome=DecisionOutcome.SELECTED,
        action_code=action,
        candidate_id="cand_1",
        enrv_paise=enrv,
        reason_code="ALLOCATED",
        idempotency_key=f"idem_{opportunity_id}_{action.value}",
        created_at_micros=NOW,
        expires_at_micros=NOW + 999_999_999,
        allocator_version="0.8.0-m8",
        allocator_mode="LAGRANGIAN",
        policy_pack_version="pol_test",
        policy_pack_status=PolicyPackStatus.DRAFT,
        configuration_hash="cfg_test_hash",
        strategy_version="strat_m7_dev",
        valuation_version="0.7.0-m7",
        allocation_hash="alloc_hash",
        snapshot=snap,
        lifecycle_status=DecisionLifecycleStatus.RESERVED,
    )


def candidate_for(
    opportunity_id: str = "opp_var",
    action: ActionCode = ActionCode.A01,
    **params,
) -> RecoveryCandidate:
    base_params = {"channel": "SMS", "incentive_tier": "TIER_0"}
    base_params.update(params)
    resources: tuple[ResourceRequirement, ...] = ()
    if action in (ActionCode.A01, ActionCode.A02):
        resources = (ResourceRequirement("retry_slots", 1),)
    elif action not in (ActionCode.A00,):
        resources = (
            ResourceRequirement("message_capacity", 1),
            ResourceRequirement("contact_allowance", 1),
        )
    return RecoveryCandidate(
        candidate_id="cand_1",
        opportunity_id=opportunity_id,
        cycle_id="cyc_1",
        action_code=action,
        params=base_params,
        availability_status=CandidateAvailability.AVAILABLE,
        prerequisites_satisfied=(),
        prerequisites_failed=(),
        resource_requirements=resources,
        nominal_cost_paise=100,
        earliest_eligible_at_micros=params.get("earliest_eligible_at_micros"),
        approval_required=False,
        reason_codes=(),
        provenance=("test",),
        policy_pack_version="test",
    )


def valuation_for(
    opportunity_id: str = "opp_var",
    action: ActionCode = ActionCode.A01,
    enrv: int = 5000,
    cost: int = 100,
) -> CandidateValuation:
    return CandidateValuation(
        valuation_id="val_1",
        candidate_id="cand_1",
        opportunity_id=opportunity_id,
        cycle_id="cyc_1",
        action_code=action,
        p_action=0.5,
        p_natural=0.3,
        uplift=0.2,
        sigma=0.05,
        predictor_cell_ref="test",
        shrinkage_level=2,
        gross_paise=enrv,
        cost_paise=cost,
        expected_incentive_paise=0,
        fatigue_cost_paise=0,
        enrv_paise=enrv,
        enrv_lo_paise=enrv - 100,
        enrv_hi_paise=enrv + 100,
        valuation_version="0.7.0-m7",
        strategy_version="strat_m7_dev",
        provenance=("test",),
        value_drivers=("test",),
    )


def authorize_ctx(**kwargs) -> AuthorizeContext:
    defaults = {
        "now_micros": NOW + 1000,
        "opportunity_state": "AUTHORISED",
        "value_at_risk_paise": 5000,
        "customer_id": "cust_var",
        "recovery_window_expires_at_micros": NOW + 10_000_000,
        "merchant_local_hour": 12,
        "configuration_hash": "cfg_test_hash",
        "reconciliation_status": "VALID",
    }
    defaults.update(kwargs)
    return AuthorizeContext(**defaults)


def authorize_selected(
    action: ActionCode = ActionCode.A01,
    rules: PolicyRules | None = None,
    **ctx_kwargs,
) -> tuple[ExecutionAuthorization, AllocationDecision, RecoveryCandidate, CandidateValuation]:
    cand_kwargs = {
        k: v
        for k, v in ctx_kwargs.items()
        if k in {"delay_minutes", "earliest_eligible_at_micros"}
    }
    ctx_only = {
        k: v
        for k, v in ctx_kwargs.items()
        if k not in {"delay_minutes", "earliest_eligible_at_micros"}
    }
    decision = decision_for(action=action)
    cand = candidate_for(action=action, **cand_kwargs)
    val = valuation_for(action=action)
    auth = authorize_execution(decision, cand, val, authorize_ctx(**ctx_only), rules=rules)
    return auth, decision, cand, val


def partition_with_a02() -> OraclePartition:
    """Fixture partition with A02 delayed-retry oracle response."""
    partition = fixture_partition()
    row = partition.get_row("opp_var")
    if row is None:
        return partition
    from revive.simulation.oracle._partition import ActionResponse, OracleRow

    responses = dict(row.per_action_response)
    responses["A02"] = responses["A01"]
    partition.add_row(
        OracleRow(
            opportunity_id=row.opportunity_id,
            customer_id=row.customer_id,
            recovers_naturally=row.recovers_naturally,
            natural_recovery_at_micros=row.natural_recovery_at_micros,
            natural_amount_paise=row.natural_amount_paise,
            per_action_response=responses,
            fatigue_curve=dict(row.fatigue_curve),
            degradation_cohort_ref=row.degradation_cohort_ref,
        )
    )
    return partition
