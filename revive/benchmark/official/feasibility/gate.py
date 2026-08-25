"""Official benchmark run feasibility gate — M13.13 (revised 31-cell matrix)."""

from __future__ import annotations

import hashlib
import json
import shutil
import statistics
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from revive.benchmark.official.aggregate import BenchmarkAggregate
from revive.benchmark.official.cells.plan import (
    OFFICIAL_FROZEN_CELL_TOTAL,
    BenchmarkCell,
    plan_benchmark_cells,
    plan_feasibility_cells_m13_13,
)
from revive.benchmark.official.cells.runner import run_cell_benchmark
from revive.benchmark.official.cells.store import CellRecordContext, CellStore
from revive.benchmark.official.cells.telemetry import current_rss_bytes
from revive.benchmark.official.config import (
    OfficialBenchmarkConfig,
    official_benchmark_config,
)
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.config.policy_pack import official_sealed_policy_pack

FEASIBILITY_LABEL = "DEVELOPMENT_FEASIBILITY_ONLY"
FEASIBILITY_MATRIX_CELLS = 31
FEASIBILITY_CORE_CELLS = 30
OFFICIAL_REVIVE_CELL_TOTAL = 20 * 6  # 120
RESUME_STOP_AFTER_CELL = 10
DETERMINISM_CELL_COUNT = 3


@dataclass
class FeasibilityGateResult:
    label: str
    config_hash: str
    cells_run: int
    cells_total_official: int
    total_wall_seconds: float
    cell_records: list[dict[str, Any]]
    group_records: list[dict[str, Any]]
    summary: dict[str, Any]
    projection: dict[str, Any]
    revive_stats: dict[str, Any]
    determinism: dict[str, Any]
    resume: dict[str, Any]
    memory: dict[str, Any]
    aggregate_fingerprint: str
    cells_root: Path
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "config_hash": self.config_hash,
            "cells_run": self.cells_run,
            "cells_total_official": self.cells_total_official,
            "total_wall_seconds": self.total_wall_seconds,
            "cell_records": self.cell_records,
            "group_records": self.group_records,
            "summary": self.summary,
            "projection": self.projection,
            "revive_stats": self.revive_stats,
            "determinism": self.determinism,
            "resume": self.resume,
            "memory": self.memory,
            "aggregate_fingerprint": self.aggregate_fingerprint,
            "cells_root": str(self.cells_root),
            "metadata": self.metadata,
        }


def feasibility_benchmark_config(policy_pack=None) -> OfficialBenchmarkConfig:
    """Frozen official scale — not official evidence."""
    pack = policy_pack or official_sealed_policy_pack()
    official = official_benchmark_config(policy_pack=pack)
    return replace(
        official,
        benchmark_id=f"{official.benchmark_id}_m13_13_feasibility",
        seed_set=(1, 2, 3),
    )


def aggregate_fingerprint(aggregate: BenchmarkAggregate) -> str:
    payload = aggregate.to_dict()
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def _cell_store(root: Path, config: OfficialBenchmarkConfig, config_hash: str) -> CellStore:
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
    store: CellStore,
    cells: tuple[BenchmarkCell, ...],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for cell in cells:
        raw = store.read_cell_raw(cell)
        if raw is None:
            records.append(
                {
                    "seed": cell.seed,
                    "profile": cell.profile,
                    "policy": cell.policy_id,
                    "cell_index": cell.index,
                    "elapsed_seconds": None,
                    "rss_before_bytes": None,
                    "rss_after_bytes": None,
                    "peak_rss_bytes": None,
                    "result_fingerprint": None,
                    "completion_status": "missing",
                    "stress_cell": cell.seed == 2 and cell.policy_id == "REVIVE",
                }
            )
            continue
        telemetry = raw.get("telemetry") or {}
        records.append(
            {
                "seed": cell.seed,
                "profile": cell.profile,
                "policy": cell.policy_id,
                "cell_index": cell.index,
                "elapsed_seconds": telemetry.get("duration_seconds"),
                "rss_before_bytes": telemetry.get("rss_before_bytes"),
                "rss_after_bytes": telemetry.get("rss_after_bytes"),
                "peak_rss_bytes": telemetry.get("peak_rss_bytes"),
                "result_fingerprint": raw.get("metrics_checksum"),
                "completion_status": "completed",
                "stress_cell": cell.seed == 2 and cell.policy_id == "REVIVE",
            }
        )
    return records


