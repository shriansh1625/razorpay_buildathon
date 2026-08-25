"""RR-FUNC-003/005 — dedupe, quarantine, conservation."""

from revive.domain.enums import NonAddressableReason, OpportunityState, RiskClass
from revive.recovery.sentinel import detect
from tests.recovery.helpers import view

NOW = 3_600_000_000  # 1 hour of virtual time — inside class recovery windows


def test_duplicate_failures_same_order_one_opportunity_RR_FUNC_003():
    world = view(
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
                "reason_code": "ISSUER_DOWN",
                "reason_text": None,
                "attempted_at_micros": 100,
            },
            {
                "transaction_id": "txn_2",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 5000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 2,
                "status": "FAILED",
                "reason_code": "ISSUER_DOWN",
                "reason_text": None,
                "attempted_at_micros": 200,
            },
        ),
    )
    result = detect(world, NOW)
    payment = [o for o in result.opportunities if o.risk_class == RiskClass.PAYMENT_FAILURE]
    assert len(payment) == 1
    assert payment[0].attempt_seq == 2
    assert payment[0].value_at_risk_paise == 5000
    assert result.metrics.dedupe_merges >= 1


def test_duplicate_signal_hash_quarantine_not_duplicate_opportunity():
    sig = {
        "signal_id": "sig_a",
        "signal_type": "PAYMENT_ATTEMPT_FAILED",
        "source_ref": "ord_1",
        "payload": {"amount_paise": 5000},
        "received_at_micros": 10,
        "occurred_at_micros": 10,
        "dedupe_hash": "same-hash",
    }
    dup = {**sig, "signal_id": "sig_b"}
    world = view(
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
                "reason_code": "DECLINED",
                "reason_text": None,
                "attempted_at_micros": 10,
            },
        ),
        signals=(sig, dup),
    )
    result = detect(world, NOW)
    assert len(result.opportunities) == 1


def test_malformed_signal_quarantined_RR_FUNC_005():
    world = view(
        signals=(
            {
                "signal_id": "bad",
                "signal_type": "NOT_A_REAL_TYPE",
                "source_ref": "x",
                "payload": {},
                "received_at_micros": 1,
                "occurred_at_micros": 1,
                "dedupe_hash": "h1",
            },
            {
                "signal_id": "neg",
                "signal_type": "PAYMENT_ATTEMPT_FAILED",
                "source_ref": "x",
                "payload": {"amount_paise": -5},
                "received_at_micros": 1,
                "occurred_at_micros": 1,
                "dedupe_hash": "h2",
            },
        ),
    )
    result = detect(world, NOW)
    assert result.opportunities == ()
    assert result.metrics.quarantine_count == 2
    reasons = {q.rejection_reason for q in result.quarantined}
    assert "UNKNOWN_SIGNAL_TYPE" in reasons
    assert "INVALID_AMOUNT" in reasons


def test_zero_amount_is_non_addressable():
    world = view(
        orders=({"order_id": "ord_z", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 0, "created_at_micros": 1, "status": "OPEN"},),
        transactions=(
            {
                "transaction_id": "txn_z",
                "order_id": "ord_z",
                "customer_id": "cust_1",
                "amount_paise": 0,
                "method_type": "UPI",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "FAILED",
                "reason_code": "DECLINED",
                "reason_text": None,
                "attempted_at_micros": 10,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    assert opp.addressable is False
    assert opp.state == OpportunityState.NOT_ADDRESSABLE
    assert opp.non_addressable_reason == NonAddressableReason.ZERO_AMOUNT


def test_anonymous_checkout_non_addressable_RR_FUNC_007():
    world = view(
        checkout_sessions=(
            {
                "session_id": "chk_anon",
                "customer_id": None,
                "merchant_id": "mer_1",
                "cart_value_paise": 8000,
                "stage_reached": "CHECKOUT",
                "method_selected": "UPI",
                "abandoned_at_micros": 1000,
                "created_at_micros": 1,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    assert opp.addressable is False
    assert opp.non_addressable_reason == NonAddressableReason.ANONYMOUS_CHECKOUT


def test_success_after_failure_does_not_keep_value():
    world = view(
        orders=({"order_id": "ord_1", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 5000, "created_at_micros": 1, "status": "PAID"},),
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
                "reason_code": "NETWORK_ERROR",
                "reason_text": None,
                "attempted_at_micros": 10,
            },
            {
                "transaction_id": "txn_2",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 5000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 2,
                "status": "SUCCESS",
                "reason_code": None,
                "reason_text": None,
                "attempted_at_micros": 20,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    assert opp.value_at_risk_paise == 0
    assert opp.addressable is False
    assert opp.non_addressable_reason == NonAddressableReason.ALREADY_SETTLED
