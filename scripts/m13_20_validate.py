"""M13.20 three-worker validation — development-only, frozen official experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from revive.benchmark.official.cells.plan import plan_benchmark_cells
from revive.benchmark.official.cells.runner import run_cell_benchmark
from revive.benchmark.official.cells.store import CellRecordContext, CellStore
from revive.benchmark.official.config import preflight_benchmark_config
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.benchmark.official.cells.parallel import PARALLEL_MEMORY_SAFE_BYTES
from revive.config.policy_pack import official_sealed_policy_pack
from revive.simulation.types import GenerationProfile

LABEL = "DEVELOPMENT_VALIDATION_ONLY — NOT OFFICIAL BENCHMARK EVIDENCE"


def _aggregate_fingerprint(aggregate) -> str:
    payload = aggregate.to_dict()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _cell_store(root: Path, config, config_hash: str) -> CellStore:
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


def _collect_cell_records(
    root: Path,
    config,
    config_hash: str,
    cells,
) -> dict[str, Any]:
    store = _cell_store(root, config, config_hash)
    checksums: dict[str, str] = {}
    revive_metrics: dict[str, dict[str, int | float | bool]] = {}
    for cell in cells:
        raw = store.read_cell_raw(cell) or {}
        key = f"seed={cell.seed}|profile={cell.profile}|policy={cell.policy_id}"
        checksum = raw.get("metrics_checksum")
        if checksum:
            checksums[key] = checksum
        if cell.policy_id == "REVIVE":
            metrics = raw.get("metrics") or {}
            revive_metrics[key] = {
                "intervention_count": metrics.get("intervention_count", 0),
                "net_recovered_paise": metrics.get("net_recovered_paise", 0),
                "contact_count": metrics.get("contact_count", 0),
            }
    return {
        "metrics_checksums": checksums,
        "revive_metrics": revive_metrics,
    }


def _validation_config(*, full_matrix: bool):
    pack = official_sealed_policy_pack()
    config = preflight_benchmark_config(policy_pack=pack, seeds=(1,))
    if not full_matrix:
        config = replace(
            config,
            profile_set=(
                GenerationProfile.BALANCED,
                GenerationProfile.HIGH_NATURAL,
            ),
        )
    return config, pack


def _run_workers(
    *,
    config,
    pack,
    config_hash: str,
    cells,
    output: Path,
    workers: int,
) -> dict[str, Any]:
    root = output / f"workers-{workers}"
    t0 = time.perf_counter()
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
    wall = time.perf_counter() - t0
    records = _collect_cell_records(root, config, config_hash, cells)
    return {
        "workers": workers,
        "wall_seconds": wall,
        "aggregate_fingerprint": _aggregate_fingerprint(result.aggregate),
        **records,
        "peak_parent_rss_bytes": result.metadata.get("peak_parent_rss_bytes"),
        "peak_worker_rss_bytes": result.metadata.get("peak_worker_rss_bytes"),
        "estimated_parallel_peak_bytes": result.metadata.get("estimated_parallel_peak_bytes"),
        "memory_safe": result.metadata.get("memory_safe"),
    }


def _run_resume_check(
    *,
    config,
    pack,
    config_hash: str,
    cells,
    output: Path,
    reference_fingerprint: str,
    reference_checksums: dict[str, str],
    stop_after_cell: int = 5,
) -> dict[str, Any]:
    resume_root = output / "resume-workers-3"
    partial = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=resume_root,
        workers=3,
        benchmark_mode="development",
        stop_after_cell=stop_after_cell,
        progress=False,
        require_complete_aggregate=False,
    )
    resumed = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=resume_root,
        workers=3,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    resumed_fp = _aggregate_fingerprint(resumed.aggregate)
    resumed_checksums = _collect_cell_records(resume_root, config, config_hash, cells)[
        "metrics_checksums"
    ]
    return {
        "stop_after_cell": stop_after_cell,
        "partial_cells_executed": partial.cells_executed,
        "resumed_aggregate_fingerprint": resumed_fp,
        "reference_aggregate_fingerprint": reference_fingerprint,
        "match": resumed_fp == reference_fingerprint,
        "metrics_checksum_match": resumed_checksums == reference_checksums,
    }


def run_validation(output: Path, *, full_matrix: bool = False) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    config, pack = _validation_config(full_matrix=full_matrix)
    config_hash = official_benchmark_config_hash(config)
    cells = plan_benchmark_cells(config)

    worker_runs = [
        _run_workers(
            config=config,
            pack=pack,
            config_hash=config_hash,
            cells=cells,
            output=output,
            workers=workers,
        )
        for workers in (1, 2, 3)
    ]
    reference = worker_runs[0]

    determinism = {
        "aggregate_fingerprint_match_1_2": worker_runs[1]["aggregate_fingerprint"]
        == reference["aggregate_fingerprint"],
        "aggregate_fingerprint_match_1_3": worker_runs[2]["aggregate_fingerprint"]
        == reference["aggregate_fingerprint"],
        "cell_fingerprint_match_1_2": worker_runs[1]["metrics_checksums"]
        == reference["metrics_checksums"],
        "cell_fingerprint_match_1_3": worker_runs[2]["metrics_checksums"]
        == reference["metrics_checksums"],
        "revive_metrics_match_1_3": worker_runs[2]["revive_metrics"]
        == reference["revive_metrics"],
    }

    memory = {
        "safe_limit_bytes": PARALLEL_MEMORY_SAFE_BYTES,
        "runs": {
            str(run["workers"]): {
                "peak_parent_rss_bytes": run["peak_parent_rss_bytes"],
                "peak_worker_rss_bytes": run["peak_worker_rss_bytes"],
                "estimated_parallel_peak_bytes": run["estimated_parallel_peak_bytes"],
                "memory_safe": run["memory_safe"],
            }
            for run in worker_runs
        },
    }

    resume = _run_resume_check(
        config=config,
        pack=pack,
        config_hash=config_hash,
        cells=cells,
        output=output,
        reference_fingerprint=reference["aggregate_fingerprint"],
        reference_checksums=reference["metrics_checksums"],
    )

    determinism_ok = all(determinism.values())
    memory_ok = bool(worker_runs[2].get("memory_safe"))
    resume_ok = resume["match"] and resume["metrics_checksum_match"]
    decision = (
        "THREE-WORKER READY"
        if determinism_ok and memory_ok and resume_ok
        else "THREE-WORKER NOT READY"
    )

    report = {
        "label": LABEL,
        "matrix_cells": len(cells),
        "full_matrix": full_matrix,
        "config_hash": config_hash,
        "frozen_experiment": {
            "horizon_days": config.simulation_horizon_days,
            "opportunity_count": config.generator_config.opportunity_count,
            "customer_count": config.generator_config.customer_count,
            "epsilon_paise": config.epsilon_paise,
            "policy_pack_version": config.policy_pack_version,
            "predictor_version": config.predictor_version,
        },
        "worker_runs": worker_runs,
        "determinism": determinism,
        "memory": memory,
        "resume_workers_3": resume,
        "decision": decision,
    }
    (output / "validation-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output / "M13.20-decision.md").write_text(
        _decision_md(report),
        encoding="utf-8",
    )
    return report


def _decision_md(report: dict[str, Any]) -> str:
    d = report["decision"]
    mem = report["memory"]["runs"].get("3", {})
    return f"""# M13.20 Three-Worker Validation

## {d}

**Label:** {report["label"]}

| Check | Result |
|-------|--------|
| workers=1/2/3 aggregate fingerprint | {report["determinism"]["aggregate_fingerprint_match_1_3"]} |
| workers=1/3 cell metrics_checksum | {report["determinism"]["cell_fingerprint_match_1_3"]} |
| workers=3 resume | {report["resume_workers_3"]["match"]} |
| workers=3 memory safe (~8 GB) | {mem.get("memory_safe")} |
| Estimated parallel peak (3 workers) | {mem.get("estimated_parallel_peak_bytes")} bytes |

Matrix: {report["matrix_cells"]} cells (seed=1, frozen official scale).
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="M13.20 three-worker validation")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("implementation/m13-20-three-worker-validation"),
    )
    parser.add_argument(
        "--full-matrix",
        action="store_true",
        help="Use all 6 profiles (30 cells) instead of 2-profile representative (10 cells)",
    )
    args = parser.parse_args()
    report = run_validation(args.output, full_matrix=args.full_matrix)
    print(json.dumps({"decision": report["decision"], "matrix_cells": report["matrix_cells"]}, indent=2))


if __name__ == "__main__":
    main()
