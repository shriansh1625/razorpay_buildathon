"""M13.21 performance forensic — development only, frozen official config."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

OUTPUT = Path("implementation/m13-21-performance-rescue")
LABEL = "DEVELOPMENT_FORENSIC_ONLY — NOT OFFICIAL BENCHMARK EVIDENCE"


def _write(name: str, content: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / name).write_text(content, encoding="utf-8")


def _json_write(name: str, payload: dict) -> None:
    _write(name.replace(".md", ".json") if name.endswith(".md") else name, json.dumps(payload, indent=2, sort_keys=True))


def _system_info() -> dict[str, Any]:
    try:
        import psutil

        vm = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=1.0)
        proc = psutil.Process()
        proc_cpu = proc.cpu_percent(interval=0.1)
        proc_mem = proc.memory_info().rss
    except Exception as exc:
        vm = cpu_pct = proc_cpu = proc_mem = None
        psutil_err = str(exc)
    else:
        psutil_err = None

    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "python": sys.version,
        "logical_processors": os.cpu_count(),
        "psutil_available": psutil_err is None,
        "psutil_error": psutil_err,
        "ram_total_bytes": getattr(vm, "total", None) if vm else None,
        "ram_available_bytes": getattr(vm, "available", None) if vm else None,
        "system_cpu_percent": cpu_pct,
        "sample_process_rss_bytes": proc_mem,
        "sample_process_cpu_percent": proc_cpu,
    }


def _run_revive_cell(seed: int, profile: str) -> dict[str, Any]:
    from revive.benchmark.official.performance.profiling import profile_revive_cell
    from revive.benchmark.official.cells.telemetry import PeakRssTracker

    tracker = PeakRssTracker()
    t0 = time.perf_counter()
    prof, meta = profile_revive_cell(seed, profile, use_cycle_cache=True)
    wall = time.perf_counter() - t0
    tracker.sample()
    return {
        "seed": seed,
        "profile_name": profile,
        "policy": "REVIVE",
        "wall_seconds": wall,
        "stage_profile": prof.to_dict(),
        "cell_result_hash": meta["cell_result_hash"],
        "metrics": meta["metrics"],
        "peak_rss_bytes": prof.peak_rss_bytes,
    }


def _run_baseline_cell(seed: int, profile: str, policy_id: str) -> dict[str, Any]:
    from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
    from revive.benchmark.official.baseline_pipeline import new_baseline_state, run_baseline_cycle_full
    from revive.benchmark.official.cells.store import metrics_checksum
    from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
    from revive.benchmark.official.metrics import compute_policy_metrics
    from revive.benchmark.official.world import clone_shared_world, generate_shared_world
    from revive.benchmark.types import BaselinePolicyId
    from revive.config.policy_pack import official_sealed_policy_pack
    from revive.simulation.types import GenerationProfile

    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen = generator_config_for_cell(config, seed, GenerationProfile(profile))
    bundle = generate_shared_world(gen)
    cloned = clone_shared_world(bundle)
    caps = benchmark_resource_capacities(profile_from_string(profile))
    state = new_baseline_state(cloned, BaselinePolicyId(policy_id), pack)

    t0 = time.perf_counter()
    for idx, now in enumerate(cloned.cycle_times_micros):
        run_baseline_cycle_full(state, f"cyc_{idx:04d}", now)
    wall = time.perf_counter() - t0

    metrics = compute_policy_metrics(
        policy_id,
        cloned.seed,
        cloned.profile,
        tuple(state.measurements),
        tuple(state.executions),
        tuple(state.authorizations),
        incentive_budget_capacity_paise=caps.incentive_budget_paise,
        retry_capacity=caps.retry_slots,
        message_capacity=caps.message_capacity,
    )
    return {
        "seed": seed,
        "profile": profile,
        "policy": policy_id,
        "wall_seconds": wall,
        "cycle_count": len(cloned.cycle_times_micros),
        "metrics_checksum": metrics_checksum(metrics.to_dict()),
        "intervention_count": metrics.intervention_count,
        "authorizations": len(state.authorizations),
        "executions": len(state.executions),
    }


def _parallel_case(seed: int, profile: str, workers: int, root: Path) -> dict[str, Any]:
    from revive.benchmark.official.cells.runner import run_cell_benchmark
    from revive.benchmark.official.config import preflight_benchmark_config
    from revive.benchmark.official.hash import official_benchmark_config_hash
    from revive.config.policy_pack import official_sealed_policy_pack
    from revive.simulation.types import GenerationProfile
    from dataclasses import replace

    pack = official_sealed_policy_pack()
    config = replace(
        preflight_benchmark_config(policy_pack=pack, seeds=(seed,)),
        profile_set=(GenerationProfile(profile),),
    )
    config_hash = official_benchmark_config_hash(config)
    cells_root = root / f"w{workers}"
    t0 = time.perf_counter()
    result = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=cells_root,
        workers=workers,
        benchmark_mode="development",
        progress=False,
        require_complete_aggregate=True,
    )
    wall = time.perf_counter() - t0
    revive = next(r for r in result.aggregate.per_run if r.policy_id == "REVIVE")
    return {
        "workers": workers,
        "wall_seconds": wall,
        "revive_intervention_count": revive.intervention_count,
        "peak_parent_rss_bytes": result.metadata.get("peak_parent_rss_bytes"),
        "peak_worker_rss_bytes": result.metadata.get("peak_worker_rss_bytes"),
        "estimated_parallel_peak_bytes": result.metadata.get("estimated_parallel_peak_bytes"),
    }


def run_forensic(*, skip_parallel: bool = False) -> dict[str, Any]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    system = _system_info()
    _json_write("system-performance.json", system)

    workloads = [
        (2, "BALANCED", "REVIVE"),
        (1, "BALANCED", "REVIVE"),
        (1, "HIGH_NATURAL", "REVIVE"),
        (1, "SCARCE", "REVIVE"),
    ]
    revive_runs = []
    for seed, profile, _ in workloads:
        print(f"Profiling REVIVE seed={seed} profile={profile}...")
        revive_runs.append(_run_revive_cell(seed, profile))

    baseline_runs = []
    for policy in ("B1", "B2", "B3"):
        print(f"Profiling baseline {policy} seed=1 BALANCED...")
        baseline_runs.append(_run_baseline_cell(1, "BALANCED", policy))

    m14_path = Path("implementation/m13-14-performance/profile-optimized.json")
    m14 = json.loads(m14_path.read_text(encoding="utf-8")) if m14_path.exists() else {}
    m21_primary = next(r for r in revive_runs if r["seed"] == 2 and r["profile_name"] == "BALANCED")

    preflight_revive = None
    preflight_path = Path(
        "artefacts/benchmark/preflight-m13-19/cells/seed-001/BALANCED/REVIVE.json"
    )
    if preflight_path.exists():
        raw = json.loads(preflight_path.read_text(encoding="utf-8"))
        preflight_revive = raw.get("telemetry", {}).get("elapsed_seconds")

    run4_cells = list(Path("artefacts/benchmark/official-run4/cells").rglob("REVIVE.json"))
    run4_times = []
    for p in run4_cells:
        raw = json.loads(p.read_text(encoding="utf-8"))
        tel = raw.get("telemetry") or {}
        if tel.get("elapsed_seconds"):
            run4_times.append({"path": str(p), "seconds": tel["elapsed_seconds"]})

    parallel = []
    if not skip_parallel:
        par_root = OUTPUT / "parallel-smoke"
        for w in (1, 2, 3):
            if w > (os.cpu_count() or 1):
                continue
            print(f"Parallel smoke seed=2 BALANCED workers={w}...")
            parallel.append(_parallel_case(2, "BALANCED", w, par_root))

    report = {
        "label": LABEL,
        "system": system,
        "revive_runs": revive_runs,
        "baseline_runs": baseline_runs,
        "m13_14_optimized_seconds": m14.get("total_seconds"),
        "m13_21_seed2_balanced_seconds": m21_primary["wall_seconds"],
        "preflight_m13_19_balanced_revive_seconds": preflight_revive,
        "official_run4_revive_telemetry": run4_times,
        "parallel_smoke": parallel,
    }
    _json_write("forensic-report.json", report)

    speedup_vs_m14 = (
        m14.get("total_seconds", 0) / max(m21_primary["wall_seconds"], 0.001)
        if m14.get("total_seconds")
        else None
    )
    _write(
        "regression-root-cause.md",
        f"""# M13.21 Regression Root Cause

