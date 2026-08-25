"""M13.15 parallel official benchmark runner tests."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from revive.benchmark.official.cells.parallel import validate_workers
from revive.benchmark.official.cells.plan import plan_benchmark_cells, plan_benchmark_groups
from revive.benchmark.official.cells.runner import run_cell_benchmark
from revive.benchmark.official.cells.store import aggregate_from_store
from revive.benchmark.official.config import development_benchmark_config
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.benchmark.official.runner import execute_benchmark
from revive.benchmark.official.config import BenchmarkMode
from revive.config.policy_pack import default_draft_policy_pack
from revive.simulation.types import GenerationProfile


def _dev_config(*, seeds=(1,), profiles=(GenerationProfile.BALANCED, GenerationProfile.HIGH_NATURAL)):
    pack = default_draft_policy_pack()
    return development_benchmark_config(policy_pack=pack, seeds=seeds, profiles=profiles)


def _aggregate_fingerprint(aggregate) -> str:
    payload = aggregate.to_dict()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def test_cli_workers_default():
    import argparse
    from revive.cli import main  # noqa: F401

    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args([])
    assert args.workers == 1


def test_validate_workers_bounds():
    cpu = os.cpu_count() or 1
    assert validate_workers(1) == 1
    assert validate_workers(cpu) == cpu
    with pytest.raises(ValueError, match=">= 1"):
        validate_workers(0)
    with pytest.raises(ValueError, match="<= CPU"):
        validate_workers(cpu + 1)


def test_plan_benchmark_groups_shared_world_unit():
    config = _dev_config()
    cells = plan_benchmark_cells(config)
    groups = plan_benchmark_groups(cells)
    assert len(groups) == 2
    assert groups[0].key == (1, "BALANCED")
    assert len(groups[0].cells) == 5
    assert [c.policy_id for c in groups[0].cells] == ["B0", "B1", "B2", "B3", "REVIVE"]


def test_workers_one_matches_legacy_metadata(tmp_path: Path):
    config = _dev_config(profiles=(GenerationProfile.BALANCED,))
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    root = tmp_path / "cells"
    result = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=root,
        workers=1,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    assert result.metadata.get("workers") == 1
    assert len(result.aggregate.per_run) == 5


def test_workers_two_matches_workers_one_fingerprints(tmp_path: Path):
    config = _dev_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)

    seq = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=tmp_path / "seq",
        workers=1,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    par = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=tmp_path / "par",
        workers=2,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )

    seq_fp = _aggregate_fingerprint(seq.aggregate)
    par_fp = _aggregate_fingerprint(par.aggregate)
    assert seq_fp == par_fp

    cells = plan_benchmark_cells(config)
    from revive.benchmark.official.cells.store import CellRecordContext, CellStore

    seq_store = CellStore(
        tmp_path / "seq",
        CellRecordContext(
            config_hash=config_hash,
            benchmark_version=config.benchmark_version,
            policy_pack_version=config.policy_pack_version,
            policy_pack_hash=config.policy_pack_hash,
            metric_version=config.metric_version,
        ),
    )
    par_store = CellStore(
        tmp_path / "par",
        CellRecordContext(
            config_hash=config_hash,
            benchmark_version=config.benchmark_version,
            policy_pack_version=config.policy_pack_version,
            policy_pack_hash=config.policy_pack_hash,
            metric_version=config.metric_version,
        ),
    )
    for cell in cells:
        seq_raw = seq_store.read_cell_raw(cell) or {}
        par_raw = par_store.read_cell_raw(cell) or {}
        assert seq_raw.get("metrics_checksum") == par_raw.get("metrics_checksum")


def test_parallel_resume_matches_uninterrupted(tmp_path: Path):
    config = _dev_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    cells = plan_benchmark_cells(config)
    stop_after = 5

    partial_root = tmp_path / "partial"
    run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=partial_root,
        workers=2,
        benchmark_mode="development",
        stop_after_cell=stop_after,
        progress=False,
        require_complete_aggregate=False,
    )
    resumed = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=partial_root,
        workers=2,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )

    full_root = tmp_path / "full"
    uninterrupted = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=full_root,
        workers=1,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )

    assert _aggregate_fingerprint(resumed.aggregate) == _aggregate_fingerprint(
        uninterrupted.aggregate
    )


def test_execute_benchmark_passes_workers(tmp_path: Path):
    result = execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=tmp_path / "bench",
        config=_dev_config(profiles=(GenerationProfile.BALANCED,)),
        workers=2,
        progress=False,
    )
    assert result.metadata.get("workers") == 2
    assert not result.blocked
