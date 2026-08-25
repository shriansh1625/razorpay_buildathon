"""M13.15 development validation — workers=1 vs workers=2 (NOT official benchmark)."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from revive.benchmark.official.cells.plan import plan_benchmark_cells, plan_feasibility_cells_m13_13
from revive.benchmark.official.cells.runner import run_cell_benchmark
from revive.benchmark.official.cells.store import CellRecordContext, CellStore
from revive.benchmark.official.config import development_benchmark_config
from revive.benchmark.official.feasibility.gate import feasibility_benchmark_config
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.config.policy_pack import default_draft_policy_pack, official_sealed_policy_pack
from revive.simulation.types import GenerationProfile


def _aggregate_fingerprint(aggregate) -> str:
    payload = aggregate.to_dict()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _cell_fingerprints(root: Path, config, config_hash: str, cells) -> dict[tuple, str]:
    store = CellStore(
        root,
        CellRecordContext(
            config_hash=config_hash,
            benchmark_version=config.benchmark_version,
            policy_pack_version=config.policy_pack_version,
            policy_pack_hash=config.policy_pack_hash,
            metric_version=config.metric_version,
        ),
    )
    out = {}
    for cell in cells:
        raw = store.read_cell_raw(cell) or {}
        fp = raw.get("metrics_checksum")
        if fp:
            out[cell.key] = fp
    return out


def run_validation(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)

    # Representative development matrix: seed=1, two profiles
    pack = default_draft_policy_pack()
    config = development_benchmark_config(
        policy_pack=pack,
        seeds=(1,),
        profiles=(GenerationProfile.BALANCED, GenerationProfile.HIGH_NATURAL),
    )
    config_hash = official_benchmark_config_hash(config)
    cells = plan_benchmark_cells(config)

    t0 = time.perf_counter()
    seq = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=output / "workers-1",
        workers=1,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    wall_1 = time.perf_counter() - t0

    t0 = time.perf_counter()
    par = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=output / "workers-2",
        workers=2,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    wall_2 = time.perf_counter() - t0

    seq_fp = _aggregate_fingerprint(seq.aggregate)
    par_fp = _aggregate_fingerprint(par.aggregate)
    cell_seq = _cell_fingerprints(output / "workers-1", config, config_hash, cells)
    cell_par = _cell_fingerprints(output / "workers-2", config, config_hash, cells)

    report = {
        "label": "DEVELOPMENT_VALIDATION_ONLY",
        "workers_1_wall_seconds": wall_1,
        "workers_2_wall_seconds": wall_2,
        "speedup": wall_1 / max(wall_2, 0.001),
        "aggregate_fingerprint_match": seq_fp == par_fp,
        "cell_fingerprint_match": cell_seq == cell_par,
        "aggregate_fingerprint": seq_fp,
    }
    (output / "validation-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="M13.15 parallel validation")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("implementation/m13-15-parallel-execution"),
    )
    args = parser.parse_args()
    report = run_validation(args.output)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
