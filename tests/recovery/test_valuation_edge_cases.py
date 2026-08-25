"""Valuation edge cases — probabilities, costs, negative ENRV."""

from revive.domain.enums import ActionCode
from revive.recovery.valuation import ValuationConfig, default_valuation_config, price_candidates
from revive.recovery.candidates import generate_candidates
from revive.recovery.diagnosis import understand
from revive.recovery.sentinel import detect
from tests.recovery.helpers import view

NOW = 3_600_000_000


def _world(amount_paise: int = 100_000):
    return view(
        orders=(
            {
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "merchant_id": "mer_1",
                "amount_paise": amount_paise,
                "created_at_micros": 1,
                "status": "OPEN",
            },
        ),
        transactions=(
            {
                "transaction_id": "txn_1",
                "order_id": "ord_1",
                "customer_id": "cust_1",
                "amount_paise": amount_paise,
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


def _price(world, cfg=None):
    opp = detect(world, NOW).opportunities[0]
    dx = understand(opp, world, NOW)
    candidates = generate_candidates(opp, dx.observable_context, dx, NOW)
    return price_candidates(
        opp,
        dx.observable_context,
        dx,
        candidates,
        NOW,
        config=cfg,
    )


def test_negative_enrv_allowed():
    cfg = ValuationConfig(
        action_uplift_delta={"A00": 0.0, "A03": -0.2},
        incentive_tier_paise=default_valuation_config().incentive_tier_paise,
    )
    priced = _price(_world(), cfg)
    retry = next(v for v in priced.valuations if v.action_code == ActionCode.A03)
    assert retry.uplift < 0
    assert retry.enrv_paise < 0


def test_interval_contains_point():
    priced = _price(_world())
    for val in priced.valuations:
        assert val.enrv_lo_paise <= val.enrv_paise <= val.enrv_hi_paise


def test_very_small_and_large_value():
    small = _price(_world(100))
    large = _price(_world(10_000_000))
    assert all(isinstance(v.enrv_paise, int) for v in small.valuations)
    assert all(isinstance(v.enrv_paise, int) for v in large.valuations)


def test_model_version_recorded():
    priced = _price(_world())
    assert priced.valuation_version.startswith("0.7")
    assert priced.strategy_version
    for val in priced.valuations:
        assert val.strategy_version == priced.strategy_version
        assert val.valuation_id.startswith("val_")
