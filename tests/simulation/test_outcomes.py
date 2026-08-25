"""Natural recovery and action variation tests."""

from revive.domain.enums import ActionCode
from revive.domain.timestamps import VirtualTimestamp
from revive.simulation import assert_dataset_valid, generate_dataset
from revive.simulation.distributions import compute_distributions
from revive.simulation.fixtures import (
    action_variation_fixture,
    natural_recovery_fixture,
    resolve_fixture_comparison,
    tiny_config,
)
from revive.simulation.oracle.resolve import resolve_outcome
from revive.simulation.types import GenerationProfile


def test_natural_recovery_exists_in_dataset():
    dataset = generate_dataset(
        __import__("revive.simulation.config", fromlist=["GeneratorConfig"]).GeneratorConfig(
            seed=77,
            profile=GenerationProfile.HIGH_NATURAL,
            opportunity_count=30,
            inject_signal_faults=False,
        )
    )
    dist = compute_distributions(dataset)
    assert dist.natural_recovery_rate > 0.1


def test_natural_recovery_fixture():
    row = natural_recovery_fixture()
    assert row is not None
    assert row.recovers_naturally


def test_different_actions_different_outcomes():
    partition = action_variation_fixture()
    a01_ok, a05_ok = resolve_fixture_comparison(partition)
    assert a01_ok and not a05_ok


def test_action_outcomes_vary_across_opportunities():
    dataset = generate_dataset(tiny_config(seed=5))
    assert_dataset_valid(dataset)
    successes = set()
    for row in dataset.oracle_partition.rows.values():
        for code, resp in row.per_action_response.items():
            if code != "A00":
                successes.add(resp.would_recover)
    assert True in successes and False in successes


def test_no_action_natural_recovery_resolve():
    partition = action_variation_fixture()
    partition.add_row(
        __import__(
            "revive.simulation.oracle._partition",
            fromlist=["OracleRow", "ActionResponse"],
        ).OracleRow(
            opportunity_id="opp_nat",
            customer_id="c1",
            recovers_naturally=True,
            natural_recovery_at_micros=30 * 60 * 1_000_000,
            natural_amount_paise=8000,
            per_action_response={"A00": __import__(
                "revive.simulation.oracle._partition", fromlist=["ActionResponse"]
            ).ActionResponse(False, 0, 0)},
            fatigue_curve={0: 1.0},
        )
    )
    result = resolve_outcome(
        partition,
        "opp_nat",
        ActionCode.A00,
        VirtualTimestamp(0),
        horizon_minutes=120,
        value_at_risk_paise=8000,
    )
    assert result.recovered_amount_paise == 8000
