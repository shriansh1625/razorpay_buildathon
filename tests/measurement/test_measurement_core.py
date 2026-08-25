"""Core measurement tests — attribution, incremental, costs."""

from revive.domain.enums import ActionCode, AttributionClass
from revive.execution import ExecutionEnvironment, execute_authorization
from revive.execution.models import ExecutionStage
from revive.measurement import measure_execution
from revive.decision.ledger import ReservationLedger
from revive.decision.models import ResourceReservation, ReservationStatus
from revive.simulation.oracle._partition import ActionResponse, OraclePartition, OracleRow

from tests.execution.helpers import (
    NOW,
    authorize_ctx,
    authorize_selected,
    candidate_for,
    decision_for,
    valuation_for,
)
from revive.policy import authorize_execution
from tests.measurement.helpers import execute_and_measure, synthetic_execution_result


def _message_ledger(decision):
    ledger = ReservationLedger()
    ledger.reserve(
        (
            ResourceReservation(
                reservation_id="res_msg",
                decision_id=decision.decision_id,
                cycle_id=decision.cycle_id,
                resource_key="message_capacity",
                quantity=1,
                customer_id=None,
                reserved_at_micros=NOW,
                expires_at_micros=decision.expires_at_micros,
                status=ReservationStatus.ACTIVE,
            ),
        )
    )
    return ledger


def _retry_ledger(decision):
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


def test_full_recovery_attributed():
    result, m, _, val = execute_and_measure(ActionCode.A01)
    assert result.execution_stage == ExecutionStage.SUCCEEDED
    assert m.gross_recovered_paise == 5000
    assert m.attributed_recovered_paise == 5000
    assert m.incremental_recovered_paise == 5000
    assert m.identity_holds()
    assert val.enrv_paise == m.predicted_enrv_paise


def test_no_recovery():
    partition = OraclePartition()
    partition.add_row(
        OracleRow(
            opportunity_id="opp_fail",
            customer_id="c1",
            recovers_naturally=False,
            natural_recovery_at_micros=None,
            natural_amount_paise=0,
            per_action_response={"A05": ActionResponse(False, 0, 0)},
            fatigue_curve={0: 1.0},
        )
    )
    decision = decision_for(opportunity_id="opp_fail", action=ActionCode.A05)
    cand = candidate_for("opp_fail", ActionCode.A05)
    val = valuation_for("opp_fail", ActionCode.A05)
    auth = authorize_execution(decision, cand, val, authorize_ctx())
    env = ExecutionEnvironment(
        oracle_partition=partition, value_at_risk_paise=5000, customer_id="c1",
    )
    result = execute_authorization(
        auth, decision, cand, val, env, _message_ledger(decision), NOW + 2000,
    )
    m = measure_execution(result, val, decision, value_at_risk_paise=5000)
    assert m.gross_recovered_paise == 0
    assert m.incremental_recovered_paise == 0


def test_partial_recovery():
    exec_result, decision, val = synthetic_execution_result(
        execution_id="exec_partial", recovered=30_000,
    )
    m = measure_execution(exec_result, val, decision, value_at_risk_paise=50_000)
    assert m.gross_recovered_paise == 30_000
    assert m.partial_recovery is True
    assert m.remaining_exposure_paise == 20_000


def test_failed_execution_still_records_cost():
    exec_result, decision, val = synthetic_execution_result(
        execution_id="exec_fail",
        recovered=0,
        stage=ExecutionStage.PERMANENT_FAILURE,
        cost=250,
    )
    m = measure_execution(exec_result, val, decision, value_at_risk_paise=5000)
    assert m.gross_recovered_paise == 0
    assert m.realized_cost_paise == 250
    assert m.realized_net_value_paise == -250


def test_prediction_vs_realization_separate():
    result, m, _, val = execute_and_measure()
    assert m.predicted_enrv_paise == val.enrv_paise
    assert m.predicted_cost_paise == val.cost_paise
    assert m.realized_cost_paise == result.realized_cost_paise


def test_incremental_vs_no_action_reference():
    partition = OraclePartition()
    partition.add_row(
        OracleRow(
            opportunity_id="opp_inc",
            customer_id="c1",
            recovers_naturally=True,
            natural_recovery_at_micros=60 * 60 * 1_000_000,
            natural_amount_paise=7_000,
            per_action_response={
                "A01": ActionResponse(True, 30 * 60 * 1_000_000, 18_000),
            },
            fatigue_curve={0: 1.0},
        )
    )
    decision = decision_for(opportunity_id="opp_inc", action=ActionCode.A01)
    cand = candidate_for("opp_inc", ActionCode.A01)
    val = valuation_for("opp_inc", ActionCode.A01, enrv=11_000)
    auth = authorize_execution(decision, cand, val, authorize_ctx())
    env = ExecutionEnvironment(
        oracle_partition=partition, value_at_risk_paise=20_000, customer_id="c1",
    )
    result = execute_authorization(
        auth, decision, cand, val, env, _retry_ledger(decision), NOW + 2000,
    )
    m = measure_execution(
        result, val, decision,
        value_at_risk_paise=20_000,
        partition=partition,
    )
    assert m.gross_recovered_paise == 18_000
    assert m.realized_no_action_reference_paise == 7_000
    assert m.incremental_vs_no_action_paise == 11_000


def test_natural_recovery_attribution():
    exec_result, decision, val = synthetic_execution_result(
        execution_id="exec_nat", recovered=8000, attribution="NATURAL",
    )
    m = measure_execution(exec_result, val, decision, value_at_risk_paise=10_000)
    assert m.natural_recovered_paise == 8000
    assert m.attributed_recovered_paise == 0
    assert m.incremental_recovered_paise == 0
    assert m.attribution_class == AttributionClass.NATURAL
