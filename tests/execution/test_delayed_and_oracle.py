"""Delayed execution and oracle boundary tests."""

from revive.domain.enums import ActionCode
from revive.decision.ledger import ReservationLedger
from revive.decision.models import ResourceReservation, ReservationStatus
from revive.execution import execute, ExecutionEnvironment, mint_authorised_action
from revive.execution.config import MINUTE_MICROS
from revive.execution.models import ExecutionStage
from revive.execution.store import ExecutionStore
from revive.policy import AuthorizationState
from revive.policy.config import PolicyRules

from tests.execution.helpers import (
    authorize_selected,
    candidate_for,
    partition_with_a02,
    NOW,
)

_LONG_TTL = PolicyRules(authorization_ttl_micros=120 * MINUTE_MICROS)


def _ledger(decision):
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


def test_delayed_retry_not_executed_early():
    delay_minutes = 5
    scheduled_at = NOW + delay_minutes * MINUTE_MICROS
    auth, decision, cand, val = authorize_selected(
        ActionCode.A02,
        rules=_LONG_TTL,
        delay_minutes=delay_minutes,
        earliest_eligible_at_micros=scheduled_at,
    )
    assert auth.authorization_state == AuthorizationState.AUTHORIZED
    cand = candidate_for(
        ActionCode.A02,
        delay_minutes=delay_minutes,
        earliest_eligible_at_micros=scheduled_at,
    )
    env = ExecutionEnvironment(
        oracle_partition=partition_with_a02(),
        value_at_risk_paise=5000,
        customer_id="cust_var",
    )
    ledger = _ledger(decision)
    early = execute(
        mint_authorised_action(auth),
        decision,
        cand,
        val,
        env,
        ledger,
        NOW + 1000,
    )
    assert early.execution_stage == ExecutionStage.SCHEDULED
    assert early.scheduled_at_micros == scheduled_at
    assert early.realized_outcome is None
    assert ledger.has_active(decision.decision_id)


def test_delayed_retry_executes_at_scheduled_time():
    delay_minutes = 5
    scheduled_at = NOW + delay_minutes * MINUTE_MICROS
    auth, decision, cand, val = authorize_selected(
        ActionCode.A02,
        rules=_LONG_TTL,
        delay_minutes=delay_minutes,
        earliest_eligible_at_micros=scheduled_at,
    )
    cand = candidate_for(
        ActionCode.A02,
        delay_minutes=delay_minutes,
        earliest_eligible_at_micros=scheduled_at,
    )
    env = ExecutionEnvironment(
        oracle_partition=partition_with_a02(),
        value_at_risk_paise=5000,
        customer_id="cust_var",
    )
    ledger = _ledger(decision)
    store = ExecutionStore()
    execute(
        mint_authorised_action(auth),
        decision,
        cand,
        val,
        env,
        ledger,
        NOW + 1000,
        store=store,
    )
    late = execute(
        mint_authorised_action(auth),
        decision,
        cand,
        val,
        env,
        ledger,
        scheduled_at,
        store=store,
    )
    assert late.execution_stage == ExecutionStage.SUCCEEDED
    assert late.realized_outcome is not None
    assert late.realized_outcome.recovered_amount_paise == 5000


def test_same_action_different_oracle_outcomes():
    from tests.execution.helpers import fixture_partition, authorize_selected as auth_sel

    partition = fixture_partition()
    env_a = ExecutionEnvironment(
        oracle_partition=partition,
        value_at_risk_paise=5000,
        customer_id="cust_var",
    )
    env_b = ExecutionEnvironment(
        oracle_partition=partition,
        value_at_risk_paise=5000,
        customer_id="cust_var",
    )
    auth_a, decision_a, cand_a, val_a = auth_sel(ActionCode.A01, rules=_LONG_TTL)
    auth_b, decision_b, cand_b, val_b = auth_sel(ActionCode.A05, rules=_LONG_TTL)
    r_ok = execute(
        mint_authorised_action(auth_a),
        decision_a,
        cand_a,
        val_a,
        env_a,
        _ledger(decision_a),
        NOW + 2000,
    )
    ledger_b = ReservationLedger()
    ledger_b.reserve(
        (
            ResourceReservation(
                reservation_id="res_msg",
                decision_id=decision_b.decision_id,
                cycle_id=decision_b.cycle_id,
                resource_key="message_capacity",
                quantity=1,
                customer_id=None,
                reserved_at_micros=NOW,
                expires_at_micros=decision_b.expires_at_micros,
                status=ReservationStatus.ACTIVE,
            ),
        )
    )
    r_fail = execute(
        mint_authorised_action(auth_b),
        decision_b,
        cand_b,
        val_b,
        env_b,
        ledger_b,
        NOW + 2000,
    )
    assert r_ok.realized_outcome.recovered_amount_paise > 0
    assert r_fail.realized_outcome.recovered_amount_paise == 0
    assert "per_action_response" not in r_ok.to_dict()


def test_expiry_prevents_late_delayed_execution():
    delay_minutes = 30
    scheduled_at = NOW + delay_minutes * MINUTE_MICROS
    short_ttl = PolicyRules(authorization_ttl_micros=10 * MINUTE_MICROS)
    auth, decision, cand, val = authorize_selected(
        ActionCode.A02,
        rules=short_ttl,
        earliest_eligible_at_micros=scheduled_at,
    )
    cand = candidate_for(
        ActionCode.A02,
        earliest_eligible_at_micros=scheduled_at,
    )
    env = ExecutionEnvironment(
        oracle_partition=partition_with_a02(),
        value_at_risk_paise=5000,
    )
    store = ExecutionStore()
    ledger = _ledger(decision)
    execute(
        mint_authorised_action(auth),
        decision,
        cand,
        val,
        env,
        ledger,
        NOW + 1000,
        store=store,
    )
    late = execute(
        mint_authorised_action(auth),
        decision,
        cand,
        val,
        env,
        ledger,
        scheduled_at,
        store=store,
    )
    assert late.execution_stage == ExecutionStage.CANCELLED
    assert "AUTHORIZATION_EXPIRED" in late.failure_reason
