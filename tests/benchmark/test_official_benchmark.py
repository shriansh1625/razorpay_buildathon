"""M13 official benchmark tests."""

from pathlib import Path

import pytest

from revive.benchmark.official.config import (
    BenchmarkMode,
    development_benchmark_config,
    official_benchmark_config,
)
from revive.benchmark.official.freeze import check_freeze_prerequisites
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.benchmark.official.policies import ALL_BENCHMARK_POLICIES
from revive.benchmark.official.reproduce import reproduce_benchmark
from revive.benchmark.official.runner import execute_benchmark
from revive.benchmark.official.world import generate_shared_world
from revive.config.policy_pack import default_draft_policy_pack, official_sealed_policy_pack
from revive.integrity import (
    assert_baseline_modules_do_not_import_oracle,
    assert_decision_path_does_not_import_oracle,
)
from revive.simulation.fixtures import tiny_config
from revive.simulation.types import GenerationProfile


def test_official_freeze_gate_blocked_for_draft():
    pack = default_draft_policy_pack()
    with pytest.raises(ValueError, match="SEALED"):
        official_benchmark_config(policy_pack=pack)


def test_official_freeze_gate_complete():
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    freeze = check_freeze_prerequisites(config, policy_pack=pack)
    assert freeze.complete


def test_config_hash_deterministic():
    pack = default_draft_policy_pack()
    config = development_benchmark_config(policy_pack=pack)
    h1 = official_benchmark_config_hash(config)
    h2 = official_benchmark_config_hash(config)
    assert h1 == h2
    assert len(h1) == 64


def test_same_world_same_dataset_hash():
    cfg = tiny_config(seed=7, profile=GenerationProfile.BALANCED)
    w1 = generate_shared_world(cfg)
    w2 = generate_shared_world(cfg)
    assert w1.dataset_hash == w2.dataset_hash
    assert w1.seed == w2.seed


def test_all_policies_on_shared_world():
    pack = default_draft_policy_pack()
    bundle = generate_shared_world(tiny_config(seed=8))
    from revive.benchmark.official.policy_runner import run_policy_on_world
    from revive.benchmark.official.policies import BenchmarkPolicyId

    hashes = []
    for policy in ALL_BENCHMARK_POLICIES:
        metrics = run_policy_on_world(bundle, policy, pack)
        hashes.append((policy.value, metrics.net_recovered_paise))
    assert len(hashes) == 5


def test_oracle_isolation_benchmark_modules():
    assert_decision_path_does_not_import_oracle()
    assert_baseline_modules_do_not_import_oracle()


def test_development_benchmark_executes(tmp_path: Path):
    result = execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=tmp_path / "dev_bench",
    )
    assert not result.blocked
    assert result.validation_status in {"BENCHMARK_VALID", "BENCHMARK_INVALID"}
    assert len(result.aggregate.per_run) == 5
    assert (tmp_path / "dev_bench" / "config_hash.txt").exists()
    assert (tmp_path / "dev_bench" / "aggregate.json").exists()


def test_official_mode_gate_open_without_execution():
    """Freeze complete — gate allows official run; not executed in this test."""
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    freeze = check_freeze_prerequisites(config, policy_pack=pack)
    assert freeze.complete


def test_m10_paired_against_b0():
    result = execute_benchmark(mode=BenchmarkMode.DEVELOPMENT)
    b0_runs = [m for m in result.aggregate.per_run if m.policy_id == "B0"]
    revive_runs = [m for m in result.aggregate.per_run if m.policy_id == "REVIVE"]
    assert b0_runs[0].m10_incremental_net_paise == 0
    assert revive_runs[0].m10_incremental_net_paise is not None


def test_reproduction_development():
    rep = reproduce_benchmark(mode=BenchmarkMode.DEVELOPMENT)
    assert rep.identical
    assert rep.first_hash == rep.second_hash


def test_revive_vs_b3_analysis():
    result = execute_benchmark(mode=BenchmarkMode.DEVELOPMENT)
    assert "cells_compared" in result.aggregate.revive_vs_b3 or result.aggregate.revive_vs_b3 == {}
