"""Cell-by-cell benchmark runner — M13.11."""

from __future__ import annotations

import gc
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, TextIO

from revive.benchmark.official.aggregate import BenchmarkAggregate
from revive.benchmark.official.cells.plan import (
    BenchmarkCell,
    official_cell_total,
    plan_benchmark_cells,
)
from revive.benchmark.official.cells.store import (
    BenchmarkConfigMismatchError,
    CellRecordContext,
    CellStore,
    aggregate_from_store,
    assert_checkpoint_config_compatible,
)
from revive.benchmark.official.cells.telemetry import (
    CellTelemetry,
    PeakRssTracker,
    current_rss_bytes,
    monotonic_seconds,
)
from revive.benchmark.official.config import (
    OfficialBenchmarkConfig,
    generator_config_for_cell,
)
from revive.benchmark.official.metrics import PolicyRunMetrics
from revive.benchmark.official.policies import ALL_BENCHMARK_POLICIES, BenchmarkPolicyId
from revive.benchmark.official.policy_runner import run_policy_on_world
from revive.benchmark.official.world import SharedWorldBundle, generate_shared_world
from revive.config.policy_pack import PolicyPack
from revive.simulation.types import GenerationProfile


@dataclass
class CellExecutionResult:
    cells_planned: int
    cells_executed: int
    cells_skipped: int
    cells_total_official: int
    aggregate: BenchmarkAggregate
    cells_root: Path
    telemetry_samples: list[CellTelemetry] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


def _format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, rem = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m{rem:.0f}s"
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h{int(minutes)}m"


def _format_rss(rss: int | None) -> str:
    if rss is None:
        return "n/a"
    if rss >= 1024 * 1024:
        return f"{rss / (1024 * 1024):.1f}MB"
    return f"{rss / 1024:.0f}KB"


def _progress_line(
    cell: BenchmarkCell,
    *,
    cells_total: int,
    elapsed: float,
    cell_duration: float,
    completed: int,
    remaining: int,
    eta_seconds: float | None,
) -> str:
    eta = "calculating" if eta_seconds is None else _format_duration(eta_seconds)
    return (
        f"[{cell.index:03d}/{cells_total:03d}] "
        f"seed={cell.seed} profile={cell.profile} policy={cell.policy_id} | "
        f"elapsed={_format_duration(elapsed)} "
        f"cell={_format_duration(cell_duration)} "
        f"completed={completed} remaining={remaining} "
        f"ETA={eta}"
    )


def _policy_enum(policy_id: str) -> BenchmarkPolicyId:
    return BenchmarkPolicyId(policy_id)


def _run_single_policy_cell(
    bundle: SharedWorldBundle,
    cell: BenchmarkCell,
    policy_pack: PolicyPack,
) -> PolicyRunMetrics:
    return run_policy_on_world(bundle, _policy_enum(cell.policy_id), policy_pack)


