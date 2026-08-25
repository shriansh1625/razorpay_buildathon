"""RR-FUNC-010/011/012 — diagnosis completeness and taxonomy."""

from revive.domain.enums import CauseCode, ConfidenceBand, RiskClass
from revive.recovery.diagnosis import diagnose, map_raw_reason, understand
from revive.recovery.diagnosis.mapping import RAW_REASON_TO_CAUSE
from revive.recovery.sentinel import detect
from tests.recovery.helpers import view

NOW = 3_600_000_000


def test_taxonomy_mapping_is_pure_function_RR_FUNC_011():
    assert map_raw_reason("INSUFFICIENT_FUNDS") == CauseCode.INSUFFICIENT_FUNDS
    assert map_raw_reason("UNKNOWN_CODE_XYZ") == CauseCode.UNCLASSIFIED
    assert map_raw_reason(None) == CauseCode.UNCLASSIFIED
    for code in RAW_REASON_TO_CAUSE:
        mapped = map_raw_reason(code)
        assert isinstance(mapped, CauseCode)


def test_payment_degradation_diagnosis_example():
    txns = tuple(
        {
            "transaction_id": f"txn_{i}",
            "order_id": f"ord_{i}",
            "customer_id": "cust_1",
            "amount_paise": 1000,
            "method_type": "CARD",
            "instrument_id": "pi_1",
            "attempt_seq": 1,
            "status": "FAILED",
            "reason_code": "ISSUER_DOWN",
            "reason_text": None,
            "attempted_at_micros": NOW - 2000 - i,
        }
        for i in range(4)
    )
    orders = tuple(
        {
            "order_id": f"ord_{i}",
            "customer_id": "cust_1",
            "merchant_id": "mer_1",
            "amount_paise": 1000,
            "created_at_micros": 1,
            "status": "OPEN",
        }
        for i in range(4)
    )
    world = view(transactions=txns, orders=orders)
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    assert dx.ranked_causes[0].cause_code == CauseCode.ISSUER_DOWNTIME
    assert dx.ranked_causes[0].confidence_band in {ConfidenceBand.MED, ConfidenceBand.HIGH}
    assert len(dx.ranked_causes[0].evidence_refs) >= 1
    assert "degradation_signal" in dx.provenance


def test_customer_specific_failure_diagnosis():
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
                "transaction_id": "txn_ok1",
                "order_id": "ord_a",
                "customer_id": "cust_1",
                "amount_paise": 1000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "SUCCESS",
                "reason_code": None,
                "reason_text": None,
                "attempted_at_micros": 100,
            },
            {
                "transaction_id": "txn_ok2",
                "order_id": "ord_b",
                "customer_id": "cust_1",
                "amount_paise": 1000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "SUCCESS",
                "reason_code": None,
                "reason_text": None,
                "attempted_at_micros": 200,
            },
            {
                "transaction_id": "txn_fail",
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
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    top = dx.ranked_causes[0]
    assert top.cause_code == CauseCode.INSUFFICIENT_FUNDS
    assert top.confidence_band == ConfidenceBand.HIGH


def test_checkout_friction_diagnosis():
    world = view(
        checkout_sessions=(
            {
                "session_id": "chk_1",
                "customer_id": "cust_1",
                "merchant_id": "mer_1",
                "cart_value_paise": 5000,
                "stage_reached": "CART",
                "method_selected": None,
                "abandoned_at_micros": 5000,
                "created_at_micros": 1000,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    assert dx.ranked_causes[0].cause_code == CauseCode.CHECKOUT_STEP_FRICTION


def test_subscription_lifecycle_diagnosis():
    world = view(
        subscriptions=(
            {
                "subscription_id": "sub_1",
                "customer_id": "cust_1",
                "mandate_id": "man_1",
                "cycle_amount_paise": 99900,
                "cycle_number": 4,
                "next_charge_at_micros": 50,
                "state": "PAST_DUE",
            },
        ),
        mandates=(
            {
                "mandate_id": "man_1",
                "customer_id": "cust_1",
                "instrument_id": "pi_1",
                "state": "REVOKED",
                "expires_at_micros": NOW + 1_000_000,
                "max_amount_paise": 100000,
                "presented_count": 3,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    assert any(rc.cause_code == CauseCode.MANDATE_REVOKED for rc in dx.ranked_causes)


def test_receivable_ageing_diagnosis():
    world = view(
        invoices=(
            {
                "invoice_id": "inv_1",
                "customer_id": "cust_1",
                "merchant_id": "mer_1",
                "issued_amount_paise": 50000,
                "paid_amount_paise": 0,
                "credited_amount_paise": 0,
                "written_off_amount_paise": 0,
                "disputed_amount_paise": 0,
                "due_at_micros": 1,
                "terms_days": 30,
                "state": "OVERDUE",
                "ageing_days": 45,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    assert dx.ranked_causes[0].cause_code == CauseCode.BUYER_CASHFLOW_CONSTRAINT


def test_ambiguous_insufficient_evidence():
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
                "reason_code": "MYSTERY_CODE",
                "reason_text": None,
                "attempted_at_micros": 1000,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    assert dx.unclassified or any(rc.cause_code == CauseCode.UNCLASSIFIED for rc in dx.ranked_causes)


def test_no_proven_language_RR_FUNC_012():
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
    assert dx.contains_forbidden_vocabulary() == []


def test_diagnosis_is_action_agnostic():
    import inspect

    from revive.recovery.diagnosis.diagnose import diagnose as diagnose_fn

    source = inspect.getsource(diagnose_fn)
    for token in ("ActionCode", "A01", "A02", "enrv", "retry", "whatsapp"):
        assert token.lower() not in source.lower()


def test_diagnosis_has_no_numeric_confidence():
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
    blob = dx.to_dict()
    assert "confidence" not in str(blob).replace("confidence_band", "")
