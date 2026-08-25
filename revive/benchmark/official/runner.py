"""Official benchmark execution entry — M13 / M13.11 cell runner."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from revive.config.policy_pack import default_draft_policy_pack, official_sealed_policy_pack

from revive.benchmark.official.aggregate import BenchmarkAggregate
from revive.benchmark.official.artifacts import write_benchmark_artifacts
from revive.benchmark.official.cells.runner import run_cell_benchmark, run_stress_benchmark
from revive.benchmark.official.config import (
    BenchmarkMode,
    OfficialBenchmarkConfig,
    development_benchmark_config,
    official_benchmark_config,
    preflight_benchmark_config,
)
from revive.benchmark.official.falsification import run_falsification_tests
from revive.benchmark.official.freeze import check_freeze_prerequisites
from revive.benchmark.official.freeze_constants import (
    BENCHMARK_RUNNER_VERSION,
    IMPLEMENTATION_REVISION,
)
from revive.benchmark.official.hash import frozen_experiment_reference_hash, official_benchmark_config_hash
from revive.benchmark.official.policies import ALL_BENCHMARK_POLICIES
from revive.benchmark.official.preflight.gate import PREFLIGHT_LABEL, evaluate_preflight_gate
from revive.benchmark.official.validate import validate_benchmark_result
from revive.simulation.types import GenerationProfile


@dataclass
class BenchmarkRunResult:
    mode: BenchmarkMode
    blocked: bool
    config: OfficialBenchmarkConfig
    config_hash: str
    aggregate: BenchmarkAggregate
    validation_status: str
    artifact_path: Path | None = None
    freeze_reasons: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "blocked": self.blocked,
            "config_hash": self.config_hash,
            "validation_status": self.validation_status,
            "artifact_path": str(self.artifact_path) if self.artifact_path else None,
            "freeze_reasons": list(self.freeze_reasons),
            "aggregate": self.aggregate.to_dict(),
            "metadata": self.metadata,
        }


def execute_benchmark(
    *,
    mode: BenchmarkMode = BenchmarkMode.DEVELOPMENT,
    output_dir: Path | None = None,
    config: OfficialBenchmarkConfig | None = None,
    policy_pack=None,
    stop_after_cell: int | None = None,
    max_cells: int | None = None,
    stress_cells: int | None = None,
    workers: int = 1,
    progress: bool = True,
) -> BenchmarkRunResult:
    """Execute benchmark matrix or report BLOCKED for official mode."""
    pack = policy_pack
    if pack is None:
        if mode in (BenchmarkMode.OFFICIAL, BenchmarkMode.PREFLIGHT):
            pack = official_sealed_policy_pack()
        else:
            pack = default_draft_policy_pack()

    if config is None:
        if mode == BenchmarkMode.OFFICIAL:
            config = official_benchmark_config(policy_pack=pack)
        elif mode == BenchmarkMode.PREFLIGHT:
            config = preflight_benchmark_config(policy_pack=pack)
        else:
            config = development_benchmark_config(policy_pack=pack)

    if pack.is_frozen_for_benchmark:
        reference_config = official_benchmark_config(policy_pack=pack)
        frozen_experiment_hash = frozen_experiment_reference_hash(reference_config)
    else:
        frozen_experiment_hash = None

    if stress_cells is not None and mode == BenchmarkMode.DEVELOPMENT:
        groups_needed = (
            stress_cells + len(ALL_BENCHMARK_POLICIES) - 1
        ) // len(ALL_BENCHMARK_POLICIES)
        config = development_benchmark_config(
            policy_pack=pack,
            seeds=tuple(range(1, max(1, groups_needed) + 1)),
            profiles=(GenerationProfile.BALANCED,),
        )

    config_hash = official_benchmark_config_hash(config)
    freeze = check_freeze_prerequisites(
        config,
        policy_pack=pack,
        preflight=mode == BenchmarkMode.PREFLIGHT,
    )

    blocked = mode in (BenchmarkMode.OFFICIAL, BenchmarkMode.PREFLIGHT) and not freeze.complete
    aggregate = BenchmarkAggregate()
    execution_metadata: dict[str, Any] = {}

    if not blocked:
        cells_root = (output_dir / "cells") if output_dir is not None else None
        progress_stream = sys.stdout if progress else None
        benchmark_mode = mode.value

        if stress_cells is not None:
            if cells_root is None:
                raise ValueError("stress_cells requires output_dir for checkpoint persistence")
            cell_result = run_stress_benchmark(
                config=config,
                policy_pack=pack,
                config_hash=config_hash,
                cells_root=cells_root,
                cell_count=stress_cells,
                progress=progress,
                progress_stream=progress_stream,
            )
        else:
            cell_result = run_cell_benchmark(
                config=config,
                policy_pack=pack,
                config_hash=config_hash,
                cells_root=cells_root,
                max_cells=max_cells,
                stop_after_cell=stop_after_cell,
                workers=workers,
                benchmark_mode=benchmark_mode,
                progress=progress,
                progress_stream=progress_stream,
                require_complete_aggregate=stop_after_cell is None and max_cells is None,
            )
        aggregate = cell_result.aggregate
        execution_metadata = {
            "cells_planned": cell_result.cells_planned,
            "cells_executed": cell_result.cells_executed,
            "cells_skipped": cell_result.cells_skipped,
            "cells_total_official": cell_result.cells_total_official,
            "cells_root": str(cell_result.cells_root),
            **cell_result.metadata,
        }

    expected_runs = (
        len(config.seed_set) * len(config.profile_set) * len(ALL_BENCHMARK_POLICIES)
    )
    if stop_after_cell is not None or max_cells is not None or stress_cells is not None:
        expected_runs = len(aggregate.per_run)

    validation = validate_benchmark_result(
        config, config_hash, aggregate, expected_runs if not blocked else 0
    )

    if blocked:
        validation.status = "BENCHMARK_BLOCKED"
        validation.valid = False
        validation.reasons.append("BENCHMARK BLOCKED — FREEZE INCOMPLETE")

    falsification = run_falsification_tests(aggregate) if not blocked else run_falsification_tests(
        BenchmarkAggregate()
    )

    preflight_gate = None
    if mode == BenchmarkMode.PREFLIGHT and not blocked:
        preflight_gate = evaluate_preflight_gate(aggregate)

    artifact_path = None
    if output_dir is not None:
        artifact_path = write_benchmark_artifacts(
            output_dir,
            config,
            config_hash,
            aggregate,
            validation,
            falsification,
            freeze,
            mode=mode.value,
            blocked=blocked,
            frozen_experiment_hash=frozen_experiment_hash,
            preflight_gate=preflight_gate,
            implementation_revision=IMPLEMENTATION_REVISION,
            runner_version=BENCHMARK_RUNNER_VERSION,
        )

    return BenchmarkRunResult(
        mode=mode,
        blocked=blocked,
        config=config,
        config_hash=config_hash,
        aggregate=aggregate,
        validation_status=validation.status,
        artifact_path=artifact_path,
        freeze_reasons=freeze.blocked_reasons if blocked else (),
        metadata={
            "run_count": len(aggregate.per_run),
            "runner": "cell_streaming_m13_11",
            "workers": workers,
            "implementation_revision": IMPLEMENTATION_REVISION,
            "benchmark_runner_version": BENCHMARK_RUNNER_VERSION,
            "frozen_experiment_reference_hash": frozen_experiment_hash,
            "preflight_label": PREFLIGHT_LABEL if mode == BenchmarkMode.PREFLIGHT else None,
            "preflight_passed": preflight_gate.passed if preflight_gate else None,
            **execution_metadata,
        },
    )
