"""M13.10 official freeze seal tests."""

from dataclasses import replace
from pathlib import Path

import pytest

from revive.benchmark.official.config import official_benchmark_config
from revive.benchmark.official.freeze import check_freeze_prerequisites
from revive.benchmark.official.freeze_constants import OFFICIAL_EPSILON_PAISE
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.benchmark.official.seal import seal_official_benchmark
from revive.config.policy_pack import default_draft_policy_pack, official_sealed_policy_pack


def test_draft_pack_rejected_for_official_config():
    pack = default_draft_policy_pack()
    with pytest.raises(ValueError, match="SEALED"):
        official_benchmark_config(policy_pack=pack)


def test_official_freeze_gate_complete():
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    freeze = check_freeze_prerequisites(config, policy_pack=pack)
    assert freeze.complete
    assert freeze.blocked_reasons == ()


def test_official_sealed_epsilon():
    pack = official_sealed_policy_pack()
    assert pack.epsilon_paise == OFFICIAL_EPSILON_PAISE
    assert pack.is_frozen_for_benchmark


def test_config_hash_stability():
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    h1 = official_benchmark_config_hash(config)
    h2 = official_benchmark_config_hash(config)
    assert h1 == h2
    assert len(h1) == 64


def test_config_hash_sensitive_to_epsilon():
    pack = official_sealed_policy_pack()
    base = official_benchmark_config(policy_pack=pack)
    h0 = official_benchmark_config_hash(base)
    other = replace(base, epsilon_paise=200)
    assert official_benchmark_config_hash(other) != h0


def test_config_hash_sensitive_to_horizon():
    pack = official_sealed_policy_pack()
    base = official_benchmark_config(policy_pack=pack)
    h0 = official_benchmark_config_hash(base)
    g = replace(base.generator_config, simulation_window_days=30)
    other = replace(base, generator_config=g, simulation_horizon_days=30)
    assert official_benchmark_config_hash(other) != h0


def test_seal_writes_manifest(tmp_path: Path):
    result = seal_official_benchmark(output_dir=tmp_path)
    assert result.freeze_complete
    assert (tmp_path / "freeze-manifest.json").exists()
    assert result.config_hash == (tmp_path / "config_hash.txt").read_text().strip()
