"""Parallel seed/profile group execution for official cell runner — M13.15 / M13.20."""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import TextIO

from revive.benchmark.official.cells.parallel_worker import (
    config_to_worker_payload,
    run_seed_profile_group,
)
from revive.benchmark.official.cells.plan import BenchmarkCell, BenchmarkGroup, plan_benchmark_groups
from revive.benchmark.official.cells.progress import (
    aggregate_progress_line,
    cell_progress_line,
    estimate_eta,
    format_rss,
    group_header_line,
    group_summary_line,
)
from revive.benchmark.official.cells.runner import CellExecutionResult
from revive.benchmark.official.cells.store import CellStore, aggregate_from_store, sync_checkpoint_from_persisted
from revive.benchmark.official.cells.telemetry import CellTelemetry, current_rss_bytes, monotonic_seconds
from revive.benchmark.official.config import OfficialBenchmarkConfig
from revive.benchmark.official.policies import ALL_BENCHMARK_POLICIES
from revive.config.policy_pack import PolicyPack

# Conservative ceiling for an ~8 GB machine (matches M13.13 feasibility gate).
PARALLEL_MEMORY_SAFE_BYTES = 6 * 1024 * 1024 * 1024


def validate_workers(workers: int) -> int:
    cpu = os.cpu_count() or 1
    if workers < 1:
        raise ValueError(f"--workers must be >= 1, got {workers}")
    if workers > cpu:
        raise ValueError(f"--workers must be <= CPU count ({cpu}), got {workers}")
    return workers


def verify_group_persisted(store: CellStore, group: BenchmarkGroup) -> int:
    """
    Fail closed if a worker returned without persisting every cell in the group.

    Returns the number of valid cells in the group.
    """
    valid = sum(1 for cell in group.cells if store.is_cell_valid(cell))
    if valid != len(group.cells):
        raise RuntimeError(
            "parallel group incomplete after worker return: "
            f"seed={group.seed} profile={group.profile} "
            f"({valid}/{len(group.cells)} cells persisted)"
        )
    return valid


def _is_official_mode(mode: str) -> bool:
    return str(mode).upper() in {"OFFICIAL", "PREFLIGHT"}


def _emit_group_progress(
    *,
    stream: TextIO,
    group: BenchmarkGroup,
    group_index: int,
    groups_total: int,
    groups_completed: int,
    store: CellStore,
    planned: tuple[BenchmarkCell, ...],
    cells_total_official: int,
    group_seconds: float,
    elapsed: float,
    cell_durations: list[float],
    parent_rss: int | None,
) -> None:
    policies_complete = verify_group_persisted(store, group)
    cells_completed = store.count_valid_cells(planned)
    per_cell_duration = group_seconds / max(1, len(group.cells))

    stream.write(group_header_line(group, group_index=group_index, groups_total=groups_total) + "\n")
    stream.write(
        group_summary_line(
            group,
            policies_complete=policies_complete,
            policies_total=len(ALL_BENCHMARK_POLICIES),
            group_duration=group_seconds,
            rss=parent_rss,
        )
        + "\n"
    )
    for cell in group.cells:
        remaining = len(planned) - cell.index
        stream.write(
            cell_progress_line(
                cell,
                cells_total=cells_total_official,
                elapsed=elapsed,
                cell_duration=per_cell_duration,
                completed=cells_completed,
                remaining=remaining,
                eta_seconds=estimate_eta(cell_durations, remaining),
            )
            + "\n"
        )
    stream.write(
        aggregate_progress_line(
            groups_completed=groups_completed,
            groups_total=groups_total,
            cells_completed=cells_completed,
            cells_total=cells_total_official,
        )
        + "\n"
    )
    stream.flush()


