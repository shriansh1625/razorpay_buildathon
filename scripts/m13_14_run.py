"""M13.14 full pipeline performance engineering — development only."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path


def _write_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def cmd_profile(args: argparse.Namespace) -> None:
    from revive.benchmark.official.performance.profiling import profile_revive_cell

    out = Path("implementation/m13-14-performance")
    out.mkdir(parents=True, exist_ok=True)

    print("Profiling reference path (no cycle cache)...")
    ref_profile, ref_meta = profile_revive_cell(
        args.seed, args.profile, use_cycle_cache=False
    )
    (out / "profile-reference.json").write_text(
        json.dumps({**ref_profile.to_dict(), **ref_meta}, indent=2), encoding="utf-8"
    )

    print("Profiling optimized path (cycle cache)...")
    opt_profile, opt_meta = profile_revive_cell(
        args.seed, args.profile, use_cycle_cache=True
    )
    (out / "profile-optimized.json").write_text(
        json.dumps({**opt_profile.to_dict(), **opt_meta}, indent=2), encoding="utf-8"
    )

    speedup = ref_profile.total_seconds / max(opt_profile.total_seconds, 0.001)
    stages = ref_profile.stages
    lines = [
        "# M13.14 End-to-End Profile",
        "",
        "**Label:** DEVELOPMENT_ONLY — NOT official evidence",
        "",
        f"Cell: seed={args.seed} profile={args.profile} REVIVE",
        "",
        "## Total runtime",
        "",
        f"| Path | Seconds | Minutes |",
        f"|------|---------|---------|",
        f"| Reference (no cycle cache) | {ref_profile.total_seconds:.1f} | {ref_profile.total_seconds/60:.1f} |",
        f"| Optimized (cycle cache) | {opt_profile.total_seconds:.1f} | {opt_profile.total_seconds/60:.1f} |",
        f"| Speedup | {speedup:.2f}x | |",
        "",
        f"Cycles: {ref_profile.cycle_count}",
        "",
        "## Stage breakdown (reference path, cumulative seconds)",
        "",
        "| Stage | Seconds | Share | Class |",
        "|-------|---------|-------|-------|",
    ]
    for name in ("M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12"):
        s = stages[name]
        lines.append(
            f"| {name} | {s.seconds:.1f} | {ref_profile.stage_share(name)*100:.1f}% | {ref_profile.classify(name)} |"
        )
    lines.extend(
        [
            "",
            "## Counters (reference)",
            "",
            "```json",
            json.dumps(ref_profile.counters, indent=2),
            "```",
            "",
            "## Semantic check",
            "",
            f"- Reference cell hash: `{ref_meta['cell_result_hash']}`",
            f"- Optimized cell hash: `{opt_meta['cell_result_hash']}`",
            f"- Match: {ref_meta['cell_result_hash'] == opt_meta['cell_result_hash']}",
        ]
    )
    _write_md(out / "end-to-end-profile.md", "\n".join(lines) + "\n")

    stage_lines = ["# M13.14 Stage Breakdown", "", "See end-to-end-profile.md for totals.", ""]
    for name in stages:
        s = stages[name]
        stage_lines.append(f"- **{name}**: {s.seconds:.1f}s ({ref_profile.stage_share(name)*100:.1f}%)")
    _write_md(out / "stage-breakdown.md", "\n".join(stage_lines) + "\n")

    hotspots = [
        "# M13.14 Hotspot Analysis",
        "",
        "| Stage | Class | Share |",
        "|-------|-------|-------|",
    ]
    for name in stages:
        hotspots.append(
            f"| {name} | {ref_profile.classify(name)} | {ref_profile.stage_share(name)*100:.1f}% |"
        )
    _write_md(out / "hotspot-analysis.md", "\n".join(hotspots) + "\n")

    print(json.dumps({"speedup": speedup, "match": ref_meta["cell_result_hash"] == opt_meta["cell_result_hash"]}, indent=2))


def cmd_golden(args: argparse.Namespace) -> None:
    from revive.benchmark.official.performance.golden import GOLDEN_PATH, capture_golden_cell

    capture = capture_golden_cell(args.seed, args.profile, use_cycle_cache=False)
    capture.save(GOLDEN_PATH)
    print(f"golden saved {GOLDEN_PATH}")
    print(json.dumps(capture.to_dict(), indent=2))


def cmd_validate(args: argparse.Namespace) -> None:
    from revive.benchmark.official.performance.golden import (
        GOLDEN_PATH,
        GoldenCellCapture,
        capture_golden_cell,
    )

    golden = GoldenCellCapture.load(GOLDEN_PATH)
    optimized = capture_golden_cell(args.seed, args.profile, use_cycle_cache=True)
    match = golden.fingerprints["cell_result_hash"] == optimized.fingerprints["cell_result_hash"]
    print(json.dumps({"match": match, "golden": golden.fingerprints, "optimized": optimized.fingerprints}, indent=2))
    if not match:
        raise SystemExit(1)


def cmd_representatives(args: argparse.Namespace) -> None:
    from revive.benchmark.official.config import official_benchmark_config
    from revive.benchmark.official.performance.golden import capture_golden_cell
    from revive.config.policy_pack import official_sealed_policy_pack
    from revive.simulation.types import GenerationProfile

    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    profiles = [p.value for p in config.profile_set]
    results = []
    for profile in profiles:
        cap = capture_golden_cell(1, profile, use_cycle_cache=True)
        results.append({"seed": 1, "profile": profile, "hash": cap.fingerprints["cell_result_hash"]})
    stress = capture_golden_cell(2, "BALANCED", use_cycle_cache=True)
    results.append({"seed": 2, "profile": "BALANCED", "hash": stress.fingerprints["cell_result_hash"]})
    out = Path("implementation/m13-14-performance/representative-hashes.json")
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"wrote {out}")


def cmd_parallel(args: argparse.Namespace) -> None:
    from revive.benchmark.official.cells.plan import BenchmarkCell
    from revive.benchmark.official.feasibility.gate import feasibility_benchmark_config
    from revive.benchmark.official.performance.parallel import run_cells_parallel
    from revive.config.policy_pack import official_sealed_policy_pack

    pack = official_sealed_policy_pack()
    config = feasibility_benchmark_config(policy_pack=pack)
    revive_cells = (
        BenchmarkCell(index=5, seed=1, profile="BALANCED", policy_id="REVIVE"),
        BenchmarkCell(index=31, seed=2, profile="BALANCED", policy_id="REVIVE"),
    )
    root = Path("artefacts/benchmark/performance/DEVELOPMENT_PARALLEL_ONLY")

    seq = run_cells_parallel(
        config=config,
        policy_pack=pack,
        cells=revive_cells,
        cells_root=root / "workers-1",
        workers=1,
    )
    par = run_cells_parallel(
        config=config,
        policy_pack=pack,
        cells=revive_cells,
        cells_root=root / "workers-2",
        workers=2,
    )
    seq_fp = seq.fingerprints()
    par_fp = par.fingerprints()
    match = seq_fp == par_fp
    speedup = seq.wall_seconds / max(par.wall_seconds, 0.001)
    report = {
        "label": "DEVELOPMENT_PARALLEL_ONLY",
        "revive_cells": len(revive_cells),
        "workers_1_wall_seconds": seq.wall_seconds,
        "workers_2_wall_seconds": par.wall_seconds,
        "speedup": speedup,
        "fingerprints_match": match,
    }
    out = Path("implementation/m13-14-performance/parallel-feasibility.md")
    _write_md(
        out,
        "\n".join(
            [
                "# M13.14 Parallel Feasibility",
                "",
                "**Label:** DEVELOPMENT_PARALLEL_ONLY",
                "",
                f"| Workers | Wall (s) |",
                f"|---------|----------|",
                f"| 1 | {seq.wall_seconds:.1f} |",
                f"| 2 | {par.wall_seconds:.1f} |",
                "",
                f"Speedup: {speedup:.2f}x",
                f"Fingerprints match sequential: **{match}**",
            ]
        )
        + "\n",
    )
    print(json.dumps(report, indent=2))


def cmd_decision(args: argparse.Namespace) -> None:
    out = Path("implementation/m13-14-performance")
    ref = json.loads((out / "profile-reference.json").read_text(encoding="utf-8"))
    opt = json.loads((out / "profile-optimized.json").read_text(encoding="utf-8"))
    speedup = ref["total_seconds"] / max(opt["total_seconds"], 0.001)
    semantic_match = ref["cell_result_hash"] == opt["cell_result_hash"]

    revive_median = opt["total_seconds"]
    projected_600_h = (revive_median * 120 + 31 * 480) / 3600 * (ref["total_seconds"] / opt["total_seconds"])

    ready = semantic_match and speedup >= 1.15
    decision = "PERFORMANCE READY FOR OFFICIAL RUN" if ready else "PERFORMANCE NOT READY"
    bottleneck = "M7+M8" if opt["stages"]["M7"]["seconds"] + opt["stages"]["M8"]["seconds"] > opt["total_seconds"] * 0.5 else "see hotspot-analysis.md"

    _write_md(
        out / "M13.14-decision.md",
        f"# M13.14 Decision\n\n## {decision}\n\n"
        f"Semantic match: {semantic_match}. Speedup: {speedup:.2f}x. "
        f"Projected 600-cell median ~{projected_600_h:.1f}h (rough). "
        f"Remaining hotspot: {bottleneck}.\n",
    )
    print(decision)


def main() -> None:
    parser = argparse.ArgumentParser(description="M13.14 performance engineering (NOT official benchmark)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("profile")
    p.add_argument("--seed", type=int, default=2)
    p.add_argument("--profile", default="BALANCED")
    p.set_defaults(func=cmd_profile)
    g = sub.add_parser("golden")
    g.add_argument("--seed", type=int, default=2)
    g.add_argument("--profile", default="BALANCED")
    g.set_defaults(func=cmd_golden)
    v = sub.add_parser("validate")
    v.add_argument("--seed", type=int, default=2)
    v.add_argument("--profile", default="BALANCED")
    v.set_defaults(func=cmd_validate)
    r = sub.add_parser("representatives")
    r.set_defaults(func=cmd_representatives)
    pl = sub.add_parser("parallel")
    pl.set_defaults(func=cmd_parallel)
    d = sub.add_parser("decision")
    d.set_defaults(func=cmd_decision)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
