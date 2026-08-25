"""Idempotency and resource consumption tests."""

from revive.domain.enums import ActionCode
from revive.decision.ledger import ReservationLedger
from revive.decision.models import ResourceReservation, ReservationStatus
from revive.execution import execute_authorization
from revive.execution.models import ExecutionStage
from revive.execution.store import ExecutionStore
from revive.audit import AuditJournal

from tests.execution.helpers import (
    authorize_selected,
    fixture_partition,
    NOW,
)
from revive.execution import ExecutionEnvironment


def _setup(action=ActionCode.A01):
    auth, decision, cand, val = authorize_selected(action)
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
    env = ExecutionEnvironment(
        oracle_partition=fixture_partition(),
        value_at_risk_paise=5000,
        customer_id="cust_var",
    )
    return auth, decision, cand, val, ledger, env


def test_idempotent_execution():
    auth, decision, cand, val, ledger, env = _setup()
    store = ExecutionStore()
    audit = AuditJournal()
    t = NOW + 2000
    r1 = execute_authorization(
        auth, decision, cand, val, env, ledger, t, store=store, audit=audit,
    )
    r2 = execute_authorization(
        auth, decision, cand, val, env, ledger, t, store=store, audit=audit,
    )
    assert r1.execution_id == r2.execution_id
    assert r2.duplicate is True
    assert ledger.is_committed(decision.decision_id)
    assert len(audit.records()) == 2  # intent + result once; second is duplicate read


def test_resource_consumed_once():
    auth, decision, cand, val, ledger, env = _setup()
    store = ExecutionStore()
    t = NOW + 2000
    execute_authorization(auth, decision, cand, val, env, ledger, t, store=store)
    assert ledger.is_committed(decision.decision_id)
    assert not ledger.has_active(decision.decision_id)


def test_invalid_reservation_blocks():
    auth, decision, cand, val, _, env = _setup()
    result = execute_authorization(
        auth, decision, cand, val, env, ReservationLedger(), NOW + 2000,
    )
    assert result.execution_stage == ExecutionStage.CANCELLED
    assert "RESERVATION_INVALID" in result.failure_reason


def test_predicted_cost_preserved():
    auth, decision, cand, val, ledger, env = _setup()
    val = __import__(
        "tests.execution.helpers", fromlist=["valuation_for"]
    ).valuation_for(cost=250)
    result = execute_authorization(
        auth, decision, cand, val, env, ledger, NOW + 2000,
    )
    assert result.predicted_cost_paise == 250
    assert val.cost_paise == 250