def run_cell_benchmark_parallel(
    *,
    config: OfficialBenchmarkConfig,
    policy_pack: PolicyPack,
    config_hash: str,
    store: CellStore,
    planned: tuple[BenchmarkCell, ...],
    cells_total_official: int,
    workers: int,
    mode: str,
    progress: bool,
    progress_stream: TextIO | None,
    require_complete_aggregate: bool,
    reconciliation: dict[str, object] | None = None,
) -> CellExecutionResult:
    """Execute independent seed/profile groups concurrently."""
    groups = plan_benchmark_groups(planned)
    groups_total = len(groups)
    group_index_by_key = {group.key: index for index, group in enumerate(groups, start=1)}
    config_payload = config_to_worker_payload(config, policy_pack)
    config_payload["mode"] = mode
    config_payload["checkpoint_planned_cells"] = [c.to_dict() for c in planned]
    config_payload["cells_total_official"] = cells_total_official
    ctx = store.context

    if policy_pack.config_hash() != ctx.policy_pack_hash:
        raise ValueError(
            "parent policy_pack_hash mismatch: "
            f"pack={policy_pack.config_hash()} store={ctx.policy_pack_hash}"
        )
    if policy_pack.version != ctx.policy_pack_version:
        raise ValueError(
            "parent policy_pack_version mismatch: "
            f"pack={policy_pack.version} store={ctx.policy_pack_version}"
        )
    if _is_official_mode(mode) and not policy_pack.is_frozen_for_benchmark:
        raise ValueError(
            f"official parallel run requires SEALED PolicyPack (got {policy_pack.status.value})"
        )

    run_start = monotonic_seconds()
    executed = 0
    skipped = 0
    telemetry_samples: list[CellTelemetry] = []
    cell_durations: list[float] = []
    pending_groups: list[BenchmarkGroup] = []

    for group in groups:
        valid = sum(1 for cell in group.cells if store.is_cell_valid(cell))
        skipped += valid
        if valid == len(group.cells):
            continue
        pending_groups.append(group)

    groups_completed = groups_total - len(pending_groups)
    peak_parent_rss = current_rss_bytes() or 0
    peak_worker_rss = 0

    if progress and progress_stream is not None:
        progress_stream.write(
            f"parallel workers={workers} groups={groups_total} "
            f"cells_planned={len(planned)}\n"
        )
        progress_stream.flush()

    if pending_groups:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    run_seed_profile_group,
                    seed=group.seed,
                    profile=group.profile,
                    cell_dicts=[c.to_dict() for c in group.cells],
                    cells_root=str(store.root),
                    config_hash=config_hash,
                    benchmark_version=ctx.benchmark_version,
                    policy_pack_version=ctx.policy_pack_version,
                    policy_pack_hash=ctx.policy_pack_hash,
                    metric_version=ctx.metric_version,
                    mode=mode,
                    config_payload=config_payload,
                ): group
                for group in pending_groups
            }
            for fut in as_completed(futures):
                group = futures[fut]
                try:
                    result = fut.result()
                except Exception as exc:
                    raise RuntimeError(
                        f"parallel worker failed for seed={group.seed} profile={group.profile}"
                    ) from exc

                verify_group_persisted(store, group)

                executed += int(result.get("cells_executed", 0))
                group_seconds = float(result.get("group_seconds") or 0.0)
                worker_peak = int(result.get("peak_rss_bytes") or 0)
                if worker_peak > peak_worker_rss:
                    peak_worker_rss = worker_peak
                parent_rss = current_rss_bytes() or 0
                if parent_rss > peak_parent_rss:
                    peak_parent_rss = parent_rss

                if group_seconds > 0 and result.get("cells_executed", 0) > 0:
                    cell_durations.append(group_seconds / max(1, result["cells_executed"]))

                sync_checkpoint_from_persisted(store, planned, cells_total_official)

                groups_completed += 1
                if progress and progress_stream is not None:
                    _emit_group_progress(
                        stream=progress_stream,
                        group=group,
                        group_index=group_index_by_key[group.key],
                        groups_total=groups_total,
                        groups_completed=groups_completed,
                        store=store,
                        planned=planned,
                        cells_total_official=cells_total_official,
                        group_seconds=group_seconds,
                        elapsed=monotonic_seconds() - run_start,
                        cell_durations=cell_durations,
                        parent_rss=parent_rss,
                    )

    sync_checkpoint_from_persisted(store, planned, cells_total_official)

    aggregate = aggregate_from_store(
        store,
        config,
        cells=planned,
        require_complete=require_complete_aggregate,
    )

    estimated_parallel_peak = peak_parent_rss + peak_worker_rss * workers
    memory_safe = estimated_parallel_peak <= PARALLEL_MEMORY_SAFE_BYTES

    return CellExecutionResult(
        cells_planned=len(planned),
        cells_executed=executed,
        cells_skipped=skipped,
        cells_total_official=cells_total_official,
        aggregate=aggregate,
        cells_root=store.root,
        telemetry_samples=telemetry_samples,
        metadata={
            "cells_root": str(store.root),
            "workers": workers,
            "parallel_groups": groups_total,
            "peak_parent_rss_bytes": peak_parent_rss,
            "peak_worker_rss_bytes": peak_worker_rss,
            "estimated_parallel_peak_bytes": estimated_parallel_peak,
            "memory_safe": memory_safe,
            "checkpoint_reconciliation": reconciliation or {},
        },
    )