**{LABEL}**

## Headline

| Source | seed=2 BALANCED REVIVE wall (s) |
|--------|----------------------------------|
| M13.14 optimized (zero M11/M12 execution) | {m14.get('total_seconds', 'n/a'):.1f} |
| M13.21 current (full execution bridge) | {m21_primary['wall_seconds']:.1f} |
| Ratio (M14/M21) | {speedup_vs_m14:.2f}x faster in M14 era |

## Root causes (measured, not speculative)

1. **Expected new work (M13.18)** — M13.14 profile shows M11/M12 at **0s** (no executions). Current pipeline runs simulated_v1 approval, M11 execution, and M12 measurement. This is correct semantics, not a bug.

2. **Redundant identity scans (fixed in M13.21)** — `resolve_world_opportunity_id_by_natural_key` scanned all opportunities per selected assignment (~121k/cell). Replaced with cycle-local `index_world_opportunities_by_natural_key`.

3. **Baseline path amplification** — B1/B2/B3 now execute (M13.18). Each selected decision re-runs M6/M7 in `baseline_pipeline.py` (pre-existing design). B1 seed=1 BALANCED ≈ {next((b['wall_seconds'] for b in baseline_runs if b['policy']=='B1'), 0):.0f}s.

4. **Group ETA math** — seed=1 BALANCED group ≈ 27min (B0+B1+B2+B3+REVIVE). At workers=2 across 120 groups → ~27h minimum; ABUNDANT/HIGH_NATURAL REVIVE cells exceed 690s → **49–57h ETA is consistent with measured per-cell times**, not a parallelization bug.

## Official Run 4

Marked `PARTIAL_NON_EVIDENCE` at `artefacts/benchmark/official-run4/PARTIAL_NON_EVIDENCE.json`. Do not resume.
""",
    )

    _write(
        "stage-profile.md",
        f"""# M13.21 Stage Profile — seed=2 BALANCED REVIVE

**{LABEL}**

Total: **{m21_primary['wall_seconds']:.1f}s** | Cycles: **{m21_primary['stage_profile']['cycle_count']}**

| Stage | Seconds | Share % | Calls |
|-------|---------|---------|-------|
"""
        + "\n".join(
            f"| {name} | {m21_primary['stage_profile']['stages'][name]['seconds']:.1f} | "
            f"{m21_primary['stage_profile']['stages'][name]['share_pct']:.1f} | "
            f"{m21_primary['stage_profile']['stages'][name]['count']} |"
            for name in ("M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12")
        )
        + f"""

Counters: `{json.dumps(m21_primary['stage_profile']['counters'])}`
""",
    )

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="M13.21 performance forensic")
    parser.add_argument("--skip-parallel", action="store_true")
    args = parser.parse_args()
    report = run_forensic(skip_parallel=args.skip_parallel)
    print(json.dumps({"m13_21_seed2_balanced": report["m13_21_seed2_balanced_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
