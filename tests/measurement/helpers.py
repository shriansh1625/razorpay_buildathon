"""Shared builders for measurement tests."""

from __future__ import annotations

from revive.decision.ledger import ReservationLedger
from revive.decision.models import ResourceReservation, ReservationStatus
from revive.domain.enums import ActionCode, InterventionState
from revive.execution import ExecutionEnvironment, execute_authorization
from revive.execution.models import ExecutionStage, RealizedOutcome
from revive.measurement import measure_execution
from revive.recovery.valuation.models import CandidateValuation
from revive.simulation.types import OutcomeKind
from tests.execution.helpers import (
    NOW,
    authorize_selected,
    candidate_for,
    decision_for,
    fixture_partition,
    partition_with_a02,
    valuation_for,
)


def ledger_for(decision):
    ledger = ReservationLedger()
    ledger.reserve(
        (
            ResourceReservation(
                reservation_id="res_1",
                decision_id=decision.decision_id,
                cycle_id=decision.cycle_id,
                resource_key="retry_slots",
                quantity=1,
                customer_id=None,
                reserved_at_micros=NOW,
                expires_at_micros=decision.expires_at_micros,
                status=ReservationStatus.ACTIVE,
            ),
        )
    )
    return ledger


def execute_and_measure(
    action: ActionCode = ActionCode.A01,
    value_at_risk: int = 5000,
    *,
    partition=None,
    enrv: int = 5000,
):
    auth, decision, cand, val = authorize_selected(action)
    val = valuation_for(enrv=enrv, action=action)
    env = ExecutionEnvironment(
        oracle_partition=partition or fixture_partition(),
        value_at_risk_paise=value_at_risk,
        customer_id="cust_var",
    )
    result = execute_authorization(
        auth, decision, cand, val, env, ledger_for(decision), NOW + 2000,
    )
    measurement = measure_execution(
        result, val, decision, value_at_risk_paise=value_at_risk, partition=env.oracle_partition,
    )
    return result, measurement, decision, val


def synthetic_execution_result(
    *,
    execution_id: str = "exec_test",
    opportunity_id: str = "opp_var",
    recovered: int = 0,
    attribution: str = "ATTRIBUTED",
    within_horizon: bool = True,
    late: bool = False,
    cost: int = 100,
    stage: ExecutionStage = ExecutionStage.SUCCEEDED,
):
    from revive.execution.models import ExecutionResult
    from revive.domain.enums import ActionCode

    decision = decision_for(opportunity_id=opportunity_id)
    val = valuation_for(opportunity_id=opportunity_id)
    realized = None
    if recovered > 0 or stage == ExecutionStage.SUCCEEDED:
        realized = RealizedOutcome(
            outcome_kind=OutcomeKind.RECOVERED if recovered > 0 else OutcomeKind.NOT_RECOVERED,
            recovered_amount_paise=recovered,
            recovered_at_micros=NOW + 3000,
            observed_within_horizon=within_horizon,
            late_recovery=late,
            attribution_class=attribution,
        )
    result = ExecutionResult(
        execution_id=execution_id,
        authorization_id="auth_test",
        decision_id=decision.decision_id,
        opportunity_id=opportunity_id,
        candidate_id="cand_1",
        action_code=ActionCode.A01,
        intervention_id="int_test",
        execution_stage=stage,
        adapter_result=None,
        predicted_cost_paise=100,
        realized_cost_paise=cost,
        predicted_enrv_paise=val.enrv_paise,
        idempotency_key=f"idem_{opportunity_id}_A01",
        executed_at_micros=NOW + 2000,
        duplicate=False,
        failure_reason=None,
        ledger_settlement=None,
        intervention_state=InterventionState.COMPLETED_SUCCESS,
        opportunity_state="RECOVERED",
        payment_state=None,
        customer_response=None,
        realized_outcome=realized,
        resource_consumed=(),
        scheduled_at_micros=None,
        audit_intent_ref="aud_intent",
        audit_result_ref="aud_result",
        configuration_hash="cfg_test_hash",
        authorization_version="0.10.0-m10",
        execution_version="0.11.0-m11",
    )
    return result, decision, val
