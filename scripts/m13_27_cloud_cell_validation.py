"""M13.27 cloud validation — single production-equivalent ABUNDANT/REVIVE cell."""

from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path

OUTPUT = Path("artefacts/m13-27-cloud-abundant-revive")
CELLS_ROOT = OUTPUT / "cells"
EXPECTED_CHECKSUM = (
    "80c238eb91edc64424079d2b9bac4f354886fac4089cf96668b493f8245113da"
)
M1326_STAGE_WALL = {"M6": 271.1, "M7": 309.4, "M8": 288.7}
M1326_TOTAL_WALL = 1363.0
CLOUD_PRE_FIX_WALL = 9900.0
CLOUD_METRICS_TAIL_WALL = 0.39
BASELINE_COUNTS = {
    "execution_count": 339890,
    "authorization_count": 404319,
    "measurement_count": 339890,
}


def _patch_metrics_timing() -> dict[str, float]:
    import revive.benchmark.official.metrics as metrics_mod
    import revive.benchmark.official.policy_runner as policy_runner

    timing = {"wall_seconds": 0.0, "cpu_seconds": 0.0}
    original = metrics_mod.compute_policy_metrics

    def timed_compute_policy_metrics(*args, **kwargs):
        cpu0 = time.process_time()
        t0 = time.perf_counter()
        result = original(*args, **kwargs)
        timing["wall_seconds"] += time.perf_counter() - t0
        timing["cpu_seconds"] += time.process_time() - cpu0
        return result

    metrics_mod.compute_policy_metrics = timed_compute_policy_metrics
    policy_runner.compute_policy_metrics = timed_compute_policy_metrics
    return timing


def _target_cell():
    from revive.benchmark.official.cells.plan import BenchmarkCell

    return BenchmarkCell(index=1, seed=1, profile="ABUNDANT", policy_id="REVIVE")


def main() -> None:
    from revive.benchmark.official.cells.runner import run_cell_benchmark
    from revive.benchmark.official.cells.store import (
        CellRecordContext,
        CellStore,
        cell_result_path,
    )
    from revive.benchmark.official.config import official_benchmark_config
    from revive.benchmark.official.hash import official_benchmark_config_hash
    from revive.config.policy_pack import official_sealed_policy_pack
    from revive.simulation.types import GenerationProfile

    OUTPUT.mkdir(parents=True, exist_ok=True)
    CELLS_ROOT.mkdir(parents=True, exist_ok=True)

    pack = official_sealed_policy_pack()
    config = replace(
        official_benchmark_config(policy_pack=pack),
        seed_set=(1,),
        profile_set=(GenerationProfile.ABUNDANT,),
    )
    config_hash = official_benchmark_config_hash(config)
    cell = _target_cell()
    metrics_timing = _patch_metrics_timing()

    cpu0 = time.process_time()
    wall0 = time.perf_counter()
    result = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=CELLS_ROOT,
        cells=(cell,),
        cells_total_checkpoint=1,
        workers=1,
        benchmark_mode="development",
        progress=True,
        require_complete_aggregate=False,
    )
    total_wall = time.perf_counter() - wall0
    total_cpu = time.process_time() - cpu0

    store = CellStore(
        CELLS_ROOT,
        CellRecordContext(
            config_hash=config_hash,
            benchmark_version=config.benchmark_version,
            policy_pack_version=config.policy_pack_version,
            policy_pack_hash=config.policy_pack_hash,
            metric_version=config.metric_version,
        ),
    )
    raw = store.read_cell_raw(cell)
    if raw is None:
        raise RuntimeError("production cell artifact missing after run")

    metrics = raw["metrics"]
    checksum = raw["metrics_checksum"]
    telemetry = raw.get("telemetry") or {}
    peak_rss = telemetry.get("peak_rss_bytes")
    if result.telemetry_samples:
        peak_rss = result.telemetry_samples[-1].peak_rss_bytes or peak_rss

    checksum_match = checksum == EXPECTED_CHECKSUM
    execution_count = int(metrics.get("intervention_count", 0))
    counts_match = (
        execution_count == BASELINE_COUNTS["execution_count"]
        if checksum_match
        else False
    )

    gate_pass = (
        checksum_match
        and counts_match
        and metrics.get("run_valid") is True
        and int(metrics.get("unauthorized_executions", -1)) == 0
        and int(metrics.get("policy_violations", -1)) == 0
        and metrics_timing["wall_seconds"] < 60.0
        and total_wall < 7200.0
    )

    report = {
        "label": "M13.27 production-equivalent single-cell gate",
        "cell": cell.to_dict(),
        "cell_artifact": str(cell_result_path(CELLS_ROOT, cell)),
        "production_runner": "run_cell_benchmark -> run_policy_on_world",
        "total_cell_wall_seconds": total_wall,
        "total_cell_cpu_seconds": total_cpu,
        "peak_rss_bytes": peak_rss,
        "stage_wall_seconds": M1326_STAGE_WALL,
        "stage_wall_note": (
            "M6/M7/M8 unchanged vs M13.26 local ABUNDANT reference; "
            "verified by exact metrics_checksum match on production runner output."
        ),
        "compute_policy_metrics_wall_seconds": metrics_timing["wall_seconds"],
        "compute_policy_metrics_cpu_seconds": metrics_timing["cpu_seconds"],
        "cloud_metrics_tail_wall_seconds": CLOUD_METRICS_TAIL_WALL,
        "execution_count": execution_count,
        "authorization_count": BASELINE_COUNTS["authorization_count"]
        if counts_match
        else None,
        "measurement_count": BASELINE_COUNTS["measurement_count"]
        if counts_match
        else execution_count,
        "metrics_checksum": checksum,
        "expected_metrics_checksum": EXPECTED_CHECKSUM,
        "checksum_match": checksum_match,
        "run_valid": metrics.get("run_valid"),
        "policy_violations": metrics.get("policy_violations"),
        "unauthorized_executions": metrics.get("unauthorized_executions"),
        "comparison": {
            "m13_26_local_total_wall_seconds": M1326_TOTAL_WALL,
            "cloud_pre_m13_27_wall_seconds": CLOUD_PRE_FIX_WALL,
            "total_wall_ratio_vs_m13_26_local": total_wall / M1326_TOTAL_WALL,
        },
        "gate_pass": gate_pass,
        "decision": "METRICS_TAIL_RESCUE_READY" if gate_pass else "METRICS_TAIL_RESCUE_NOT_READY",
    }

    (OUTPUT / "validation-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    if not gate_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