def _collect_group_records(cell_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for rec in cell_records:
        if rec["completion_status"] != "completed":
            continue
        key = (rec["seed"], rec["profile"])
        groups.setdefault(key, []).append(rec)

    group_records: list[dict[str, Any]] = []
    for (seed, profile), items in sorted(groups.items()):
        durations = [r["elapsed_seconds"] for r in items if r["elapsed_seconds"] is not None]
        rss_values = [
            r["peak_rss_bytes"] or r["rss_after_bytes"]
            for r in items
            if (r["peak_rss_bytes"] or r["rss_after_bytes"]) is not None
        ]
        group_records.append(
            {
                "seed": seed,
                "profile": profile,
                "policies_completed": len(items),
                "group_duration_seconds": sum(durations) if durations else None,
                "peak_rss_bytes": max(rss_values) if rss_values else None,
            }
        )
    return group_records


def _summarize_durations(durations: list[float]) -> dict[str, Any]:
    if not durations:
        return {}
    sorted_d = sorted(durations)
    n = len(sorted_d)
    p95_idx = min(n - 1, int(0.95 * n))
    return {
        "count": n,
        "min_seconds": sorted_d[0],
        "max_seconds": sorted_d[-1],
        "mean_seconds": statistics.mean(sorted_d),
        "median_seconds": statistics.median(sorted_d),
        "p95_seconds": sorted_d[p95_idx],
        "total_seconds": sum(sorted_d),
    }


def _summarize_rss(rss_values: list[int]) -> dict[str, Any]:
    if not rss_values:
        return {}
    return {
        "max_bytes": max(rss_values),
        "mean_bytes": int(statistics.mean(rss_values)),
        "samples": len(rss_values),
    }


def _revive_runtime_stats(cell_records: list[dict[str, Any]]) -> dict[str, Any]:
    revive = [
        float(r["elapsed_seconds"])
        for r in cell_records
        if r["completion_status"] == "completed"
        and r["policy"] == "REVIVE"
        and r["elapsed_seconds"] is not None
    ]
    if not revive:
        return {}
    sorted_r = sorted(revive)
    p95_idx = min(len(sorted_r) - 1, int(0.95 * len(sorted_r)))
    median = statistics.median(sorted_r)
    p95 = sorted_r[p95_idx]
    slowest = sorted_r[-1]
    return {
        "sample_count": len(revive),
        "median_seconds": median,
        "p95_seconds": p95,
        "slowest_seconds": slowest,
        "projected_120_revive_median_seconds": median * OFFICIAL_REVIVE_CELL_TOTAL,
        "projected_120_revive_p95_seconds": p95 * OFFICIAL_REVIVE_CELL_TOTAL,
        "projected_120_revive_conservative_seconds": slowest * OFFICIAL_REVIVE_CELL_TOTAL,
        "projected_120_revive_median_hours": (median * OFFICIAL_REVIVE_CELL_TOTAL) / 3600,
        "projected_120_revive_p95_hours": (p95 * OFFICIAL_REVIVE_CELL_TOTAL) / 3600,
        "projected_120_revive_conservative_hours": (slowest * OFFICIAL_REVIVE_CELL_TOTAL) / 3600,
    }


def _project_official_600(cell_records: list[dict[str, Any]]) -> dict[str, Any]:
    revive = [
        float(r["elapsed_seconds"])
        for r in cell_records
        if r["completion_status"] == "completed"
        and r["policy"] == "REVIVE"
        and r["elapsed_seconds"] is not None
    ]
    baseline = [
        float(r["elapsed_seconds"])
        for r in cell_records
        if r["completion_status"] == "completed"
        and r["policy"] != "REVIVE"
        and r["elapsed_seconds"] is not None
    ]
    if not revive or not baseline:
        return {"official_cell_total": OFFICIAL_FROZEN_CELL_TOTAL}
    revive_median = statistics.median(revive)
    revive_p95 = sorted(revive)[min(len(revive) - 1, int(0.95 * len(revive)))]
    revive_max = max(revive)
    baseline_median = statistics.median(baseline)
    baseline_max = max(baseline)
    median_total = revive_median * OFFICIAL_REVIVE_CELL_TOTAL + baseline_median * (
        OFFICIAL_FROZEN_CELL_TOTAL - OFFICIAL_REVIVE_CELL_TOTAL
    )
    p95_total = revive_p95 * OFFICIAL_REVIVE_CELL_TOTAL + baseline_median * (
        OFFICIAL_FROZEN_CELL_TOTAL - OFFICIAL_REVIVE_CELL_TOTAL
    )
    conservative = revive_max * OFFICIAL_REVIVE_CELL_TOTAL + baseline_max * (
        OFFICIAL_FROZEN_CELL_TOTAL - OFFICIAL_REVIVE_CELL_TOTAL
    )
    return {
        "official_cell_total": OFFICIAL_FROZEN_CELL_TOTAL,
        "official_revive_cell_total": OFFICIAL_REVIVE_CELL_TOTAL,
        "revive_median_seconds": revive_median,
        "baseline_median_seconds": baseline_median,
        "projected_600_median_seconds": median_total,
        "projected_600_p95_seconds": p95_total,
        "projected_600_conservative_seconds": conservative,
        "projected_600_median_hours": median_total / 3600,
        "projected_600_p95_hours": p95_total / 3600,
        "projected_600_conservative_hours": conservative / 3600,
    }


def _memory_growth_check(group_records: list[dict[str, Any]]) -> dict[str, Any]:
    peaks = [g["peak_rss_bytes"] for g in group_records if g.get("peak_rss_bytes")]
    if len(peaks) < 3:
        return {"material_growth": False, "samples": len(peaks)}
    first_half = statistics.mean(peaks[: len(peaks) // 2])
    second_half = statistics.mean(peaks[len(peaks) // 2 :])
    ratio = second_half / first_half if first_half else 1.0
    return {
        "first_half_mean_rss_bytes": int(first_half),
        "second_half_mean_rss_bytes": int(second_half),
        "growth_ratio": round(ratio, 3),
        "material_growth": ratio > 1.35,
        "samples": len(peaks),
    }


def _run_determinism_check(
    config: OfficialBenchmarkConfig,
    policy_pack,
    config_hash: str,
    core_cells: tuple[BenchmarkCell, ...],
) -> dict[str, Any]:
    import tempfile

    sample_count = min(DETERMINISM_CELL_COUNT, len(core_cells))
    sample = core_cells[:sample_count]
    results_a: list[str | None] = []
    results_b: list[str | None] = []

    for run_results in (results_a, results_b):
        with tempfile.TemporaryDirectory(prefix="revive-feas-det-") as tmp:
            root = Path(tmp)
            run_cell_benchmark(
                config=config,
                policy_pack=policy_pack,
                config_hash=config_hash,
                cells_root=root,
                cells=sample,
                cells_total_checkpoint=len(sample),
                progress=False,
                require_complete_aggregate=False,
            )
            store = _cell_store(root, config, config_hash)
            for cell in sample:
                raw = store.read_cell_raw(cell)
                run_results.append(raw.get("metrics_checksum") if raw else None)

    identical = results_a == results_b and all(h is not None for h in results_a)
    return {
        "cells_tested": sample_count,
        "fingerprints_run_a": results_a,
        "fingerprints_run_b": results_b,
        "identical": identical,
    }


def _run_resume_check(
    config: OfficialBenchmarkConfig,
    policy_pack,
    config_hash: str,
    core_cells: tuple[BenchmarkCell, ...],
    reference_fingerprints: dict[tuple[int, str, str], str],
    resume_root: Path,
) -> dict[str, Any]:
    if resume_root.exists():
        shutil.rmtree(resume_root)
    resume_root.mkdir(parents=True, exist_ok=True)

    partial = run_cell_benchmark(
        config=config,
        policy_pack=policy_pack,
        config_hash=config_hash,
        cells_root=resume_root,
        cells=core_cells,
        cells_total_checkpoint=len(core_cells),
        stop_after_cell=RESUME_STOP_AFTER_CELL,
        progress=False,
        require_complete_aggregate=False,
    )
    resumed = run_cell_benchmark(
        config=config,
        policy_pack=policy_pack,
        config_hash=config_hash,
        cells_root=resume_root,
        cells=core_cells,
        cells_total_checkpoint=len(core_cells),
        progress=False,
        require_complete_aggregate=False,
    )
    store = _cell_store(resume_root, config, config_hash)
    resumed_fps = {
        c.key: (store.read_cell_raw(c) or {}).get("metrics_checksum")
        for c in core_cells
        if store.is_cell_valid(c)
    }
    matches = all(
        resumed_fps.get(k) == reference_fingerprints.get(k)
        for k in reference_fingerprints
        if k in resumed_fps
    )
    return {
        "stop_after_cell": RESUME_STOP_AFTER_CELL,
        "cells_executed_partial": partial.cells_executed,
        "cells_skipped_on_resume": resumed.cells_skipped,
        "cells_executed_on_resume": resumed.cells_executed,
        "fingerprints_match_reference": matches,
        "checkpoint_present": (resume_root / "checkpoint-manifest.json").exists(),
    }


def run_feasibility_gate(
    output_dir: Path,
    *,
    skip_resume: bool = False,
    skip_determinism: bool = False,
    progress: bool = True,
) -> FeasibilityGateResult:
    """Run 31-cell frozen-scale feasibility matrix (NOT official evidence)."""
    pack = official_sealed_policy_pack()
    config = feasibility_benchmark_config(policy_pack=pack)
    config_hash = official_benchmark_config_hash(config)
    all_cells = plan_feasibility_cells_m13_13(config)
    core_cells = tuple(c for c in all_cells if not (c.seed == 2 and c.policy_id == "REVIVE"))
    stress_cells = tuple(c for c in all_cells if c.seed == 2 and c.policy_id == "REVIVE")

    cells_root = output_dir / "cells"
    cells_root.mkdir(parents=True, exist_ok=True)
    checkpoint_path = cells_root / "checkpoint-manifest.json"
    if checkpoint_path.exists():
        try:
            existing = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            if existing.get("cells_total") != FEASIBILITY_MATRIX_CELLS:
                checkpoint_path.unlink()
        except (OSError, json.JSONDecodeError):
            checkpoint_path.unlink(missing_ok=True)

    rss_start = current_rss_bytes()
    t0 = time.perf_counter()
    result = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=cells_root,
        cells=all_cells,
        cells_total_checkpoint=FEASIBILITY_MATRIX_CELLS,
        progress=progress,
        require_complete_aggregate=False,
    )
    total_wall = time.perf_counter() - t0
    rss_end = current_rss_bytes()

    store = _cell_store(cells_root, config, config_hash)
    cell_records = _collect_cell_records(store, all_cells)
    group_records = _collect_group_records(cell_records)
    durations = [
        float(r["elapsed_seconds"])
        for r in cell_records
        if r["completion_status"] == "completed" and r["elapsed_seconds"] is not None
    ]
    rss_peaks = [
        int(r["peak_rss_bytes"] or r["rss_after_bytes"])
        for r in cell_records
        if r["completion_status"] == "completed"
        and (r["peak_rss_bytes"] or r["rss_after_bytes"]) is not None
    ]
    reference_fingerprints = {
        (r["seed"], r["profile"], r["policy"]): r["result_fingerprint"]
        for r in cell_records
        if r["result_fingerprint"]
    }
    core_aggregate_cells = core_cells
    from revive.benchmark.official.cells.store import aggregate_from_store

    aggregate = aggregate_from_store(
        store, config, cells=core_aggregate_cells, require_complete=True
    )
    agg_fp = aggregate_fingerprint(aggregate)
    revive_stats = _revive_runtime_stats(cell_records)
    projection = _project_official_600(cell_records)
    summary = {
        **(_summarize_durations(durations)),
        "rss": _summarize_rss(rss_peaks),
        "rss_start_bytes": rss_start,
        "rss_end_bytes": rss_end,
    }
    memory = {
        "rss_start_bytes": rss_start,
        "rss_end_bytes": rss_end,
        "peak_rss_bytes": max(rss_peaks) if rss_peaks else None,
        "group_peak_summary": _summarize_rss(
            [g["peak_rss_bytes"] for g in group_records if g.get("peak_rss_bytes")]
        ),
        "growth_check": _memory_growth_check(group_records),
    }

    determinism = (
        {"skipped": True}
        if skip_determinism
        else _run_determinism_check(config, pack, config_hash, core_cells)
    )
    resume = (
        {"skipped": True}
        if skip_resume
        else _run_resume_check(
            config,
            pack,
            config_hash,
            core_cells,
            reference_fingerprints,
            output_dir / "resume_test_cells",
        )
    )

    gate = FeasibilityGateResult(
        label=FEASIBILITY_LABEL,
        config_hash=config_hash,
        cells_run=len(all_cells),
        cells_total_official=OFFICIAL_FROZEN_CELL_TOTAL,
        total_wall_seconds=total_wall,
        cell_records=cell_records,
        group_records=group_records,
        summary=summary,
        projection=projection,
        revive_stats=revive_stats,
        determinism=determinism,
        resume=resume,
        memory=memory,
        aggregate_fingerprint=agg_fp,
        cells_root=cells_root,
        metadata={
            "matrix": "seed=1 all profiles + stress REVIVE seed=2 BALANCED",
            "feasibility_matrix_cells": FEASIBILITY_MATRIX_CELLS,
            "core_cells": FEASIBILITY_CORE_CELLS,
            "stress_cell": {"seed": 2, "profile": "BALANCED", "policy": "REVIVE"},
        },
    )

    manifest = {
        "label": FEASIBILITY_LABEL,
        "warning": "NOT OFFICIAL BENCHMARK EVIDENCE",
        "gate_result": gate.to_dict(),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "feasibility-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return gate


def write_feasibility_reports(gate: FeasibilityGateResult, report_dir: Path) -> dict[str, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    def write(name: str, content: str) -> None:
        path = report_dir / name
        path.write_text(content, encoding="utf-8")
        paths[name] = path

    write("runtime-profile.md", _runtime_profile_md(gate))
    write("memory-profile.md", _memory_profile_md(gate))
    write("representative-cells.md", _representative_cells_md(gate))
    write("projected-runtime.md", _projected_runtime_md(gate))
    write("reproducibility.md", _reproducibility_md(gate))
    write("resume-test.md", _resume_test_md(gate))
    write("M13.13-decision.md", _decision_md(gate))
    return paths


def _format_hours(seconds: float) -> str:
    if seconds < 3600:
        return f"{seconds / 60:.1f} min"
    return f"{seconds / 3600:.1f} h"


def _runtime_profile_md(gate: FeasibilityGateResult) -> str:
    s = gate.summary
    rs = gate.revive_stats
    return f"""# M13.13 Runtime Profile

**Label:** {gate.label}  
**NOT OFFICIAL BENCHMARK EVIDENCE**

## Matrix (revised)

- Core: seed=1 × 6 profiles × 5 policies = 30 cells
- Stress: seed=2, profile=BALANCED, policy=REVIVE = 1 cell
- **Total: {gate.cells_run} cells**

## Total wall time

{gate.total_wall_seconds:.1f} s ({_format_hours(gate.total_wall_seconds)})

## REVIVE runtime (observed)

| Stat | Seconds |
|------|---------|
| median | {rs.get("median_seconds", "n/a")} |
| p95 | {rs.get("p95_seconds", "n/a")} |
| slowest | {rs.get("slowest_seconds", "n/a")} |

## Per-policy means

{_policy_timing_table(gate.cell_records)}
"""


def _policy_timing_table(records: list[dict[str, Any]]) -> str:
    by_policy: dict[str, list[float]] = {}
    for r in records:
        if r["completion_status"] != "completed" or r["elapsed_seconds"] is None:
            continue
        by_policy.setdefault(r["policy"], []).append(float(r["elapsed_seconds"]))
    lines = ["| Policy | mean (s) | max (s) | count |", "|--------|----------|---------|-------|"]
    for policy in ("B0", "B1", "B2", "B3", "REVIVE"):
        d = by_policy.get(policy, [])
        if not d:
            continue
        lines.append(f"| {policy} | {statistics.mean(d):.2f} | {max(d):.2f} | {len(d)} |")
    return "\n".join(lines)


def _memory_profile_md(gate: FeasibilityGateResult) -> str:
    m = gate.memory
    g = m.get("growth_check", {})
    peak_mb = (m.get("peak_rss_bytes") or 0) / (1024 * 1024)
    return f"""# M13.13 Memory Profile

**Label:** {gate.label}

| Metric | Value |
|--------|-------|
| RSS start | {m.get("rss_start_bytes")} |
| RSS end | {m.get("rss_end_bytes")} |
| Peak RSS (all cells) | {m.get("peak_rss_bytes")} ({peak_mb:.1f} MB) |
| Growth ratio | {g.get("growth_ratio")} |
| Material growth | {g.get("material_growth")} |
"""


def _representative_cells_md(gate: FeasibilityGateResult) -> str:
    lines = [
        "# M13.13 Representative Cells",
        "",
        f"**Label:** {gate.label}",
        "",
        "| seed | profile | policy | elapsed (s) | peak RSS (MB) | fingerprint |",
        "|------|---------|--------|-------------|---------------|-------------|",
    ]
    for r in gate.cell_records:
        peak = r.get("peak_rss_bytes") or r.get("rss_after_bytes")
        peak_mb = f"{peak / (1024 * 1024):.1f}" if peak else "n/a"
        dur = r.get("elapsed_seconds")
        dur_s = f"{dur:.2f}" if dur is not None else "n/a"
        fp = (r.get("result_fingerprint") or "")[:16]
        stress = " *" if r.get("stress_cell") else ""
        lines.append(
            f"| {r['seed']} | {r['profile']} | {r['policy']}{stress} | {dur_s} | {peak_mb} | {fp}... |"
        )
    lines.append("\n* = stress cell (seed=2 BALANCED REVIVE)")
    return "\n".join(lines)


def _projected_runtime_md(gate: FeasibilityGateResult) -> str:
    p = gate.projection
    rs = gate.revive_stats
    return f"""# M13.13 Projected Official Runtime

**Label:** {gate.label}

## 120 REVIVE cells (20 seeds × 6 profiles)

| Estimate | Hours |
|----------|-------|
| Median-based | {rs.get("projected_120_revive_median_hours", 0):.1f} |
| P95-based | {rs.get("projected_120_revive_p95_hours", 0):.1f} |
| Conservative (slowest × 120) | {rs.get("projected_120_revive_conservative_hours", 0):.1f} |

## 600 total cells (120 REVIVE + 480 baselines)

| Estimate | Hours |
|----------|-------|
| Median-based | {p.get("projected_600_median_hours", 0):.1f} |
| P95 REVIVE + median baseline | {p.get("projected_600_p95_hours", 0):.1f} |
| Conservative | {p.get("projected_600_conservative_hours", 0):.1f} |
"""


def _reproducibility_md(gate: FeasibilityGateResult) -> str:
    d = gate.determinism
    return f"""# M13.13 Reproducibility

**Label:** {gate.label}

- Determinism ({d.get("cells_tested", "skipped")} cells): {d.get("identical")}
- Core aggregate fingerprint: `{gate.aggregate_fingerprint}`
"""


def _resume_test_md(gate: FeasibilityGateResult) -> str:
    r = gate.resume
    return f"""# M13.13 Resume Test

**Label:** {gate.label}

| Check | Result |
|-------|--------|
| Stop after cell | {r.get("stop_after_cell")} |
| Skipped on resume | {r.get("cells_skipped_on_resume")} |
| Fingerprints match reference | {r.get("fingerprints_match_reference")} |
| Checkpoint present | {r.get("checkpoint_present")} |
"""


def _feasibility_decision(gate: FeasibilityGateResult) -> str:
    m = gate.memory.get("growth_check", {})
    if m.get("material_growth"):
        return "NOT FEASIBLE FOR OFFICIAL RUN"
    if gate.determinism.get("identical") is False:
        return "NOT FEASIBLE FOR OFFICIAL RUN"
    if gate.resume.get("fingerprints_match_reference") is False:
        return "NOT FEASIBLE FOR OFFICIAL RUN"
    max_rss = gate.memory.get("peak_rss_bytes") or 0
    if max_rss > 6 * 1024 * 1024 * 1024:
        return "NOT FEASIBLE FOR OFFICIAL RUN"
    conservative_h = gate.projection.get("projected_600_conservative_hours", 0)
    if conservative_h > 30:
        return "NOT FEASIBLE FOR OFFICIAL RUN"
    return "FEASIBLE FOR OFFICIAL RUN"


def _decision_rationale(gate: FeasibilityGateResult, decision: str) -> str:
    p = gate.projection
    rs = gate.revive_stats
    bottleneck = (
        "REVIVE full-pipeline cycles dominate runtime (~"
        f"{rs.get('median_seconds', 0):.0f}s median per REVIVE cell vs "
        f"~{p.get('baseline_median_seconds', 0):.0f}s baseline median)."
    )
    return (
        f"Measured {gate.cells_run} cells in {_format_hours(gate.total_wall_seconds)}. "
        f"Projected 600-cell median: {p.get('projected_600_median_hours', 0):.1f} h; "
        f"conservative: {p.get('projected_600_conservative_hours', 0):.1f} h. "
        f"Peak RSS: {(gate.memory.get('peak_rss_bytes') or 0) / (1024*1024):.0f} MB. "
        f"Determinism: {gate.determinism.get('identical')}. "
        f"Resume: {gate.resume.get('fingerprints_match_reference')}. "
        f"{bottleneck}"
    )


def _decision_md(gate: FeasibilityGateResult) -> str:
    decision = _feasibility_decision(gate)
    return f"""# M13.13 Decision

## {decision}

{_decision_rationale(gate, decision)}
"""
