"""Feasibility layers, policy, capacity, and approval tests."""

from revive.domain.enums import ActionCode, CandidateAvailability
from revive.recovery.candidates import CandidateCapacityContext, generate_candidates
from revive.recovery.candidates.config import CandidateConfig
from revive.recovery.diagnosis import understand
from revive.recovery.sentinel import detect
from tests.recovery.helpers import view

NOW = 3_600_000_000


def test_retry_exhausted_ineligible():
    world = view(
        orders=({"order_id": "ord_1", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 1000, "created_at_micros": 1, "status": "OPEN"},),
        transactions=(
            {
                "transaction_id": "txn_1",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 1000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 10,
                "status": "FAILED",
                "reason_code": "INSUFFICIENT_FUNDS",
                "reason_text": None,
                "attempted_at_micros": 1000,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    # attempt_seq on txn is 10; detect copies from transaction
    assert opp.attempt_seq == 10
    dx = understand(opp, world, NOW)
    cfg = CandidateConfig(max_retry_attempts=3)
    result = generate_candidates(
        opp, dx.observable_context, dx, NOW, config=cfg
    )
    retry = next(c for c in result.candidates if c.action_code == ActionCode.A01)
    assert retry.availability_status == CandidateAvailability.INELIGIBLE
    assert "MAX_RETRIES_REACHED" in retry.reason_codes


def test_contact_window_closed_ineligible():
    # NOW maps to hour ~10 in fixture timezone; use config with closed window.
    world = view(
        orders=({"order_id": "ord_1", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 1000, "created_at_micros": 1, "status": "OPEN"},),
        transactions=(
            {
                "transaction_id": "txn_1",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 1000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "FAILED",
                "reason_code": "INSUFFICIENT_FUNDS",
                "reason_text": None,
                "attempted_at_micros": 1000,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    cfg = CandidateConfig(comm_window_start_hour=20, comm_window_end_hour=22)
    result = generate_candidates(opp, dx.observable_context, dx, NOW, config=cfg)
    reminder = next(c for c in result.candidates if c.action_code == ActionCode.A05)
    assert reminder.availability_status == CandidateAvailability.INELIGIBLE
    assert "CONTACT_WINDOW_CLOSED" in reminder.reason_codes


def test_capacity_exhausted_temporarily_unavailable():
    world = view(
        orders=({"order_id": "ord_1", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 1000, "created_at_micros": 1, "status": "OPEN"},),
        transactions=(
            {
                "transaction_id": "txn_1",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 1000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "FAILED",
                "reason_code": "INSUFFICIENT_FUNDS",
                "reason_text": None,
                "attempted_at_micros": 1000,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    capacity = CandidateCapacityContext(retry_slots_remaining=0, message_capacity_remaining=0)
    result = generate_candidates(
        opp,
        dx.observable_context,
        dx,
        NOW,
        capacity=capacity,
    )
    retry = next(c for c in result.candidates if c.action_code == ActionCode.A01)
    assert retry.availability_status == CandidateAvailability.TEMPORARILY_UNAVAILABLE
    assert "RETRY_CAPACITY_EXHAUSTED" in retry.reason_codes


def test_high_value_approval_required():
    world = view(
        orders=({"order_id": "ord_1", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 100_000, "created_at_micros": 1, "status": "OPEN"},),
        transactions=(
            {
                "transaction_id": "txn_1",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 100_000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "FAILED",
                "reason_code": "INSUFFICIENT_FUNDS",
                "reason_text": None,
                "attempted_at_micros": 1000,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    result = generate_candidates(opp, dx.observable_context, dx, NOW)
    human = next((c for c in result.candidates if c.action_code == ActionCode.A13), None)
    assert human is not None
    assert human.approval_required


def test_receivable_early_overdue_candidates():
    world = view(
        invoices=(
            {
                "invoice_id": "inv_1",
                "customer_id": "cust_1",
                "merchant_id": "mer_1",
                "issued_amount_paise": 20000,
                "paid_amount_paise": 0,
                "credited_amount_paise": 0,
                "written_off_amount_paise": 0,
                "disputed_amount_paise": 0,
                "due_at_micros": 1,
                "terms_days": 30,
                "state": "OVERDUE",
                "ageing_days": 10,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    result = generate_candidates(opp, dx.observable_context, dx, NOW)
    codes = {c.action_code for c in result.candidates}
    assert ActionCode.A05 in codes


def test_deterministic_candidate_ids():
    world = view(
        orders=({"order_id": "ord_1", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 1000, "created_at_micros": 1, "status": "OPEN"},),
        transactions=(
            {
                "transaction_id": "txn_1",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 1000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "FAILED",
                "reason_code": "INSUFFICIENT_FUNDS",
                "reason_text": None,
                "attempted_at_micros": 1000,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    a = generate_candidates(opp, dx.observable_context, dx, NOW)
    b = generate_candidates(opp, dx.observable_context, dx, NOW)
    assert [c.candidate_id for c in a.candidates] == [c.candidate_id for c in b.candidates]
