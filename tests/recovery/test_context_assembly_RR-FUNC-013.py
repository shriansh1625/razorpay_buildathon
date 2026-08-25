"""RR-FUNC-013 — context assembly completeness."""

from revive.domain.enums import RiskClass
from revive.recovery.context import assemble_context
from revive.recovery.sentinel import detect
from tests.recovery.helpers import view

NOW = 3_600_000_000


def _payment_opportunity():
    world = view(
        instruments=(
            {
                "instrument_id": "pi_1",
                "customer_id": "cust_1",
                "method_type": "CARD",
                "network_band": "VISA",
                "expiry_state": "VALID",
                "block_state": "ACTIVE",
                "failure_count": 1,
            },
        ),
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
                "reason_text": None,
                "attempted_at_micros": 1000,
            },
            {
                "transaction_id": "txn_ok",
                "order_id": "ord_old",
                "customer_id": "cust_1",
                "amount_paise": 5000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "SUCCESS",
                "reason_code": None,
                "reason_text": None,
                "attempted_at_micros": 500,
            },
        ),
    )
    return detect(world, NOW).opportunities[0], world


def test_customer_context_fields_RR_FUNC_013():
    opp, world = _payment_opportunity()
    ctx = assemble_context(opp, world, NOW)
    assert ctx.customer.customer_id == "cust_1"
    assert ctx.customer.segment == "NEW"
    assert ctx.customer.tenure_band == "LT_3M"
    assert ctx.customer.successful_payment_count == 1
    assert ctx.customer.failed_payment_count == 1
    assert ctx.customer.success_rate == 0.5
    assert ctx.temporal.time_since_event_micros is not None
    assert ctx.temporal.merchant_local_hour is not None
    assert ctx.fatigue.fatigue_band in {"LOW", "MED", "HIGH"}


def test_payment_instrument_context_RR_FUNC_015():
    opp, world = _payment_opportunity()
    ctx = assemble_context(opp, world, NOW)
    assert ctx.instrument is not None
    assert ctx.instrument.method_type == "CARD"
    assert ctx.instrument.expiry_state == "VALID"
    assert ctx.payment is not None
    assert ctx.payment.reason_code == "INSUFFICIENT_FUNDS"


def test_checkout_context_assembly():
    world = view(
        checkout_sessions=(
            {
                "session_id": "chk_1",
                "customer_id": "cust_1",
                "merchant_id": "mer_1",
                "cart_value_paise": 12000,
                "stage_reached": "PAYMENT_INIT",
                "method_selected": "UPI",
                "abandoned_at_micros": 5000,
                "created_at_micros": 1000,
            },
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    ctx = assemble_context(opp, world, NOW)
    assert ctx.checkout is not None
    assert ctx.checkout.payment_initiated is True
    assert ctx.checkout.cart_value_paise == 12000


def test_receivable_context_ageing():
    world = view(
        invoices=(
            {
                "invoice_id": "inv_1",
                "customer_id": "cust_1",
                "merchant_id": "mer_1",
                "issued_amount_paise": 10000,
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
    ctx = assemble_context(opp, world, NOW)
    assert ctx.receivable is not None
    assert ctx.receivable.ageing_days == 45
    assert ctx.receivable.ageing_bucket == "31-60"


def test_degradation_context_interpretation():
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
            "attempted_at_micros": NOW - 1000 - i,
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
    ctx = assemble_context(opp, world, NOW)
    assert ctx.degradation.degradation_flag is True
    assert ctx.degradation.observed_failure_rate is not None
    assert ctx.degradation.observed_failure_rate >= 0.6


def test_no_future_lookahead_in_context():
    opp, world = _payment_opportunity()
    future_world = view(
        instruments=world.instruments,
        orders=world.orders,
        transactions=world.transactions
        + (
            {
                "transaction_id": "txn_future",
                "order_id": "ord_f",
                "customer_id": "cust_1",
                "amount_paise": 99999,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "FAILED",
                "reason_code": "DECLINED",
                "reason_text": None,
                "attempted_at_micros": NOW + 1_000_000,
            },
        ),
    )
    ctx = assemble_context(opp, future_world, NOW)
    assert ctx.customer.failed_payment_count == 1
