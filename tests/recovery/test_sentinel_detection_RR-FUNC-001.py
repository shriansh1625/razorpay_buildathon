"""RR-FUNC-001/002 — class detection and valuation."""

from revive.domain.enums import OpportunityState, RiskClass
from revive.recovery.sentinel import detect
from tests.recovery.helpers import view

NOW = 3_600_000_000  # 1 hour of virtual time — inside class recovery windows
DAY = 24 * 60 * 60 * 1_000_000


def test_payment_failure_detection_RR_FUNC_001():
    world = view(
        orders=({"order_id": "ord_1", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 18000, "created_at_micros": 1, "status": "OPEN"},),
        transactions=(
            {
                "transaction_id": "txn_1",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 18000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "FAILED",
                "reason_code": "INSUFFICIENT_FUNDS",
                "reason_text": "declined",
                "attempted_at_micros": 1000,
            },
        ),
    )
    result = detect(world, NOW)
    opps = [o for o in result.opportunities if o.risk_class == RiskClass.PAYMENT_FAILURE]
    assert len(opps) == 1
    assert opps[0].value_at_risk_paise == 18000
    assert opps[0].state == OpportunityState.DETECTED
    assert opps[0].addressable
    assert opps[0].evidence.source_refs["order_id"] == "ord_1"


def test_checkout_abandonment_requires_started_checkout():
    landing = view(
        checkout_sessions=(
            {
                "session_id": "chk_land",
                "customer_id": "cust_1",
                "merchant_id": "mer_1",
                "cart_value_paise": 5000,
                "stage_reached": "LANDING",
                "method_selected": None,
                "abandoned_at_micros": 1000,
                "created_at_micros": 1,
            },
        ),
    )
    cart = view(
        checkout_sessions=(
            {
                "session_id": "chk_cart",
                "customer_id": "cust_1",
                "merchant_id": "mer_1",
                "cart_value_paise": 5000,
                "stage_reached": "CART",
                "method_selected": None,
                "abandoned_at_micros": 1000,
                "created_at_micros": 1,
            },
        ),
    )
    assert detect(landing, NOW).opportunities == ()
    opps = detect(cart, NOW).opportunities
    assert len(opps) == 1
    assert opps[0].risk_class == RiskClass.CHECKOUT_ABANDONMENT
    assert opps[0].value_at_risk_paise == 5000


def test_subscription_failure_detection():
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
    )
    opps = detect(world, NOW).opportunities
    assert len(opps) == 1
    assert opps[0].risk_class == RiskClass.SUBSCRIPTION_FAILURE
    assert opps[0].value_at_risk_paise == 99900
    assert opps[0].continuation_value_paise == 0


def test_receivable_overdue_uses_outstanding_not_issued():
    world = view(
        invoices=(
            {
                "invoice_id": "inv_1",
                "customer_id": "cust_1",
                "merchant_id": "mer_1",
                "issued_amount_paise": 10000,
                "paid_amount_paise": 2000,
                "credited_amount_paise": 1000,
                "written_off_amount_paise": 0,
                "disputed_amount_paise": 500,
                "due_at_micros": 1,
                "terms_days": 30,
                "state": "OVERDUE",
                "ageing_days": 20,
            },
        ),
    )
    opps = detect(world, NOW).opportunities
    assert len(opps) == 1
    assert opps[0].risk_class == RiskClass.RECEIVABLE_OVERDUE
    assert opps[0].value_at_risk_paise == 6500
    assert opps[0].ageing_bucket is not None
    assert opps[0].ageing_bucket.value == "16-30"


def test_mandate_health_near_expiry():
    world = view(
        mandates=(
            {
                "mandate_id": "man_h",
                "customer_id": "cust_1",
                "instrument_id": "pi_1",
                "state": "EXPIRING",
                "expires_at_micros": NOW + DAY,
                "max_amount_paise": 25000,
                "presented_count": 2,
            },
        ),
    )
    opps = detect(world, NOW).opportunities
    assert len(opps) == 1
    assert opps[0].risk_class == RiskClass.MANDATE_HEALTH
    assert opps[0].value_at_risk_paise == 25000


def test_recovery_window_assigned_RR_FUNC_004():
    world = view(
        transactions=(
            {
                "transaction_id": "txn_1",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 100,
                "method_type": "UPI",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "FAILED",
                "reason_code": "NETWORK_ERROR",
                "reason_text": None,
                "attempted_at_micros": 1000,
            },
        ),
        orders=({"order_id": "ord_1", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 100, "created_at_micros": 1, "status": "OPEN"},),
    )
    opp = detect(world, NOW).opportunities[0]
    assert opp.recovery_window_expires_at_micros > opp.first_detected_at_micros
