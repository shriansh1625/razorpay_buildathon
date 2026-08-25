"""Demo-grade authorization scenarios."""

from revive.config.policy_pack import PolicyPack, PolicyPackStatus
from revive.domain.enums import ActionCode, ApprovalRequestState, DecisionOutcome
from revive.decision.models import (
    AllocationDecision,
    AllocationSnapshot,
    DecisionLifecycleStatus,
)
from revive.policy import (
    AuthorizationState,
    AuthorizeContext,
    authorize_execution,
    default_policy_rules,
)
from revive.policy.config import PolicyRules
from revive.recovery.candidates.models import RecoveryCandidate, ResourceRequirement
from revive.recovery.valuation.models import CandidateValuation
from revive.domain.enums import CandidateAvailability

NOW = 3_600_000_000


def _decision(
    action: ActionCode = ActionCode.A05,
    enrv: int = 5000,
    value: int = 5_000_000,
) -> AllocationDecision:
    snap = AllocationSnapshot(
        opportunity_id="opp_1",
        customer_id="cust_1",
        value_at_risk_paise=value,
        candidate_ids=("cand_1",),
        valuation_ids=("val_1",),
        valuation_version="0.7.0-m7",
        strategy_version="strat_m7_dev",
        resource_capacities_digest="abc",
        simulation_time_micros=NOW,
        opportunity_state="PRICED",
    )
    return AllocationDecision(
        decision_id="dec_test123456789012345678901",
        cycle_id="cyc_1",
        opportunity_id="opp_1",
        customer_id="cust_1",
        outcome=DecisionOutcome.SELECTED,
        action_code=action,
        candidate_id="cand_1",
        enrv_paise=enrv,
        reason_code="ALLOCATED",
        idempotency_key="idem_test",
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


def _candidate(action: ActionCode, **params) -> RecoveryCandidate:
    base_params = {"channel": "SMS", "incentive_tier": "TIER_0"}
    base_params.update(params)
    resources: tuple[ResourceRequirement, ...] = ()
    if action not in (ActionCode.A00, ActionCode.A01, ActionCode.A02):
        resources = (
            ResourceRequirement("message_capacity", 1),
            ResourceRequirement("contact_allowance", 1),
        )
    if action in (ActionCode.A01, ActionCode.A02):
        resources = (ResourceRequirement("retry_slots", 1),)
    return RecoveryCandidate(
        candidate_id="cand_1",
        opportunity_id="opp_1",
        cycle_id="cyc_1",
        action_code=action,
        params=base_params,
        availability_status=CandidateAvailability.AVAILABLE,
        prerequisites_satisfied=(),
        prerequisites_failed=(),
        resource_requirements=resources,
        nominal_cost_paise=0,
        earliest_eligible_at_micros=None,
        approval_required=False,
        reason_codes=(),
        provenance=("test",),
        policy_pack_version="test",
    )


def _valuation(enrv: int = 5000, action: ActionCode = ActionCode.A05) -> CandidateValuation:
    return CandidateValuation(
        valuation_id="val_1",
        candidate_id="cand_1",
        opportunity_id="opp_1",
        cycle_id="cyc_1",
        action_code=action,
        p_action=0.5,
        p_natural=0.3,
        uplift=0.2,
        sigma=0.05,
        predictor_cell_ref="test",
        shrinkage_level=2,
        gross_paise=enrv,
        cost_paise=0,
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


def _ctx(**kwargs) -> AuthorizeContext:
    defaults = {
        "now_micros": NOW + 1000,
        "opportunity_state": "PRICED",
        "value_at_risk_paise": 5_000_000,
        "customer_id": "cust_1",
        "recovery_window_expires_at_micros": NOW + 10_000_000,
        "merchant_local_hour": 12,
        "configuration_hash": "cfg_test_hash",
        "reconciliation_status": "VALID",
    }
    defaults.update(kwargs)
    return AuthorizeContext(**defaults)


def test_max_discount_exceeded_blocked():
    decision = _decision(ActionCode.A10, enrv=8000)
    cand = _candidate(ActionCode.A10, incentive_tier="TIER_3", incentive_pct=10.0)
    val = _valuation(8000, ActionCode.A10)
    auth = authorize_execution(decision, cand, val, _ctx(), rules=PolicyRules(max_incentive_pct=5.0))
    assert auth.authorization_state == AuthorizationState.BLOCKED
    assert auth.blocking_reason_code == "MAX_DISCOUNT_EXCEEDED"
    assert auth.blocking_gate_id == "G5"
    g5 = next(g for g in auth.gate_trace if g.gate_id == "G5")
    assert g5.detail["proposed_pct"] == 10.0
    assert g5.detail["allowed_pct"] == 5.0


def test_max_contacts_reached_blocked():
    decision = _decision()
    auth = authorize_execution(
        decision,
        _candidate(ActionCode.A05),
        _valuation(),
        _ctx(contacts_today=2),
        rules=PolicyRules(max_contacts_per_customer=2),
    )
    assert auth.authorization_state == AuthorizationState.BLOCKED
    assert auth.blocking_reason_code == "MAX_CONTACTS_REACHED"


def test_high_value_requires_approval_then_authorized():
    decision = _decision(enrv=9000, value=8_000_000)
    cand = _candidate(ActionCode.A05)
    val = _valuation(9000)
    pending = authorize_execution(
        decision, cand, val, _ctx(value_at_risk_paise=8_000_000),
        rules=PolicyRules(approval_value_threshold_paise=8_000_000),
    )
    assert pending.authorization_state == AuthorizationState.REQUIRES_HUMAN_APPROVAL

    approved = authorize_execution(
        decision, cand, val,
        _ctx(value_at_risk_paise=8_000_000, approval_state=ApprovalRequestState.APPROVED),
        rules=PolicyRules(approval_value_threshold_paise=8_000_000),
    )
    assert approved.authorization_state == AuthorizationState.AUTHORIZED


def test_payment_recovered_blocks_retry():
    decision = _decision(ActionCode.A01)
    auth = authorize_execution(
        decision,
        _candidate(ActionCode.A01),
        _valuation(),
        _ctx(payment_succeeded=True),
    )
    assert auth.authorization_state == AuthorizationState.BLOCKED
    assert any(s.rule_id == "SR-02" and s.fired for s in auth.stopping_results)
