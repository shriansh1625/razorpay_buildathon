"""Oracle isolation, determinism, future invariance."""

import inspect

from revive.integrity import assert_decision_path_does_not_import_oracle
from revive.allocation import allocate_portfolio, default_resource_state
from revive.allocation.allocate import allocate_portfolio as allocate_fn
from revive.domain.enums import ActionCode
from revive.recovery.candidates import generate_candidates
from revive.recovery.diagnosis import understand
from revive.recovery.sentinel import detect
from revive.recovery.valuation import price_candidates
from revive.allocation.resources import portfolio_item_from_valuation
from tests.recovery.helpers import view
from tests.allocation.helpers import make_item, priced
from revive.recovery.candidates.models import ResourceRequirement

NOW = 3_600_000_000


def test_allocation_modules_do_not_import_oracle():
    assert_decision_path_does_not_import_oracle()


def test_no_execution_in_allocate_module():
    source = inspect.getsource(allocate_fn)
    forbidden = ("execute", "oracle", "simulate_outcome", "realized")
    for token in forbidden:
        assert token not in source.lower()


def test_determinism():
    item = make_item(
        "opp_1",
        "cust_1",
        20_000,
        (
            priced(
                "opp_1",
                ActionCode.A03,
                4000,
                (ResourceRequirement("message_capacity", 1), ResourceRequirement("contact_allowance", 1)),
            ),
            priced("opp_1", ActionCode.A00, 0),
        ),
    )
    a = allocate_portfolio((item,), default_resource_state(), NOW, "cyc")
    b = allocate_portfolio((item,), default_resource_state(), NOW, "cyc")
    assert a.to_dict() == b.to_dict()
    assert a.allocation_hash == b.allocation_hash


def test_pipeline_allocation_invariance_hidden_state():
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
    hidden = view(
        transactions=(txn,),
        orders=(order,),
        opportunities=({"opportunity_id": "x", "intent_to_pay": 0.99},),
    )

    def run(world):
        opp = detect(world, NOW).opportunities[0]
        dx = understand(opp, world, NOW)
        candidates = generate_candidates(opp, dx.observable_context, dx, NOW)
        valuations = price_candidates(opp, dx.observable_context, dx, candidates, NOW)
        item = portfolio_item_from_valuation(
            opp.opportunity_id,
            opp.customer_id,
            opp.value_at_risk_paise,
            candidates.candidates,
            valuations.valuations,
        )
        return allocate_portfolio((item,), default_resource_state(), NOW, "cyc")

    assert run(plain).to_dict() == run(hidden).to_dict()
