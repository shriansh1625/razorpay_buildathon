"""M13.13 official benchmark run feasibility gate."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="M13.13 feasibility gate (NOT official benchmark)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artefacts/benchmark/feasibility/DEVELOPMENT_FEASIBILITY_ONLY"),
    )
    parser.add_argument(
        "--reports",
        type=Path,
        default=Path("implementation/m13-13-feasibility"),
    )
    parser.add_argument("--skip-resume", action="store_true")
    parser.add_argument("--skip-determinism", action="store_true")
    args = parser.parse_args()

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
    print(f"cells={gate.cells_run} wall={gate.total_wall_seconds:.1f}s")
    print(f"aggregate_fingerprint={gate.aggregate_fingerprint}")
    print(f"projected_600_median_hours={gate.projection.get('projected_600_median_hours')}")
    print(f"reports={paths}")


if __name__ == "__main__":
    main()
