"""Minimal CLI — M2 adds dataset generation for development."""

import argparse
from pathlib import Path


def main() -> None:
    from revive.__version__ import __version__

    parser = argparse.ArgumentParser(prog="revive")
    parser.add_argument("--version", action="version", version=f"PAYVANTA {__version__}")
    sub = parser.add_subparsers(dest="command")

    gen = sub.add_parser("generate-dataset", help="Generate synthetic dataset (M2)")
    gen.add_argument("--seed", type=int, default=42)
    gen.add_argument("--profile", default="BALANCED")
    gen.add_argument("--opportunities", type=int, default=80)
    gen.add_argument("--output", type=Path, default=Path("artefacts/datasets/dev"))

    bench = sub.add_parser("benchmark", help="Run M13 benchmark engine")
    bench.add_argument(
        "--mode",
        choices=["development", "official", "preflight"],
        default="development",
    )
    bench.add_argument(
        "--output",
        type=Path,
        default=Path("artefacts/benchmark"),
    )
    bench.add_argument("--reproduce", action="store_true")
    bench.add_argument(
        "--stress-cells",
        type=int,
        default=None,
        help="M13.11 development stress mode (requires --output)",
    )
    bench.add_argument(
        "--stop-after-cell",
        type=int,
        default=None,
        help="M13.11 stop after N cells (checkpoint/resume testing)",
    )
    bench.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Parallel seed/profile groups (default 1 = sequential legacy behavior)",
    )

    cal = sub.add_parser("calibrate", help="Run M13.5 benchmark calibration diagnostics")
    cal.add_argument(
        "--output",
        type=Path,
        default=Path("implementation/m13-5-benchmark-calibration"),
    )
    cal.add_argument("--skip-reproduction", action="store_true")

    repair = sub.add_parser("repair-calibrate", help="M13.6 structural repair re-calibration")
    repair.add_argument(
        "--output",
        type=Path,
        default=Path("implementation/m13-6-structural-repair"),
    )
    repair.add_argument("--skip-reproduction", action="store_true")

    thesis = sub.add_parser("thesis-audit", help="M13.7 portfolio allocation thesis audit")
    thesis.add_argument(
        "--output",
        type=Path,
        default=Path("implementation/m13-7-allocation-thesis"),
    )

    freeze = sub.add_parser("freeze-decision", help="M13.8 benchmark configuration freeze decision")
    freeze.add_argument(
        "--output",
        type=Path,
        default=Path("implementation/m13-8-benchmark-freeze-decision"),
    )

    freeze = sub.add_parser("freeze-seal", help="M13.10 seal official benchmark config (no run)")
    freeze.add_argument(
        "--output",
        type=Path,
        default=Path("artefacts/benchmark/official"),
    )

    feas = sub.add_parser(
        "feasibility-gate",
        help="M13.13 frozen-scale runtime feasibility (NOT official benchmark)",
    )
    feas.add_argument(
        "--output",
        type=Path,
        default=Path("artefacts/benchmark/feasibility/DEVELOPMENT_FEASIBILITY_ONLY"),
    )
    feas.add_argument(
        "--reports",
        type=Path,
        default=Path("implementation/m13-13-feasibility"),
    )
    feas.add_argument("--skip-resume", action="store_true")
    feas.add_argument("--skip-determinism", action="store_true")

    room = sub.add_parser("control-room", help="PAYVANTA Recovery Control Room (demo UI)")
    room.add_argument("--host", default="127.0.0.1")
    room.add_argument("--port", type=int, default=8765)

    args = parser.parse_args()
    if args.command == "generate-dataset":
        from revive.simulation import GeneratorConfig, assert_dataset_valid, generate_dataset
        from revive.simulation.io import write_dataset
        from revive.simulation.types import GenerationProfile

        config = GeneratorConfig(
            seed=args.seed,
            profile=GenerationProfile(args.profile),
            opportunity_count=args.opportunities,
        )
        dataset = generate_dataset(config)
        assert_dataset_valid(dataset)
        path = write_dataset(dataset, args.output / f"seed_{args.seed}")
        print(f"Dataset written to {path}")
        print(f"dataset_hash={dataset.dataset_hash}")
    elif args.command == "benchmark":
        from revive.benchmark.official.config import BenchmarkMode
        from revive.benchmark.official.reproduce import reproduce_benchmark
        from revive.benchmark.official.runner import execute_benchmark

        mode_map = {
            "official": BenchmarkMode.OFFICIAL,
            "preflight": BenchmarkMode.PREFLIGHT,
            "development": BenchmarkMode.DEVELOPMENT,
        }
        mode = mode_map[args.mode]
        if args.reproduce:
            rep = reproduce_benchmark(mode=mode)
            print(f"reproduction_identical={rep.identical}")
            print(f"fingerprint_1={rep.first_hash}")
            print(f"fingerprint_2={rep.second_hash}")
        else:
            result = execute_benchmark(
                mode=mode,
                output_dir=args.output,
                stress_cells=args.stress_cells,
                stop_after_cell=args.stop_after_cell,
                workers=args.workers,
            )
            print(f"mode={result.mode.value}")
            print(f"blocked={result.blocked}")
            print(f"workers={result.metadata.get('workers', 1)}")
            print(f"config_hash={result.config_hash}")
            if result.metadata.get("frozen_experiment_reference_hash"):
                print(
                    "frozen_experiment_reference_hash="
                    f"{result.metadata['frozen_experiment_reference_hash']}"
                )
            if result.metadata.get("implementation_revision"):
                print(f"implementation_revision={result.metadata['implementation_revision']}")
            print(f"validation={result.validation_status}")
            if result.mode == BenchmarkMode.PREFLIGHT:
                print(f"preflight_passed={result.metadata.get('preflight_passed')}")
                print("PREFLIGHT_ONLY — NOT BENCHMARK EVIDENCE")
            if result.blocked:
                print("BENCHMARK BLOCKED — FREEZE INCOMPLETE")
                for reason in result.freeze_reasons:
                    print(f"  - {reason}")
            else:
                print(f"runs={len(result.aggregate.per_run)}")
                for pid in ("B0", "B1", "B2", "B3", "REVIVE"):
                    s = result.aggregate.policy_summary(pid)
                    if s:
                        print(
                            f"{pid}: M-10_median={s.get('M-10_median_paise')} paise"
                        )
            if result.artifact_path:
                print(f"artifacts={result.artifact_path}")
    elif args.command == "calibrate":
        from revive.benchmark.calibration import run_calibration_diagnostics, write_calibration_reports

        report = run_calibration_diagnostics(skip_reproduction=args.skip_reproduction)
        out = write_calibration_reports(report, args.output)
        print(f"calibration_version={report.version}")
        print(f"decision={report.freeze_readiness.decision}")
        print(f"baseline_separation={report.baseline_separation.classification}")
        print(f"scarcity={report.scarcity.classification}")
        print(f"b3_revive={report.b3_revive.classification}")
        print(f"reports={out}")
    elif args.command == "repair-calibrate":
        from revive.benchmark.calibration.m13_6 import run_m13_6_recalibration
        from revive.benchmark.calibration.m13_6_report import write_m13_6_reports

        report = run_m13_6_recalibration(skip_reproduction=args.skip_reproduction)
        out = write_m13_6_reports(report, args.output)
        print(f"version={report.version}")
        print(f"scarcity_official={report.scarcity_official_scale.classification}")
        print(f"b3_revive_official={report.b3_revive_official_scale.classification}")
        print(f"decision={report.freeze_readiness.decision}")
        print(f"reports={out}")
    elif args.command == "thesis-audit":
        from revive.benchmark.calibration.thesis_audit.runner import run_m13_7_audit
        from revive.benchmark.calibration.thesis_audit.report import write_m13_7_reports

        report = run_m13_7_audit()
        out = write_m13_7_reports(report, args.output)
        print(f"version={report.version}")
        print(f"thesis={report.thesis_classification}")
        print(f"reports={out}")
    elif args.command == "freeze-decision":
        from revive.benchmark.calibration.m13_8.runner import run_m13_8_decision
        from revive.benchmark.calibration.m13_8.report import write_m13_8_reports

        report = run_m13_8_decision()
        out = write_m13_8_reports(report, args.output)
        print(f"version={report.version}")
        print(f"recommended={report.recommended_candidate_id}")
        print(f"decision={report.decision}")
        print(f"reports={out}")
    elif args.command == "freeze-seal":
        from revive.benchmark.official.seal import seal_official_benchmark

        result = seal_official_benchmark(output_dir=args.output)
        print(f"freeze_complete={result.freeze_complete}")
        print(f"config_hash={result.config_hash}")
        print(f"manifest={result.manifest_path}")
        if not result.freeze_complete:
            for reason in result.blocked_reasons:
                print(f"BLOCKED: {reason}")
    elif args.command == "feasibility-gate":
        from revive.benchmark.official.feasibility.gate import (
            FEASIBILITY_LABEL,
            run_feasibility_gate,
            write_feasibility_reports,
        )

        print(f"label={FEASIBILITY_LABEL}")
        print("NOT OFFICIAL BENCHMARK EVIDENCE")
        gate = run_feasibility_gate(
            args.output,
            skip_resume=args.skip_resume,
            skip_determinism=args.skip_determinism,
            progress=True,
        )
        paths = write_feasibility_reports(gate, args.reports)
        print(f"cells={gate.cells_run} wall_seconds={gate.total_wall_seconds:.1f}")
        print(f"median_projected_hours={gate.projection.get('median_estimate_hours')}")
        print(f"reports={paths}")
    elif args.command == "control-room":
        from revive.product.server import serve

        serve(args.host, args.port)
    else:
        print(
            f"PAYVANTA {__version__} — use generate-dataset, benchmark, calibrate, "
            "repair-calibrate, thesis-audit, freeze-decision, freeze-seal, "
            "feasibility-gate, or control-room."
        )
