"""Authorization requirement tests — only AUTHORIZED executes."""

from revive.domain.enums import ActionCode, ApprovalRequestState
from revive.policy import AuthorizationState, authorize_execution
from revive.policy.models import ExecutionAuthorization
from revive.policy.config import PolicyRules
from revive.decision.ledger import ReservationLedger
from revive.execution import ExecutionEnvironment, execute_authorization
from revive.audit import AuditJournal
from revive.execution.models import ExecutionStage
from revive.execution.store import ExecutionStore

from tests.execution.helpers import (
    authorize_ctx,
    authorize_selected,
    candidate_for,
    decision_for,
    fixture_partition,
    valuation_for,
    NOW,
)


def _exec_env():
    return ExecutionEnvironment(
        oracle_partition=fixture_partition(),
        value_at_risk_paise=5000,
        customer_id="cust_var",
    )


def _ledger_with_reservation(decision):
    ledger = ReservationLedger()
    from revive.decision.models import ResourceReservation, ReservationStatus

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


def test_authorized_executes():
    auth, decision, cand, val = authorize_selected(ActionCode.A01)
    assert auth.authorization_state == AuthorizationState.AUTHORIZED
    result = execute_authorization(
        auth,
        decision,
        cand,
        val,
        _exec_env(),
        _ledger_with_reservation(decision),
        NOW + 2000,
    )
    assert result.execution_stage == ExecutionStage.SUCCEEDED
    assert result.duplicate is False
    assert result.realized_outcome is not None
    assert result.realized_outcome.recovered_amount_paise == 5000


def test_blocked_rejected():
    decision = decision_for(action=ActionCode.A01)
    cand = candidate_for(ActionCode.A01)
    val = valuation_for(ActionCode.A01)
    auth = authorize_execution(
        decision, cand, val, authorize_ctx(payment_succeeded=True),
    )
    assert auth.authorization_state == AuthorizationState.BLOCKED
    result = execute_authorization(
        auth, decision, cand, val, _exec_env(), ReservationLedger(), NOW + 2000,
    )
    assert result.execution_stage == ExecutionStage.CANCELLED
    assert result.failure_reason.startswith("NOT_AUTHORIZED")
    assert result.realized_outcome is None


def test_stale_rejected():
    decision = decision_for()
    cand = candidate_for()
    val = valuation_for()
    auth = authorize_execution(decision, cand, val, authorize_ctx(reconciliation_status="STALE"))
    assert auth.authorization_state == AuthorizationState.STALE
    result = execute_authorization(
        auth, decision, cand, val, _exec_env(), ReservationLedger(), NOW + 2000,
    )
    assert result.execution_stage == ExecutionStage.CANCELLED


def test_expired_authorization_rejected():
    auth, decision, cand, val = authorize_selected(ActionCode.A01)
    expired = ExecutionAuthorization(
        **{**auth.to_dict(), "authorization_state": AuthorizationState.EXPIRED.value}
    )
    # rebuild with enum
    expired_auth = ExecutionAuthorization(
        authorization_id=auth.authorization_id,
        decision_id=auth.decision_id,
        opportunity_id=auth.opportunity_id,
        candidate_id=auth.candidate_id,
        action_code=auth.action_code,
        authorized_parameters=dict(auth.authorized_parameters),
        authorization_state=AuthorizationState.EXPIRED,
        gate_trace=auth.gate_trace,
        stopping_results=auth.stopping_results,
        approval_requirement=auth.approval_requirement,
        approval_state=auth.approval_state,
        policy_pack_version=auth.policy_pack_version,
        configuration_hash=auth.configuration_hash,
        allocator_version=auth.allocator_version,
        valuation_version=auth.valuation_version,
        authorization_version=auth.authorization_version,
        authorized_at_micros=auth.authorized_at_micros,
        expires_at_micros=auth.expires_at_micros,
        idempotency_key=auth.idempotency_key,
        enrv_paise=auth.enrv_paise,
        blocking_gate_id=auth.blocking_gate_id,
        blocking_reason_code="EXPIRED",
        audit_reference=auth.audit_reference,
        explanation=auth.explanation,
    )
    result = execute_authorization(
        expired_auth, decision, cand, val, _exec_env(), ReservationLedger(), NOW + 2000,
    )
    assert result.execution_stage == ExecutionStage.CANCELLED


def test_approval_required_rejected_until_approved():
    decision = decision_for(enrv=9000, action=ActionCode.A05)
    cand = candidate_for(ActionCode.A05)
    val = valuation_for(ActionCode.A05, enrv=9000)
    pending = authorize_execution(
        decision, cand, val,
        authorize_ctx(value_at_risk_paise=8_000_000),
        rules=PolicyRules(approval_value_threshold_paise=8_000_000),
    )
    assert pending.authorization_state == AuthorizationState.REQUIRES_HUMAN_APPROVAL
    result = execute_authorization(
        pending, decision, cand, val, _exec_env(), ReservationLedger(), NOW + 2000,
    )
    assert result.execution_stage == ExecutionStage.CANCELLED

    approved = authorize_execution(
        decision, cand, val,
        authorize_ctx(
            value_at_risk_paise=8_000_000,
            approval_state=ApprovalRequestState.APPROVED,
        ),
        rules=PolicyRules(approval_value_threshold_paise=8_000_000),
    )
    ledger = _ledger_with_reservation(decision)
    ledger.reserve(
        (
            __import__(
                "revive.decision.models", fromlist=["ResourceReservation"]
            ).ResourceReservation(
                reservation_id="res_msg",
                decision_id=decision.decision_id,
                cycle_id=decision.cycle_id,
                resource_key="message_capacity",
                quantity=1,
                customer_id=None,
                reserved_at_micros=NOW,
                expires_at_micros=decision.expires_at_micros,
                status=__import__(
                    "revive.decision.models", fromlist=["ReservationStatus"]
                ).ReservationStatus.ACTIVE,
            ),
        )
    )
    ok = execute_authorization(
        approved, decision, cand, val, _exec_env(), ledger, NOW + 2000,
    )
    assert ok.execution_stage in {
        ExecutionStage.SUCCEEDED,
        ExecutionStage.PERMANENT_FAILURE,
        ExecutionStage.RETRYABLE,
    }