def run_cell_benchmark(
    *,
    config: OfficialBenchmarkConfig,
    policy_pack: PolicyPack,
    config_hash: str,
    cells_root: Path | None = None,
    cells: tuple[BenchmarkCell, ...] | None = None,
    cells_total_checkpoint: int | None = None,
    max_cells: int | None = None,
    stop_after_cell: int | None = None,
    workers: int = 1,
    benchmark_mode: str = "development",
    progress: bool = True,
    progress_stream: TextIO | None = None,
    require_complete_aggregate: bool = True,
) -> CellExecutionResult:
    """
    Execute benchmark one cell at a time with bounded memory and checkpointing.

    When ``cells_root`` is None, results are written to a temporary directory
    that is removed after aggregation (lifecycle matches persisted runs).
    """
    cells_total_official = (
        cells_total_checkpoint
        if cells_total_checkpoint is not None
        else (len(cells) if cells is not None else official_cell_total(config))
    )
    if cells is not None:
        planned = cells
        if max_cells is not None:
            planned = planned[:max_cells]
    else:
        planned = plan_benchmark_cells(config, max_cells=max_cells)
    if stop_after_cell is not None:
        if cells is not None:
            planned = planned[:stop_after_cell]
        else:
            planned = tuple(c for c in planned if c.index <= stop_after_cell)

    owns_temp = cells_root is None
    temp_dir: tempfile.TemporaryDirectory[str] | None = None
    if cells_root is None:
        temp_dir = tempfile.TemporaryDirectory(prefix="revive-bench-cells-")
        cells_root = Path(temp_dir.name)

    store = CellStore(
        cells_root,
        CellRecordContext(
            config_hash=config_hash,
            benchmark_version=config.benchmark_version,
            policy_pack_version=config.policy_pack_version,
            policy_pack_hash=config.policy_pack_hash,
            metric_version=config.metric_version,
        ),
    )
    assert_checkpoint_config_compatible(store, cells_total=cells_total_official)

    if workers > 1:
        from revive.benchmark.official.cells.parallel import (
            run_cell_benchmark_parallel,
            validate_workers,
        )

        validate_workers(workers)
        return run_cell_benchmark_parallel(
            config=config,
            policy_pack=policy_pack,
            config_hash=config_hash,
            store=store,
            planned=planned,
            cells_total_official=cells_total_official,
            workers=workers,
            mode=benchmark_mode,
            progress=progress,
            progress_stream=progress_stream,
            require_complete_aggregate=require_complete_aggregate
            and stop_after_cell is None
            and max_cells is None,
        )

    stream = progress_stream
    run_start = monotonic_seconds()
    executed = 0
    skipped = 0
    completed = store.count_valid_cells(planned)
    telemetry_samples: list[CellTelemetry] = []
    last_completed: BenchmarkCell | None = None
    cell_durations: list[float] = []

    current_seed: int | None = None
    current_profile: str | None = None
    bundle: SharedWorldBundle | None = None
    group_start: float | None = None
    policies_in_group = 0

    def flush_group_summary() -> None:
        nonlocal bundle, group_start, policies_in_group
        if current_seed is None or current_profile is None or group_start is None:
            return
        if progress and stream is not None and policies_in_group > 0:
            group_elapsed = monotonic_seconds() - group_start
            rss = current_rss_bytes()
            stream.write(
                f"seed={current_seed} profile={current_profile}: "
                f"{policies_in_group}/{len(ALL_BENCHMARK_POLICIES)} policies complete | "
                f"group_duration={_format_duration(group_elapsed)} | "
                f"rss={_format_rss(rss)}\n"
            )
            stream.flush()
        if bundle is not None:
            del bundle
            bundle = None
        gc.collect()
        group_start = None
        policies_in_group = 0

    try:
        for cell in planned:
            if cell.seed != current_seed or cell.profile != current_profile:
                flush_group_summary()
                current_seed = cell.seed
                current_profile = cell.profile
                group_start = monotonic_seconds()
                policies_in_group = 0
                group_cells = tuple(
                    c
                    for c in planned
                    if c.seed == cell.seed and c.profile == cell.profile
                )
                needs_world = any(not store.is_cell_valid(c) for c in group_cells)
                if needs_world:
                    profile_enum = GenerationProfile(cell.profile)
                    gen_config = generator_config_for_cell(config, cell.seed, profile_enum)
                    bundle = generate_shared_world(gen_config)
                else:
                    bundle = None

            if store.is_cell_valid(cell):
                skipped += 1
                completed = store.count_valid_cells(planned)
                policies_in_group += 1
                if progress and stream is not None:
                    elapsed = monotonic_seconds() - run_start
                    remaining = len(planned) - cell.index
                    stream.write(
                        _progress_line(
                            cell,
                            cells_total=cells_total_official,
                            elapsed=elapsed,
                            cell_duration=0.0,
                            completed=completed,
                            remaining=remaining,
                            eta_seconds=_estimate_eta(cell_durations, remaining),
                        )
                        + " (skipped)\n"
                    )
                    stream.flush()
                continue

            if bundle is None:
                profile_enum = GenerationProfile(cell.profile)
                gen_config = generator_config_for_cell(config, cell.seed, profile_enum)
                bundle = generate_shared_world(gen_config)

            rss_before = current_rss_bytes()
            tracker = PeakRssTracker()
            cell_start = monotonic_seconds()
            metrics = _run_single_policy_cell(bundle, cell, policy_pack)
            tracker.sample()
            cell_duration = monotonic_seconds() - cell_start
            cell_durations.append(cell_duration)
            rss_after = current_rss_bytes()

            telemetry = CellTelemetry(
                rss_before_bytes=rss_before,
                rss_after_bytes=rss_after,
                peak_rss_bytes=tracker.peak,
                duration_seconds=cell_duration,
            )
            telemetry_samples.append(telemetry)
            store.write_cell(cell, metrics, telemetry=telemetry.to_dict())
            del metrics

            executed += 1
            policies_in_group += 1
            last_completed = cell
            completed = store.count_valid_cells(planned)
            store.write_checkpoint(
                cells_completed=completed,
                cells_total=cells_total_official,
                last_cell=last_completed,
            )

            if progress and stream is not None:
                elapsed = monotonic_seconds() - run_start
                remaining = len(planned) - cell.index
                stream.write(
                    _progress_line(
                        cell,
                        cells_total=cells_total_official,
                        elapsed=elapsed,
                        cell_duration=cell_duration,
                        completed=completed,
                        remaining=remaining,
                        eta_seconds=_estimate_eta(cell_durations, remaining),
                    )
                    + "\n"
                )
                stream.flush()

            if cell.policy_id == ALL_BENCHMARK_POLICIES[-1].value:
                flush_group_summary()

        flush_group_summary()

        aggregate = aggregate_from_store(
            store,
            config,
            cells=planned,
            require_complete=require_complete_aggregate
            and stop_after_cell is None
            and max_cells is None,
        )
    finally:
        if temp_dir is not None and owns_temp:
            temp_dir.cleanup()

    return CellExecutionResult(
        cells_planned=len(planned),
        cells_executed=executed,
        cells_skipped=skipped,
        cells_total_official=cells_total_official,
        aggregate=aggregate,
        cells_root=cells_root,
        telemetry_samples=telemetry_samples,
        metadata={
            "cells_root": str(cells_root),
            "stop_after_cell": stop_after_cell,
            "max_cells": max_cells,
            "workers": workers,
        },
    )


def _estimate_eta(durations: list[float], remaining: int) -> float | None:
    if not durations or remaining <= 0:
        return None
    if len(durations) < 2:
        return None
    avg = sum(durations) / len(durations)
    return avg * remaining


def run_stress_benchmark(
    *,
    config: OfficialBenchmarkConfig,
    policy_pack: PolicyPack,
    config_hash: str,
    cells_root: Path,
    cell_count: int,
    progress: bool = True,
    progress_stream: TextIO | None = None,
) -> CellExecutionResult:
    """Development stress mode — same lifecycle as official, limited cell count."""
    return run_cell_benchmark(
        config=config,
        policy_pack=policy_pack,
        config_hash=config_hash,
        cells_root=cells_root,
        max_cells=cell_count,
        progress=progress,
        progress_stream=progress_stream,
        require_complete_aggregate=False,
    )
