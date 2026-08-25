"""Oracle isolation, determinism, no ranking — M7 integrity."""

import inspect

from revive.integrity import assert_decision_path_does_not_import_oracle
from revive.recovery.candidates import generate_candidates
from revive.recovery.diagnosis import understand
from revive.recovery.sentinel import detect
from revive.recovery.valuation import price_candidates
from revive.recovery.valuation.price import price_candidates as price_fn
from tests.recovery.helpers import view

NOW = 3_600_000_000


def test_valuation_modules_do_not_import_oracle():
    assert_decision_path_does_not_import_oracle()


def test_no_ranking_in_price_module():
    source = inspect.getsource(price_fn)
    forbidden = ("best_action", "selected_action", "optimal_action", "sort_by_enrv", "rank_")
    for token in forbidden:
        assert token not in source.lower()


def test_hidden_state_invariance():
    txn = {
        "transaction_id": "txn_1",
        "order_id": "ord_1",
        "customer_id": "cust_1",
        "amount_paise": 10_000,
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
        "amount_paise": 10_000,
        "created_at_micros": 1,
        "status": "OPEN",
    }
    plain = view(transactions=(txn,), orders=(order,))
    labeled = view(
        transactions=(txn,),
        orders=(order,),
        opportunities=({"opportunity_id": "hidden", "intent_to_pay": 0.99},),
    )
    opp_a = detect(plain, NOW).opportunities[0]
    opp_b = detect(labeled, NOW).opportunities[0]
    dx_a = understand(opp_a, plain, NOW)
    dx_b = understand(opp_b, labeled, NOW)
    ca = generate_candidates(opp_a, dx_a.observable_context, dx_a, NOW)
    cb = generate_candidates(opp_b, dx_b.observable_context, dx_b, NOW)
    va = price_candidates(opp_a, dx_a.observable_context, dx_a, ca, NOW)
    vb = price_candidates(opp_b, dx_b.observable_context, dx_b, cb, NOW)
    assert va.to_dict() == vb.to_dict()


def test_future_leakage_invariance():
    txn = {
        "transaction_id": "txn_1",
        "order_id": "ord_1",
        "customer_id": "cust_1",
        "amount_paise": 20_000,
        "method_type": "CARD",
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
        "amount_paise": 20_000,
        "created_at_micros": 1,
        "status": "OPEN",
    }
    plain = view(transactions=(txn,), orders=(order,))
    future_outcome = view(
        transactions=(txn,),
        orders=(order,),
        opportunities=({"opportunity_id": "future", "will_recover_at_micros": NOW + 9_999_999},),
    )
    opp_a = detect(plain, NOW).opportunities[0]
    opp_b = detect(future_outcome, NOW).opportunities[0]
    dx_a = understand(opp_a, plain, NOW)
    dx_b = understand(opp_b, future_outcome, NOW)
    ca = generate_candidates(opp_a, dx_a.observable_context, dx_a, NOW)
    cb = generate_candidates(opp_b, dx_b.observable_context, dx_b, NOW)
    va = price_candidates(opp_a, dx_a.observable_context, dx_a, ca, NOW)
    vb = price_candidates(opp_b, dx_b.observable_context, dx_b, cb, NOW)
    assert va.to_dict() == vb.to_dict()


def test_determinism():
    world = view(
        orders=(
            {
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "merchant_id": "mer_1",
                "amount_paise": 15_000,
                "created_at_micros": 1,
                "status": "OPEN",
            },
        ),
        transactions=(
            {
                "transaction_id": "txn_1",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": 15_000,
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
    candidates = generate_candidates(opp, dx.observable_context, dx, NOW)
    a = price_candidates(opp, dx.observable_context, dx, candidates, NOW)
    b = price_candidates(opp, dx.observable_context, dx, candidates, NOW)
    assert a.to_dict() == b.to_dict()


def test_prediction_not_realized_outcome():
    from revive.recovery.valuation.models import CandidateValuation

    fields = {f.name for f in CandidateValuation.__dataclass_fields__.values()}
    assert "realized_outcome" not in fields
    assert "observed_recovery" not in fields
