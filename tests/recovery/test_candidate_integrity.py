"""Oracle isolation, no value leakage, policy neutrality."""

import inspect

from revive.integrity import assert_decision_path_does_not_import_oracle
from revive.recovery.candidates import generate_candidates
from revive.recovery.candidates.generate import generate_candidates as generate_fn
from revive.recovery.diagnosis import understand
from revive.recovery.sentinel import detect
from tests.recovery.helpers import view

NOW = 3_600_000_000


def test_candidate_modules_do_not_import_oracle():
    assert_decision_path_does_not_import_oracle()


def test_no_enrv_or_prediction_fields():
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
    result = generate_candidates(opp, dx.observable_context, dx, NOW)
    blob = str(result.to_dict()).lower()
    forbidden = ("enrv", "uplift", "p_action", "p_natural", "recovery_probability", "optimal")
    for term in forbidden:
        assert term not in blob.replace("nominal_cost_paise", "")


def test_generate_source_has_no_ranking():
    source = inspect.getsource(generate_fn)
    for token in ("best_action", "selected_action", "optimal_action", "rank_candidates"):
        assert token not in source.lower()


def test_hidden_state_invariance():
    txn = {
        "transaction_id": "txn_1",
        "order_id": "ord_1",
        "customer_id": "cust_1",
        "amount_paise": 1000,
        "method_type": "UPI",
        "instrument_id": "pi_1",
        "attempt_seq": 1,
        "status": "FAILED",
        "reason_code": "INSUFFICIENT_FUNDS",
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
        opportunities=({"opportunity_id": "x", "intent_to_pay": 0.99},),
    )
    opp_a = detect(plain, NOW).opportunities[0]
    opp_b = detect(labeled, NOW).opportunities[0]
    dx_a = understand(opp_a, plain, NOW)
    dx_b = understand(opp_b, labeled, NOW)
    ca = generate_candidates(opp_a, dx_a.observable_context, dx_a, NOW)
    cb = generate_candidates(opp_b, dx_b.observable_context, dx_b, NOW)
    assert ca.to_dict() == cb.to_dict()


def test_policy_neutral_signature():
    params = inspect.signature(generate_fn).parameters
    assert "policy_id" not in params
    assert "baseline" not in params
