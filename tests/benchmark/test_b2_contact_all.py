"""B2 baseline tests."""

from revive.benchmark.baselines.b2_contact_all import ContactAllBaseline
from revive.benchmark.config import default_baseline_environment_config
from revive.benchmark.runner import run_baseline_cycle
from revive.benchmark.types import BaselineCycleContext, BaselinePolicyId, ObservableOpportunity
from revive.domain.enums import DecisionOutcome, RiskClass
from revive.simulation import generate_dataset
from revive.simulation.fixtures import tiny_config
from revive.simulation.observation import get_observable_state

MINUTE_MICROS = 60 * 1_000_000


def test_b2_respects_global_message_capacity():
    env = default_baseline_environment_config()
    baseline = ContactAllBaseline()
    ctx = BaselineCycleContext(
        cycle_id="cyc",
        now_micros=MINUTE_MICROS,
        epsilon_paise=0,
        contact_allowance_per_customer=5,
        retry_slots_per_cycle=0,
        message_capacity_per_cycle=1,
    )
    opps = [
        ObservableOpportunity(
            opportunity_id=f"opp_{i}",
            merchant_id="mer_1",
            customer_id="cust_shared",
            risk_class=RiskClass.CHECKOUT_ABANDONMENT.value,
            value_at_risk_paise=5000,
            addressable=True,
            state="PRICED",
            first_detected_at_micros=0,
            recovery_window_expires_at_micros=10 * MINUTE_MICROS,
            attempt_seq=0,
            contacts_made=0,
        )
        for i in range(3)
    ]
    result = baseline.decide_cycle(opps, ctx, env, epsilon_paise=0)
    selected = [d for d in result.decisions if d.outcome == DecisionOutcome.SELECTED]
    deferred = [d for d in result.decisions if d.outcome == DecisionOutcome.DEFERRED]
    assert len(selected) == 1
    assert len(deferred) == 2


def test_b2_deterministic_order_by_opportunity_id():
    dataset = generate_dataset(tiny_config(seed=15))
    view = get_observable_state(dataset.world)
    now = max(o.first_detected_at_micros for o in dataset.world.opportunities) + 1
    a = run_baseline_cycle(BaselinePolicyId.B2, view, cycle_id="cyc_1", now_micros=now)
    b = run_baseline_cycle(BaselinePolicyId.B2, view, cycle_id="cyc_1", now_micros=now)
    assert a.to_trace() == b.to_trace()
