"""Cross-baseline fairness and integrity tests."""

from revive.benchmark.baselines import all_baselines
from revive.benchmark.runner import run_baseline_cycle
from revive.benchmark.types import BaselinePolicyId
from revive.integrity import (
    assert_baseline_modules_do_not_import_oracle,
    assert_decision_path_does_not_import_oracle,
)
from revive.simulation import generate_dataset
from revive.simulation.fixtures import tiny_config
from revive.simulation.observation import get_observable_state


def test_baselines_do_not_import_oracle():
    assert_baseline_modules_do_not_import_oracle()
    assert_decision_path_does_not_import_oracle()


def test_all_baselines_share_same_eligible_opportunity_set():
    dataset = generate_dataset(tiny_config(seed=30))
    view = get_observable_state(dataset.world)
    now = max(o.first_detected_at_micros for o in dataset.world.opportunities) + 1

    eligible_sets = []
    for policy in all_baselines():
        result = run_baseline_cycle(policy.policy_id, view, cycle_id="cyc_1", now_micros=now)
        eligible_sets.append({d.opportunity_id for d in result.decisions})

    assert eligible_sets[0] == eligible_sets[1] == eligible_sets[2] == eligible_sets[3]


def test_baseline_reproducibility():
    dataset = generate_dataset(tiny_config(seed=31))
    view = get_observable_state(dataset.world)
    now = max(o.first_detected_at_micros for o in dataset.world.opportunities) + 1

    for policy_id in BaselinePolicyId:
        a = run_baseline_cycle(policy_id, view, cycle_id="cyc_1", now_micros=now)
        b = run_baseline_cycle(policy_id, view, cycle_id="cyc_1", now_micros=now)
        assert a.to_trace() == b.to_trace()


def test_four_baselines_implemented():
    assert len(all_baselines()) == 4
