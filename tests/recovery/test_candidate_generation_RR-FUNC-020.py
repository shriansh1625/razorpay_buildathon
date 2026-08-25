"""RR-FUNC-020/021 — candidate enumeration and class-aware sets."""

from revive.domain.enums import ActionCode, CandidateAvailability
from revive.recovery.candidates import generate_candidates
from revive.recovery.diagnosis import understand
from revive.recovery.sentinel import detect
from tests.recovery.helpers import view

NOW = 3_600_000_000


def _pipeline(world):
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    return opp, dx, generate_candidates(opp, dx.observable_context, dx, NOW)


def test_minimum_candidate_count_RR_FUNC_020():
    world = view(
        instruments=(
            {
                "instrument_id": "pi_1",
                "customer_id": "cust_1",
                "method_type": "CARD",
                "network_band": "VISA",
                "expiry_state": "VALID",
                "block_state": "ACTIVE",
                "failure_count": 0,
            },
        ),
        orders=({"order_id": "ord_1", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 5000, "created_at_micros": 1, "status": "OPEN"},),
        transactions=(
            {
                "transaction_id": "txn_1",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 5000,
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
    opp, dx, result = _pipeline(world)
    assert opp.addressable
    assert len(result.candidates) >= 3
    codes = {c.action_code for c in result.candidates}
    assert ActionCode.A00 in codes
    real = [c for c in result.candidates if c.action_code != ActionCode.A00]
    assert len(real) >= 2


def test_no_action_is_always_present():
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
    _, _, result = _pipeline(world)
    no_action = next(c for c in result.candidates if c.action_code == ActionCode.A00)
    assert no_action.availability_status == CandidateAvailability.AVAILABLE


def test_class_aware_sets_RR_FUNC_021():
    insuf_world = view(
        orders=({"order_id": "ord_1", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 5000, "created_at_micros": 1, "status": "OPEN"},),
        transactions=(
            {
                "transaction_id": "txn_1",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 5000,
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
    expired_world = view(
        instruments=(
            {
                "instrument_id": "pi_1",
                "customer_id": "cust_1",
                "method_type": "CARD",
                "network_band": "VISA",
                "expiry_state": "EXPIRED",
                "block_state": "ACTIVE",
                "failure_count": 2,
            },
        ),
        orders=({"order_id": "ord_2", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 5000, "created_at_micros": 1, "status": "OPEN"},),
        transactions=(
            {
                "transaction_id": "txn_2",
                "order_id": "ord_2",
                "customer_id": "cust_1",
                "amount_paise": 5000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "FAILED",
                "reason_code": "EXPIRED_CARD",
                "reason_text": None,
                "attempted_at_micros": 1000,
            },
        ),
    )
    network_world = view(
        orders=({"order_id": "ord_3", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 5000, "created_at_micros": 1, "status": "OPEN"},),
        transactions=(
            {
                "transaction_id": "txn_3",
                "order_id": "ord_3",
                "customer_id": "cust_1",
                "amount_paise": 5000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "FAILED",
                "reason_code": "NETWORK_ERROR",
                "reason_text": None,
                "attempted_at_micros": 1000,
            },
        ),
    )
    _, _, insuf = _pipeline(insuf_world)
    _, _, expired = _pipeline(expired_world)
    _, _, network = _pipeline(network_world)

    insuf_codes = {c.action_code for c in insuf.candidates}
    expired_codes = {c.action_code for c in expired.candidates}
    assert insuf_codes != expired_codes

    assert ActionCode.A01 in insuf_codes
    assert ActionCode.A01 not in expired_codes
    assert ActionCode.A03 in expired_codes

    network_a01 = next((c for c in network.candidates if c.action_code == ActionCode.A01), None)
    assert network_a01 is not None
    assert network_a01.availability_status == CandidateAvailability.AVAILABLE


def test_immediate_retry_available_for_payment_failure():
    world = view(
        orders=({"order_id": "ord_1", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 2000, "created_at_micros": 1, "status": "OPEN"},),
        transactions=(
            {
                "transaction_id": "txn_1",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 2000,
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
    _, _, result = _pipeline(world)
    retry = next(c for c in result.candidates if c.action_code == ActionCode.A01)
    assert retry.availability_status == CandidateAvailability.AVAILABLE
    assert "retry_slots" in {r.resource_key for r in retry.resource_requirements}


def test_checkout_candidates_include_resume_link():
    world = view(
        checkout_sessions=(
            {
                "session_id": "chk_1",
                "customer_id": "cust_1",
                "merchant_id": "mer_1",
                "cart_value_paise": 8000,
                "stage_reached": "PAYMENT_INIT",
                "method_selected": "UPI",
                "abandoned_at_micros": 5000,
                "created_at_micros": 1000,
            },
        ),
    )
    _, _, result = _pipeline(world)
    codes = {c.action_code for c in result.candidates}
    assert ActionCode.A07 in codes


def test_non_addressable_only_no_action_or_impossible():
    world = view(
        checkout_sessions=(
            {
                "session_id": "chk_anon",
                "customer_id": None,
                "merchant_id": "mer_1",
                "cart_value_paise": 5000,
                "stage_reached": "CART",
                "method_selected": None,
                "abandoned_at_micros": 1000,
                "created_at_micros": 1,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    assert not opp.addressable
    dx = understand(opp, world, NOW)
    result = generate_candidates(opp, dx.observable_context, dx, NOW)
    no_action = next(c for c in result.candidates if c.action_code == ActionCode.A00)
    assert no_action.availability_status == CandidateAvailability.AVAILABLE
    others = [c for c in result.candidates if c.action_code != ActionCode.A00]
    assert all(
        c.availability_status == CandidateAvailability.IMPOSSIBLE for c in others
    ) or len(others) == 0
