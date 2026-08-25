"""M13.19 preflight mode tests."""

from revive.benchmark.official.config import BenchmarkMode, preflight_benchmark_config
from revive.benchmark.official.freeze import check_freeze_prerequisites
from revive.benchmark.official.hash import frozen_experiment_reference_hash, official_benchmark_config_hash
from revive.config.policy_pack import official_sealed_policy_pack


def test_preflight_uses_sealed_official_experiment():
    pack = official_sealed_policy_pack()
    pre = preflight_benchmark_config(policy_pack=pack)
    full = __import__(
        "revive.benchmark.official.config", fromlist=["official_benchmark_config"]
    ).official_benchmark_config(policy_pack=pack)

    assert pre.policy_pack_version == "pol_m13_official_v1"
    assert pre.epsilon_paise == 100
    assert pre.generator_config.opportunity_count == 500
    assert pre.generator_config.customer_count == 100
    assert pre.simulation_horizon_days == 21
    assert pre.seed_set == (1,)
    assert len(pre.profile_set) == 6
    assert frozen_experiment_reference_hash(pre) == frozen_experiment_reference_hash(full)
    assert official_benchmark_config_hash(pre) != official_benchmark_config_hash(full)


def test_preflight_mode_enum():
    assert BenchmarkMode.PREFLIGHT.value == "PREFLIGHT"


def test_preflight_freeze_allows_single_seed():
    pack = official_sealed_policy_pack()
    config = preflight_benchmark_config(policy_pack=pack)
    freeze = check_freeze_prerequisites(config, policy_pack=pack, preflight=True)
    assert freeze.complete is True
    assert freeze.blocked_reasons == ()
