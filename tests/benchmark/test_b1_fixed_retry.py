"""B1 baseline tests."""

from revive.benchmark.config import B1_RETRY_SCHEDULE
from revive.benchmark.runner import run_baseline_cycle
from revive.benchmark.types import BaselinePolicyId, ObservableOpportunity
from revive.domain.enums import ActionCode, DecisionOutcome, RiskClass
from revive.simulation import generate_dataset
from revive.simulation.fixtures import tiny_config
from revive.simulation.observation import get_observable_state

MINUTE_MICROS = 60 * 1_000_000


def test_b1_schedule_is_documented_and_provisional():
    assert RiskClass.PAYMENT_FAILURE in B1_RETRY_SCHEDULE
    assert B1_RETRY_SCHEDULE[RiskClass.PAYMENT_FAILURE][0] == (0, ActionCode.A01)


def test_b1_selects_scheduled_retry_for_payment_failure():
    dataset = generate_dataset(tiny_config(seed=11))
    view = get_observable_state(dataset.world)
    opp = next(o for o in dataset.world.opportunities if o.risk_class == RiskClass.PAYMENT_FAILURE)
    now = opp.first_detected_at_micros + 5 * MINUTE_MICROS

    result = run_baseline_cycle(BaselinePolicyId.B1, view, cycle_id="cyc_1", now_micros=now)
    decision = next(d for d in result.decisions if d.opportunity_id == opp.opportunity_id)
    assert decision.action_code == ActionCode.A01
    assert decision.outcome == DecisionOutcome.SELECTED


def test_b1_waits_before_schedule_delay():
    opp = ObservableOpportunity(
        opportunity_id="opp_test",
        merchant_id="mer_1",
        customer_id="cust_1",
        risk_class=RiskClass.PAYMENT_FAILURE.value,
        value_at_risk_paise=5000,
        addressable=True,
        state="PRICED",
        first_detected_at_micros=0,
        recovery_window_expires_at_micros=10 * 24 * MINUTE_MICROS,
        attempt_seq=0,
        contacts_made=0,
    )
    from revive.benchmark.baselines.b1_fixed_retry import FixedRetryBaseline
    from revive.benchmark.config import default_baseline_environment_config
    from revive.benchmark.types import BaselineCycleContext

    baseline = FixedRetryBaseline()
    ctx = BaselineCycleContext(
        cycle_id="cyc",
        now_micros=10 * MINUTE_MICROS,
        epsilon_paise=0,
        contact_allowance_per_customer=5,
        retry_slots_per_cycle=10,
        message_capacity_per_cycle=10,
    )
    opp_wait = ObservableOpportunity(
        opportunity_id="opp_wait",
        merchant_id="mer_1",
        customer_id="cust_1",
        risk_class=RiskClass.PAYMENT_FAILURE.value,
        value_at_risk_paise=5000,
        addressable=True,
        state="PRICED",
        first_detected_at_micros=0,
        recovery_window_expires_at_micros=10 * 24 * MINUTE_MICROS,
        attempt_seq=1,
        contacts_made=0,
    )
    action, reason = baseline._scheduled_action(opp_wait, ctx)
    assert action == ActionCode.A00
    assert reason == "B1_WAITING_FOR_SCHEDULE"
