"""Oracle isolation, determinism, and adversarial diagnosis tests."""

from revive.integrity import assert_decision_path_does_not_import_oracle
from revive.recovery.diagnosis import understand
from revive.recovery.sentinel import detect
from revive.simulation import generate_dataset
from revive.simulation.fixtures import tiny_config
from revive.simulation.observation import get_observable_state
from tests.recovery.helpers import view

NOW = 3_600_000_000


def test_diagnosis_modules_do_not_import_oracle():
    assert_decision_path_does_not_import_oracle()


def test_diagnosis_has_no_hidden_keys():
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
    assert dx.hidden_keys() == []


def test_same_observable_different_hidden_state():
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
        "attempted_at_micros": 1000,
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
            {"cohort_ref": "hidden", "start_micros": 0, "end_micros": NOW, "severity": 0.99},
        ),
        opportunities=({"opportunity_id": "x", "intent_to_pay": 0.99, "fatigue_sensitivity": 0.1},),
    )
    opp_a = detect(plain, NOW).opportunities[0]
    opp_b = detect(labeled, NOW).opportunities[0]
    dx_a = understand(opp_a, plain, NOW)
    dx_b = understand(opp_b, labeled, NOW)
    assert [rc.cause_code for rc in dx_a.ranked_causes] == [
        rc.cause_code for rc in dx_b.ranked_causes
    ]
    assert dx_a.unclassified == dx_b.unclassified


def test_diagnosis_is_deterministic():
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
    a = understand(opp, world, NOW)
    b = understand(opp, world, NOW)
    assert a.to_dict() == b.to_dict()


def test_generator_opportunities_diagnosable():
    dataset = generate_dataset(tiny_config(seed=3))
    world = get_observable_state(dataset.world)
    now = max(o.first_detected_at_micros for o in dataset.world.opportunities) + 1
    detected = detect(world, now).opportunities
    assert detected
    for opp in detected[:5]:
        dx = understand(opp, world, now)
        assert dx.ranked_causes
        assert dx.diagnosis_id.startswith("dg_")


def test_contradicting_evidence_on_degradation_with_healthy_instrument():
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
        orders=tuple(
            {
                "order_id": f"ord_{i}",
                "customer_id": "cust_1",
                "merchant_id": "mer_1",
                "amount_paise": 1000,
                "created_at_micros": 1,
                "status": "OPEN",
            }
            for i in range(5)
        ),
        transactions=tuple(
            [
                {
                    "transaction_id": f"txn_ok_{i}",
                    "order_id": f"ord_old_{i}",
                    "customer_id": "cust_1",
                    "amount_paise": 1000,
                    "method_type": "CARD",
                    "instrument_id": "pi_1",
                    "attempt_seq": 1,
                    "status": "SUCCESS",
                    "reason_code": None,
                    "reason_text": None,
                    # Outside the 90-minute degradation window, inside customer history.
                    "attempted_at_micros": -2_000_000_000 - i,
                }
                for i in range(10)
            ]
            + [
                {
                    "transaction_id": f"txn_fail_{i}",
                    "order_id": f"ord_{i}",
                    "customer_id": "cust_1",
                    "amount_paise": 1000,
                    "method_type": "CARD",
                    "instrument_id": "pi_1",
                    "attempt_seq": 1,
                    "status": "FAILED",
                    "reason_code": "ISSUER_DOWN",
                    "reason_text": None,
                    "attempted_at_micros": NOW - 500 - i,
                }
                for i in range(4)
            ]
        ),
    )
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    degradation_cause = next(
        (rc for rc in dx.ranked_causes if rc.cause_code.value == "ISSUER_DOWNTIME"),
        None,
    )
    assert degradation_cause is not None
    assert "instrument_success_rate" in degradation_cause.contradicting_features or degradation_cause.confidence_band.value == "MED"


def test_policy_neutral_diagnosis_signature():
    import inspect

    from revive.recovery.diagnosis.diagnose import understand as understand_fn

    params = inspect.signature(understand_fn).parameters
    assert "policy_id" not in params
    assert "policy" not in params
