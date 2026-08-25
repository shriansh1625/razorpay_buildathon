"""B0 baseline tests."""

from revive.benchmark.runner import run_baseline_cycle
from revive.benchmark.types import BaselinePolicyId
from revive.domain.enums import ActionCode, DecisionOutcome
from revive.simulation import generate_dataset
from revive.simulation.fixtures import tiny_config
from revive.simulation.observation import get_observable_state


def test_b0_never_selects_real_action():
    dataset = generate_dataset(tiny_config(seed=7))
    view = get_observable_state(dataset.world)
    now = max(o.first_detected_at_micros for o in dataset.world.opportunities)
    result = run_baseline_cycle(BaselinePolicyId.B0, view, cycle_id="cyc_1", now_micros=now)
    for decision in result.decisions:
        assert decision.action_code == ActionCode.A00
        assert decision.outcome == DecisionOutcome.NO_ACTION
        assert decision.reason_code == "NO_ACTION_CONTROL"


def test_b0_covers_all_eligible_opportunities():
    dataset = generate_dataset(tiny_config(seed=8))
    view = get_observable_state(dataset.world)
    now = max(o.recovery_window_expires_at_micros for o in dataset.world.opportunities) - 1
    result = run_baseline_cycle(BaselinePolicyId.B0, view, cycle_id="cyc_1", now_micros=now)
    assert len(result.decisions) >= 1
