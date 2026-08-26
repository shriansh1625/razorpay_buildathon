"""M13.25 checkpoint / resume integrity regression tests."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from revive.benchmark.official.cells.plan import plan_benchmark_cells
from revive.benchmark.official.cells.runner import run_cell_benchmark
from revive.benchmark.official.cells.store import (
    CellRecordContext,
    CellStore,
    atomic_write_json,
    cell_result_path,
    metrics_checksum,
    reconcile_checkpoint,
)
from revive.benchmark.official.config import development_benchmark_config
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.config.policy_pack import default_draft_policy_pack
from revive.simulation.types import GenerationProfile

REPRO_ROOT = Path(__file__).resolve().parents[2] / "implementation" / "m13-25-checkpoint-repair" / "repro"
CPU_COUNT = os.cpu_count() or 1


@pytest.fixture
def repro_dir(tmp_path: Path):
    REPRO_ROOT.mkdir(parents=True, exist_ok=True)
    return tmp_path


def _tiny_config():
    pack = default_draft_policy_pack()
    return development_benchmark_config(
        policy_pack=pack,
        seeds=(1,),
        profiles=(GenerationProfile.BALANCED, GenerationProfile.HIGH_NATURAL),
    )


def _store(config, config_hash: str, root: Path) -> CellStore:
    return CellStore(
        root,
        CellRecordContext(
            config_hash=config_hash,
            benchmark_version=config.benchmark_version,
            policy_pack_version=config.policy_pack_version,
            policy_pack_hash=config.policy_pack_hash,
            metric_version=config.metric_version,
        ),
    )


def _aggregate_fingerprint(aggregate) -> str:
    payload = aggregate.to_dict()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _cell_checksums(root: Path, config, config_hash: str, cells) -> dict[tuple[int, str, str], str]:
    store = _store(config, config_hash, root)
    checksums: dict[tuple[int, str, str], str] = {}
    for cell in cells:
        raw = store.read_cell_raw(cell) or {}
        checksum = raw.get("metrics_checksum")
        assert checksum is not None, f"missing checksum for {cell.key}"
        checksums[cell.key] = checksum
    return checksums


def _run_uninterrupted(tmp_path: Path, *, workers: int = 1):
    config = _tiny_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    root = tmp_path / f"full-w{workers}"
    result = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=root,
        workers=workers,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    cells = plan_benchmark_cells(config)
    manifest = json.loads((root / "checkpoint-manifest.json").read_text(encoding="utf-8"))
    assert manifest["cells_completed"] == len(cells)
    assert manifest["cells_total"] == len(cells)
    return config, pack, config_hash, cells, result, root


def test_reconcile_files_ahead_of_manifest(repro_dir: Path):
    config, pack, config_hash, cells, reference, _ = _run_uninterrupted(repro_dir, workers=1)
    resume_root = repro_dir / "files-ahead"
    full_root = repro_dir / "full-w1"
    import shutil

    shutil.copytree(full_root, resume_root)

    store = _store(config, config_hash, resume_root)
    missing = cells[-1]
    cell_result_path(resume_root, missing).unlink()
    assert store.count_valid_cells(cells) == len(cells) - 1

    stale_last = cells[4]
    store.write_checkpoint(
        cells_completed=6,
        cells_total=len(cells),
        last_cell=stale_last,
    )

    report = reconcile_checkpoint(store, cells, len(cells))
    assert report.files_ahead is True
    assert report.valid_cells == len(cells) - 1
    manifest = json.loads((resume_root / "checkpoint-manifest.json").read_text(encoding="utf-8"))
    assert manifest["cells_completed"] == len(cells) - 1

    resumed = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=resume_root,
        workers=2,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    manifest = json.loads((resume_root / "checkpoint-manifest.json").read_text(encoding="utf-8"))
    assert manifest["cells_completed"] == len(cells)
    assert _aggregate_fingerprint(resumed.aggregate) == _aggregate_fingerprint(reference.aggregate)
    assert _cell_checksums(resume_root, config, config_hash, cells) == _cell_checksums(
        full_root, config, config_hash, cells
    )


def test_reconcile_manifest_ahead_of_files(repro_dir: Path):
    config, pack, config_hash, cells, reference, full_root = _run_uninterrupted(repro_dir, workers=1)
    resume_root = repro_dir / "manifest-ahead"
    import shutil

    shutil.copytree(full_root, resume_root)
    deleted = cells[-1]
    cell_result_path(resume_root, deleted).unlink()

    store = _store(config, config_hash, resume_root)
    store.write_checkpoint(
        cells_completed=len(cells),
        cells_total=len(cells),
        last_cell=cells[-1],
    )
    report = reconcile_checkpoint(store, cells, len(cells))
    assert report.manifest_ahead is True
    assert report.valid_cells == len(cells) - 1

    resumed = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=resume_root,
        workers=2,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    manifest = json.loads((resume_root / "checkpoint-manifest.json").read_text(encoding="utf-8"))
    assert manifest["cells_completed"] == len(cells)
    assert _aggregate_fingerprint(resumed.aggregate) == _aggregate_fingerprint(reference.aggregate)


def test_corrupt_cell_is_recomputed(repro_dir: Path):
    config, pack, config_hash, cells, _, full_root = _run_uninterrupted(repro_dir, workers=1)
    target = cells[0]
    path = cell_result_path(full_root, target)
    corrupt = json.loads(path.read_text(encoding="utf-8"))
    corrupt["metrics"]["net_recovered_paise"] = 999_999_999
    atomic_write_json(path, corrupt)

    store = _store(config, config_hash, full_root)
    assert not store.is_cell_valid(target)
    report = reconcile_checkpoint(store, cells, len(cells))
    assert report.valid_cells == len(cells) - 1

    rerun = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=full_root,
        workers=2,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    assert rerun.cells_executed >= 1
    fixed = json.loads(path.read_text(encoding="utf-8"))
    assert fixed["metrics"]["net_recovered_paise"] != 999_999_999
    assert metrics_checksum(fixed["metrics"]) == fixed["metrics_checksum"]


def test_partial_group_four_of_five_resume(repro_dir: Path):
    config, pack, config_hash, cells, reference, _ = _run_uninterrupted(repro_dir, workers=1)
    partial_root = repro_dir / "partial-group"
    run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=partial_root,
        stop_after_cell=9,
        workers=2,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=False,
    )
    store = _store(config, config_hash, partial_root)
    assert store.count_valid_cells(cells) == 9
    missing = cells[-1]
    assert missing.policy_id == "REVIVE"
    assert not store.is_cell_valid(missing)

    store.write_checkpoint(
        cells_completed=5,
        cells_total=len(cells),
        last_cell=cells[4],
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
    manifest = json.loads((partial_root / "checkpoint-manifest.json").read_text(encoding="utf-8"))
    assert manifest["cells_completed"] == len(cells)
    assert cell_result_path(partial_root, missing).exists()
    assert _aggregate_fingerprint(resumed.aggregate) == _aggregate_fingerprint(reference.aggregate)


def test_production_failure_shape_resume(repro_dir: Path):
    """Scaled 10-cell analogue of manifest=26, files=29, missing REVIVE."""
    config, pack, config_hash, cells, reference, full_root = _run_uninterrupted(repro_dir, workers=1)
    resume_root = repro_dir / "production-shape"
    import shutil

    shutil.copytree(full_root, resume_root)
    missing = next(c for c in cells if c.profile == "HIGH_NATURAL" and c.policy_id == "REVIVE")
    cell_result_path(resume_root, missing).unlink()

    store = _store(config, config_hash, resume_root)
    assert store.count_valid_cells(cells) == len(cells) - 1
    store.write_checkpoint(
        cells_completed=6,
        cells_total=len(cells),
        last_cell=cells[4],
    )

    resumed = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=resume_root,
        workers=2,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    manifest = json.loads((resume_root / "checkpoint-manifest.json").read_text(encoding="utf-8"))
    assert manifest["cells_completed"] == len(cells)
    assert store.is_cell_valid(missing)
    assert _aggregate_fingerprint(resumed.aggregate) == _aggregate_fingerprint(reference.aggregate)


@pytest.mark.parametrize("workers", [1, 2, 3])
def test_parallel_order_independence(repro_dir: Path, workers: int):
    if workers > CPU_COUNT:
        pytest.skip(f"requires >= {workers} CPUs")
    config, pack, config_hash, cells, reference, ref_root = _run_uninterrupted(repro_dir, workers=1)
    result = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=repro_dir / f"workers-{workers}",
        workers=workers,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    assert _aggregate_fingerprint(result.aggregate) == _aggregate_fingerprint(reference.aggregate)
    assert _cell_checksums(repro_dir / f"workers-{workers}", config, config_hash, cells) == _cell_checksums(
        ref_root, config, config_hash, cells
    )


def test_interruption_then_resume_parallel(repro_dir: Path):
    if CPU_COUNT < 2:
        pytest.skip("requires >= 2 CPUs")
    config, pack, config_hash, cells, reference, _ = _run_uninterrupted(repro_dir, workers=1)
    partial_root = repro_dir / "interrupt"
    run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=partial_root,
        stop_after_cell=5,
        workers=2,
        benchmark_mode="development",
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
    manifest = json.loads((partial_root / "checkpoint-manifest.json").read_text(encoding="utf-8"))
    assert manifest["cells_completed"] == len(cells)
    assert _aggregate_fingerprint(resumed.aggregate) == _aggregate_fingerprint(reference.aggregate)
