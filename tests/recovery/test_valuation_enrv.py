"""ENRV formula properties CF-1, CF-7, CF-8, CF-10."""

from revive.domain.enums import ActionCode
from revive.recovery.candidates import generate_candidates
from revive.recovery.diagnosis import understand
from revive.recovery.sentinel import detect
from revive.recovery.valuation import price_candidates
from tests.recovery.helpers import view

NOW = 3_600_000_000


def _pipeline(world):
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    candidates = generate_candidates(opp, dx.observable_context, dx, NOW)
    priced = price_candidates(
        opp,
        dx.observable_context,
        dx,
        candidates,
        NOW,
    )
    return opp, dx, candidates, priced


def _txn_world(**customer_overrides):
    txn = {
        "transaction_id": "txn_1",
        "order_id": "ord_1",
        "customer_id": "cust_1",
        "amount_paise": 50_000,
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
        "amount_paise": 50_000,
        "created_at_micros": 1,
        "status": "OPEN",
    }
    customer = {
        "customer_id": "cust_1",
        "customer_ref": "c1",
        "merchant_id": "mer_1",
        "segment": "NEW",
        "tenure_band": "LT_3M",
        "value_band": "MID",
        "prior_self_recovery_rate": 0.2,
    }
    customer.update(customer_overrides)
    return view(transactions=(txn,), orders=(order,), customers=(customer,))


def test_cf1_no_action_enrv_zero():
    _, _, _, priced = _pipeline(_txn_world())
    no_action = next(v for v in priced.valuations if v.action_code == ActionCode.A00)
    assert no_action.enrv_paise == 0
    assert no_action.gross_paise == 0
    assert no_action.cost_paise == 0
    assert no_action.expected_incentive_paise == 0
    assert no_action.fatigue_cost_paise == 0


def test_cf8_component_reconstruction():
    _, _, _, priced = _pipeline(_txn_world())
    for val in priced.valuations:
        assert val.component_sum_paise() == val.enrv_paise


def test_cf7_natural_recovery_dominance():
    """High natural recovery shrinks uplift — actions should not get full gross credit."""
    low_nat, _, _, priced_low = _pipeline(
        _txn_world(prior_self_recovery_rate=0.15)
    )
    high_nat, _, _, priced_high = _pipeline(
        _txn_world(prior_self_recovery_rate=0.92)
    )
    assert priced_high.p_natural > priced_low.p_natural
    retry_low = next(
        v for v in priced_low.valuations if v.action_code == ActionCode.A03
    )
    retry_high = next(
        v for v in priced_high.valuations if v.action_code == ActionCode.A03
    )
    assert retry_high.uplift < retry_low.uplift
    assert retry_high.gross_paise <= retry_low.gross_paise


def test_integer_money_components():
    _, _, _, priced = _pipeline(_txn_world())
    for val in priced.valuations:
        for field in (
            val.gross_paise,
            val.cost_paise,
            val.expected_incentive_paise,
            val.fatigue_cost_paise,
            val.enrv_paise,
            val.enrv_lo_paise,
            val.enrv_hi_paise,
        ):
            assert isinstance(field, int)


def test_multiple_candidates_valued():
    _, _, candidates, priced = _pipeline(_txn_world())
    assert len(priced.valuations) == len(candidates.candidates)
    assert len(priced.valuations) >= 3
