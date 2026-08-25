"""M13.16 parallel worker PolicyPack propagation tests."""

from __future__ import annotations

import pickle

import pytest

from revive.benchmark.official.cells.parallel_worker import (
    config_to_worker_payload,
    reconstruct_worker_policy_pack,
    run_seed_profile_group,
)
from revive.benchmark.official.config import BenchmarkMode, official_benchmark_config
from revive.benchmark.official.freeze_constants import OFFICIAL_BENCHMARK_ID
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.config.policy_pack import (
    PolicyPackStatus,
    default_draft_policy_pack,
    official_sealed_policy_pack,
    policy_pack_from_frozen_payload,
    policy_pack_to_frozen_payload,
)


def test_sealed_policy_pack_roundtrip_via_pickle():
    pack = official_sealed_policy_pack()
    payload = policy_pack_to_frozen_payload(pack)
    wire = pickle.dumps(payload)
    restored_payload = pickle.loads(wire)
    restored = policy_pack_from_frozen_payload(
        restored_payload,
        expected_hash=pack.config_hash(),
        require_sealed=True,
    )
    assert restored.status == PolicyPackStatus.SEALED
    assert restored.version == "pol_m13_official_v1"
    assert restored.epsilon_paise == 100
    assert restored.config_hash() == pack.config_hash()


def test_official_mode_uppercase_does_not_downgrade_to_draft():
    """Regression: BenchmarkMode.OFFICIAL.value is 'OFFICIAL', not 'official'."""
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    payload = config_to_worker_payload(config, pack)
    payload = pickle.loads(pickle.dumps(payload))

    restored = reconstruct_worker_policy_pack(
        payload,
        mode=BenchmarkMode.OFFICIAL.value,
        expected_policy_pack_hash=pack.config_hash(),
    )
    assert restored.status == PolicyPackStatus.SEALED
    assert restored.version == pack.version
    assert restored.config_hash() == pack.config_hash()


def test_worker_payload_rejects_draft_for_official_benchmark():
    draft = default_draft_policy_pack()
    config = official_benchmark_config(policy_pack=official_sealed_policy_pack())
    payload = config_to_worker_payload(config, official_sealed_policy_pack())
    payload["policy_pack"] = policy_pack_to_frozen_payload(draft)

    with pytest.raises(ValueError, match="SEALED"):
        reconstruct_worker_policy_pack(
            payload,
            mode=BenchmarkMode.OFFICIAL.value,
            expected_policy_pack_hash=official_sealed_policy_pack().config_hash(),
        )


def test_worker_payload_rejects_policy_hash_mismatch():
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    payload = config_to_worker_payload(config, pack)

    with pytest.raises(ValueError, match="policy pack hash mismatch"):
        reconstruct_worker_policy_pack(
            payload,
            mode=BenchmarkMode.OFFICIAL.value,
            expected_policy_pack_hash="0" * 64,
        )


def test_worker_config_hash_invariant():
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    config_hash = official_benchmark_config_hash(config)
    payload = config_to_worker_payload(config, pack)

    restored_pack = reconstruct_worker_policy_pack(
        payload,
        mode=BenchmarkMode.OFFICIAL.value,
        expected_policy_pack_hash=pack.config_hash(),
    )
    from revive.benchmark.official.cells.parallel_worker import config_from_worker_payload

    worker_config = config_from_worker_payload(payload, policy_pack=restored_pack)
    assert official_benchmark_config_hash(worker_config) == config_hash
    assert worker_config.benchmark_id == OFFICIAL_BENCHMARK_ID
    assert worker_config.epsilon_paise == 100
    assert worker_config.simulation_horizon_days == 21


def test_preflight_worker_honours_profile_subset():
    from dataclasses import replace

    from revive.benchmark.official.cells.parallel_worker import config_from_worker_payload
    from revive.benchmark.official.config import preflight_benchmark_config
    from revive.simulation.types import GenerationProfile

    pack = official_sealed_policy_pack()
    config = replace(
        preflight_benchmark_config(policy_pack=pack, seeds=(1,)),
        profile_set=(GenerationProfile.BALANCED, GenerationProfile.HIGH_NATURAL),
    )
    config_hash = official_benchmark_config_hash(config)
    payload = config_to_worker_payload(config, pack)
    payload["mode"] = "DEVELOPMENT"

    restored_pack = reconstruct_worker_policy_pack(
        payload,
        mode="DEVELOPMENT",
        expected_policy_pack_hash=pack.config_hash(),
    )
    worker_config = config_from_worker_payload(payload, policy_pack=restored_pack)
    assert official_benchmark_config_hash(worker_config) == config_hash
    assert len(worker_config.profile_set) == 2
