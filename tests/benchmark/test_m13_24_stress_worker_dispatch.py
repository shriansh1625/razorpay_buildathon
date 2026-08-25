"""M13.24 development stress-mode worker dispatch — not official evidence."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from revive.benchmark.official.cells.plan import plan_benchmark_cells
from revive.benchmark.official.cells.store import CellRecordContext, CellStore
from revive.benchmark.official.config import BenchmarkMode
from revive.benchmark.official.runner import execute_benchmark

CPU_COUNT = os.cpu_count() or 1


def _aggregate_fingerprint(aggregate) -> str:
    payload = aggregate.to_dict()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _cell_checksums(result) -> dict[tuple[int, str, str], str]:
    cells = plan_benchmark_cells(
        result.config,
        max_cells=result.metadata["cells_planned"],
    )
    store = CellStore(
        Path(result.metadata["cells_root"]),
        CellRecordContext(
            config_hash=result.config_hash,
            benchmark_version=result.config.benchmark_version,
            policy_pack_version=result.config.policy_pack_version,
            policy_pack_hash=result.config.policy_pack_hash,
            metric_version=result.config.metric_version,
        ),
    )
    checksums: dict[tuple[int, str, str], str] = {}
    for cell in cells:
        raw = store.read_cell_raw(cell) or {}
        checksum = raw.get("metrics_checksum")
        assert checksum is not None, f"missing metrics_checksum for {cell.key}"
        checksums[cell.key] = checksum
    return checksums


def test_stress_cells_workers_one_stays_sequential(tmp_path: Path, capsys):
    result = execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=tmp_path / "stress-w1",
        stress_cells=10,
        workers=1,
        progress=True,
    )
    out = capsys.readouterr().out
    assert "parallel workers=" not in out
    assert result.metadata["workers"] == 1
    assert result.metadata["cells_planned"] == 10
    assert len(result.aggregate.per_run) == 10


def test_stress_cells_workers_two_dispatches_parallel(tmp_path: Path, capsys):
    result = execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=tmp_path / "stress-w2",
        stress_cells=10,
        workers=2,
        progress=True,
    )
    out = capsys.readouterr().out
    assert "parallel workers=2" in out
    assert result.metadata["workers"] == 2
    assert result.metadata["cells_planned"] == 10
    assert len(result.aggregate.per_run) == 10


@pytest.mark.skipif(CPU_COUNT < 8, reason="--workers 8 requires at least 8 CPUs")
def test_stress_cells_workers_eight_dispatches_parallel(tmp_path: Path, capsys):
    result = execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=tmp_path / "stress-w8",
        stress_cells=10,
        workers=8,
        progress=True,
    )
    out = capsys.readouterr().out
    assert "parallel workers=8" in out
    assert result.metadata["workers"] == 8
    assert result.metadata["cells_planned"] == 10
    assert len(result.aggregate.per_run) == 10


def test_stress_cells_worker_fingerprints_identical(tmp_path: Path):
    worker_counts = [1, 2]
    if CPU_COUNT >= 8:
        worker_counts.append(8)

    runs = {}
    for workers in worker_counts:
        result = execute_benchmark(
            mode=BenchmarkMode.DEVELOPMENT,
            output_dir=tmp_path / f"fp-w{workers}",
            stress_cells=10,
            workers=workers,
            progress=False,
        )
        runs[workers] = result
        assert result.metadata["workers"] == workers
        assert result.metadata["cells_planned"] == 10

    reference = runs[1]
    ref_fp = _aggregate_fingerprint(reference.aggregate)
    ref_cells = _cell_checksums(reference)
    for workers, result in runs.items():
        assert _aggregate_fingerprint(result.aggregate) == ref_fp, f"aggregate mismatch workers={workers}"
        assert _cell_checksums(result) == ref_cells, f"cell fingerprint mismatch workers={workers}"


@pytest.mark.skipif(CPU_COUNT < 8, reason="--workers 8 requires at least 8 CPUs")
def test_stress_cells_workers_eight_resume_matches_uninterrupted(tmp_path: Path):
    full = execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=tmp_path / "uninterrupted",
        stress_cells=10,
        workers=8,
        progress=False,
    )
    resume_dir = tmp_path / "resume"
    partial = execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=resume_dir,
        stress_cells=10,
        workers=8,
        stop_after_cell=5,
        progress=False,
    )
    assert partial.metadata["cells_planned"] == 5
    resumed = execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=resume_dir,
        stress_cells=10,
        workers=8,
        progress=False,
    )
    assert resumed.metadata["cells_planned"] == 10
    assert resumed.metadata["cells_skipped"] >= 5
    assert _aggregate_fingerprint(resumed.aggregate) == _aggregate_fingerprint(full.aggregate)
    assert _cell_checksums(resumed) == _cell_checksums(full)


def test_stress_cells_workers_two_resume_matches_uninterrupted(tmp_path: Path):
    full = execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=tmp_path / "uninterrupted",
        stress_cells=10,
        workers=2,
        progress=False,
    )
    resume_dir = tmp_path / "resume"
    execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=resume_dir,
        stress_cells=10,
        workers=2,
        stop_after_cell=5,
        progress=False,
    )
    resumed = execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=resume_dir,
        stress_cells=10,
        workers=2,
        progress=False,
    )
    assert resumed.metadata["cells_skipped"] >= 5
    assert _aggregate_fingerprint(resumed.aggregate) == _aggregate_fingerprint(full.aggregate)
    assert _cell_checksums(resumed) == _cell_checksums(full)
