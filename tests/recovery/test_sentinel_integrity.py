"""Temporal, degradation, integrity, and reproducibility tests."""

from revive.domain.enums import RiskClass
from revive.integrity import assert_decision_path_does_not_import_oracle
from revive.recovery.sentinel import detect
from revive.simulation import generate_dataset
from revive.simulation.fixtures import tiny_config
from revive.simulation.observation import get_observable_state
from tests.recovery.helpers import view

NOW = 3_600_000_000  # 1 hour of virtual time — inside class recovery windows


def test_no_future_lookahead():
    world = view(
        transactions=(
            {
                "transaction_id": "txn_future",
                "order_id": "ord_f",
                "customer_id": "cust_1",
                "amount_paise": 1000,
                "method_type": "CARD",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "FAILED",
                "reason_code": "DECLINED",
                "reason_text": None,
                "attempted_at_micros": NOW + 1,
            },
        ),
        orders=({"order_id": "ord_f", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 1000, "created_at_micros": 1, "status": "OPEN"},),
    )
    assert detect(world, NOW).opportunities == ()


def test_late_event_with_past_occurred_at_is_processed():
    world = view(
        transactions=(
            {
                "transaction_id": "txn_late",
                "order_id": "ord_l",
                "customer_id": "cust_1",
                "amount_paise": 2000,
                "method_type": "UPI",
                "instrument_id": "pi_1",
                "attempt_seq": 1,
                "status": "FAILED",
                "reason_code": "NETWORK_ERROR",
                "reason_text": None,
                "attempted_at_micros": 50,
            },
        ),
        orders=({"order_id": "ord_l", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 2000, "created_at_micros": 1, "status": "OPEN"},),
        signals=(
            {
                "signal_id": "sig_late",
                "signal_type": "PAYMENT_ATTEMPT_FAILED",
                "source_ref": "ord_l",
                "payload": {"amount_paise": 2000},
                "received_at_micros": NOW,
                "occurred_at_micros": 50,
                "dedupe_hash": "late",
            },
        ),
    )
    opps = detect(world, NOW).opportunities
    assert len(opps) == 1


def test_degradation_flag_from_observable_failure_rate_RR_FUNC_006():
    txns = []
    for i in range(4):
        txns.append(
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
                "attempted_at_micros": NOW - 1000,
            }
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
    world = view(transactions=tuple(txns), orders=orders)
    result = detect(world, NOW)
    flagged = [o for o in result.opportunities if o.degradation_flag]
    assert len(flagged) == 4


def test_ignores_hidden_degradation_windows():
    txn = {
        "transaction_id": "txn_1",
        "order_id": "ord_1",
        "customer_id": "cust_1",
        "amount_paise": 1000,
        "method_type": "UPI",
        "instrument_id": "pi_1",
        "attempt_seq": 1,
        "status": "FAILED",
        "reason_code": "NETWORK_ERROR",
        "reason_text": None,
        "attempted_at_micros": 10,
    }
    order = {
        "order_id": "ord_1",
        "customer_id": "cust_1",
        "merchant_id": "mer_1",
        "amount_paise": 1000,
        "created_at_micros": 1,
        "status": "OPEN",
    }
    plain = view(transactions=(txn,), orders=(order,))
    labeled = view(
        transactions=(txn,),
        orders=(order,),
        degradation_windows=(
            {
                "cohort_ref": "hidden_cohort",
                "start_micros": 0,
                "end_micros": NOW,
                "severity": 0.99,
            },
        ),
        opportunities=(
            {"opportunity_id": "should_be_ignored", "intent_to_pay": 0.9},
        ),
    )
    a = detect(plain, NOW)
    b = detect(labeled, NOW)
    assert [o.opportunity_id for o in a.opportunities] == [o.opportunity_id for o in b.opportunities]
    assert all(not o.degradation_flag for o in b.opportunities)


def test_opportunity_has_no_hidden_keys():
    world = view(
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
                "reason_code": "DECLINED",
                "reason_text": None,
                "attempted_at_micros": 10,
            },
        ),
        orders=({"order_id": "ord_1", "customer_id": "cust_1", "merchant_id": "mer_1", "amount_paise": 1000, "created_at_micros": 1, "status": "OPEN"},),
    )
    opp = detect(world, NOW).opportunities[0]
    assert opp.hidden_keys() == []


def test_sentinel_modules_do_not_import_oracle():
    assert_decision_path_does_not_import_oracle()


def test_detection_is_deterministic():
    dataset = generate_dataset(tiny_config(seed=9))
    world = get_observable_state(dataset.world)
    now = max(o.first_detected_at_micros for o in dataset.world.opportunities) + 1
    a = detect(world, now)
    b = detect(world, now)
    assert [o.to_dict() for o in a.opportunities] == [o.to_dict() for o in b.opportunities]


def test_policy_neutral_signature_has_no_policy_id():
    import inspect

    from revive.recovery.sentinel.detect import detect as detect_fn

    params = inspect.signature(detect_fn).parameters
    assert "policy_id" not in params
    assert "policy" not in params
