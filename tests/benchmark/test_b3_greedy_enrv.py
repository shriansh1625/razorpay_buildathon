"""B3 baseline tests."""

from revive.benchmark.runner import run_baseline_cycle
from revive.benchmark.types import BaselinePolicyId
from revive.domain.enums import ActionCode, DecisionOutcome
from revive.simulation import generate_dataset
from revive.simulation.fixtures import tiny_config
from revive.simulation.observation import get_observable_state


def test_b3_ranks_by_enrv_not_opportunity_id():
    dataset = generate_dataset(tiny_config(seed=21))
    view = get_observable_state(dataset.world)
    now = max(o.first_detected_at_micros for o in dataset.world.opportunities) + 1
    result = run_baseline_cycle(BaselinePolicyId.B3, view, cycle_id="cyc_1", now_micros=now)
    ranked = sorted(
        [d for d in result.decisions if d.rank is not None and d.enrv_estimate_paise],
        key=lambda d: d.rank,
    )
    if len(ranked) >= 2:
        assert ranked[0].rank == 1
        assert ranked[0].enrv_estimate_paise >= ranked[1].enrv_estimate_paise


def test_b3_no_action_when_below_epsilon():
    from revive.config import PolicyPack, PolicyPackStatus

    dataset = generate_dataset(tiny_config(seed=22))
    view = get_observable_state(dataset.world)
    now = max(o.first_detected_at_micros for o in dataset.world.opportunities) + 1
    high_epsilon = PolicyPack(
        version="pol_test_high_eps",
        status=PolicyPackStatus.DRAFT,
        epsilon_paise=10_000_000,
    )
    result = run_baseline_cycle(
        BaselinePolicyId.B3,
        view,
        cycle_id="cyc_1",
        now_micros=now,
        policy_pack=high_epsilon,
    )
    assert all(d.action_code == ActionCode.A00 for d in result.decisions)
    assert all(d.outcome == DecisionOutcome.NO_ACTION for d in result.decisions)
