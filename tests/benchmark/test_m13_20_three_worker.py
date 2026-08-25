"""M13.20 three-worker parallel runner validation."""

from __future__ import annotations

import hashlib
import io
import json
import os
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pytest

from revive.benchmark.official.cells.parallel import (
    PARALLEL_MEMORY_SAFE_BYTES,
    validate_workers,
    verify_group_persisted,
)
from revive.benchmark.official.cells.plan import plan_benchmark_cells, plan_benchmark_groups
from revive.benchmark.official.cells.runner import run_cell_benchmark
from revive.benchmark.official.cells.store import CellRecordContext, CellStore
from revive.benchmark.official.config import development_benchmark_config, preflight_benchmark_config
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.config.policy_pack import default_draft_policy_pack, official_sealed_policy_pack
from revive.simulation.types import GenerationProfile


def _dev_config(*, seeds=(1,), profiles=(GenerationProfile.BALANCED, GenerationProfile.HIGH_NATURAL)):
    pack = default_draft_policy_pack()
    return development_benchmark_config(policy_pack=pack, seeds=seeds, profiles=profiles)


def _frozen_validation_config(
    *,
    profiles=(
        GenerationProfile.BALANCED,
        GenerationProfile.HIGH_NATURAL,
    ),
):
    pack = official_sealed_policy_pack()
    config = preflight_benchmark_config(policy_pack=pack, seeds=(1,))
    return replace(config, profile_set=profiles), pack


def _aggregate_fingerprint(aggregate) -> str:
    payload = aggregate.to_dict()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def test_validate_workers_allows_three_when_cpu_permits():
    cpu = os.cpu_count() or 1
    if cpu >= 3:
        assert validate_workers(3) == 3


def test_parallel_progress_reports_after_group_persisted(tmp_path: Path):
    config = _dev_config(profiles=(GenerationProfile.BALANCED,))
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    buf = io.StringIO()
    run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=tmp_path / "cells",
        workers=2,
        benchmark_mode="development",
        progress=True,
        progress_stream=buf,
        require_complete_aggregate=True,
    )
    out = buf.getvalue()
    assert "parallel workers=2 groups=1 cells_planned=5" in out
    assert "[GROUP 001/001] seed=1 profile=BALANCED" in out
    assert "5/5 policies complete" in out
    assert "progress: groups=1/1 cells=5/5" in out
    assert out.index("[GROUP 001/001]") < out.index("[001/005]")


def test_verify_group_persisted_rejects_partial_group(tmp_path: Path):
    config = _dev_config(profiles=(GenerationProfile.BALANCED,))
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    cells = plan_benchmark_cells(config)
    groups = plan_benchmark_groups(cells)
    store = CellStore(
        tmp_path / "cells",
        CellRecordContext(
            config_hash=config_hash,
            benchmark_version=config.benchmark_version,
            policy_pack_version=config.policy_pack_version,
            policy_pack_hash=config.policy_pack_hash,
            metric_version=config.metric_version,
        ),
    )
    with pytest.raises(RuntimeError, match="parallel group incomplete"):
        verify_group_persisted(store, groups[0])


def test_worker_failure_does_not_emit_group_complete(tmp_path: Path):
    config = _dev_config(profiles=(GenerationProfile.BALANCED,))
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)

    def _fail_group(**kwargs):
        raise RuntimeError("injected worker failure")

    with patch(
        "revive.benchmark.official.cells.parallel.run_seed_profile_group",
        side_effect=_fail_group,
    ):
        with pytest.raises(RuntimeError, match="parallel worker failed"):
            run_cell_benchmark(
                config=config,
                policy_pack=pack,
                config_hash=config_hash,
                cells_root=tmp_path / "cells",
                workers=2,
                benchmark_mode="development",
                progress=False,
                require_complete_aggregate=True,
            )

    store = CellStore(
        tmp_path / "cells",
        CellRecordContext(
            config_hash=config_hash,
            benchmark_version=config.benchmark_version,
            policy_pack_version=config.policy_pack_version,
            policy_pack_hash=config.policy_pack_hash,
            metric_version=config.metric_version,
        ),
    )
    assert store.count_valid_cells(plan_benchmark_cells(config)) == 0


@pytest.mark.parametrize("workers", [1, 2, 3])
def test_workers_match_reference_fingerprints(tmp_path: Path, workers: int):
    cpu = os.cpu_count() or 1
    if workers > cpu:
        pytest.skip(f"CPU count {cpu} < {workers}")

    config = _dev_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    cells = plan_benchmark_cells(config)

    reference = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=tmp_path / "workers-1",
        workers=1,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    result = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=tmp_path / f"workers-{workers}",
        workers=workers,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )

    assert _aggregate_fingerprint(result.aggregate) == _aggregate_fingerprint(reference.aggregate)

    ref_store = CellStore(
        tmp_path / "workers-1",
        CellRecordContext(
            config_hash=config_hash,
            benchmark_version=config.benchmark_version,
            policy_pack_version=config.policy_pack_version,
            policy_pack_hash=config.policy_pack_hash,
            metric_version=config.metric_version,
        ),
    )
    run_store = CellStore(
        tmp_path / f"workers-{workers}",
        CellRecordContext(
            config_hash=config_hash,
            benchmark_version=config.benchmark_version,
            policy_pack_version=config.policy_pack_version,
            policy_pack_hash=config.policy_pack_hash,
            metric_version=config.metric_version,
        ),
    )
    for cell in cells:
        ref_raw = ref_store.read_cell_raw(cell) or {}
        run_raw = run_store.read_cell_raw(cell) or {}
        assert ref_raw.get("metrics_checksum") == run_raw.get("metrics_checksum")


def test_workers_three_resume_matches_uninterrupted(tmp_path: Path):
    cpu = os.cpu_count() or 1
    if cpu < 3:
        pytest.skip("requires >= 3 CPUs for workers=3 resume test")

    config = _dev_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)

    partial_root = tmp_path / "partial"
    run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=partial_root,
        workers=3,
        benchmark_mode="development",
        stop_after_cell=5,
        progress=False,
        require_complete_aggregate=False,
    )
    resumed = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=partial_root,
        workers=3,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    uninterrupted = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=tmp_path / "full",
        workers=1,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    assert _aggregate_fingerprint(resumed.aggregate) == _aggregate_fingerprint(
        uninterrupted.aggregate
    )


def test_workers_three_records_memory_metadata(tmp_path: Path):
    cpu = os.cpu_count() or 1
    if cpu < 3:
        pytest.skip("requires >= 3 CPUs")

    config = _dev_config(profiles=(GenerationProfile.BALANCED,))
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    result = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=tmp_path / "cells",
        workers=3,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    assert result.metadata.get("workers") == 3
    assert result.metadata.get("peak_worker_rss_bytes") is not None
    assert result.metadata.get("estimated_parallel_peak_bytes") is not None
    assert isinstance(result.metadata.get("memory_safe"), bool)
    assert PARALLEL_MEMORY_SAFE_BYTES == 6 * 1024 * 1024 * 1024
