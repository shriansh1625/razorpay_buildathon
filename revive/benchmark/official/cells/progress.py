"""Shared benchmark progress formatting — M13.20."""

from __future__ import annotations

from revive.benchmark.official.cells.plan import BenchmarkCell, BenchmarkGroup


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, rem = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)}m{rem:.0f}s"
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h{int(minutes)}m"


def format_rss(rss: int | None) -> str:
    if rss is None:
        return "n/a"
    if rss >= 1024 * 1024:
        return f"{rss / (1024 * 1024):.1f}MB"
    return f"{rss / 1024:.0f}KB"


def estimate_eta(durations: list[float], remaining: int) -> float | None:
    if not durations or remaining <= 0 or len(durations) < 2:
        return None
    avg = sum(durations) / len(durations)
    return avg * remaining


def cell_progress_line(
    cell: BenchmarkCell,
    *,
    cells_total: int,
    elapsed: float,
    cell_duration: float,
    completed: int,
    remaining: int,
    eta_seconds: float | None,
) -> str:
    eta = "calculating" if eta_seconds is None else format_duration(eta_seconds)
    return (
        f"[{cell.index:03d}/{cells_total:03d}] "
        f"seed={cell.seed} profile={cell.profile} policy={cell.policy_id} | "
        f"elapsed={format_duration(elapsed)} "
        f"cell={format_duration(cell_duration)} "
        f"completed={completed} remaining={remaining} "
        f"ETA={eta}"
    )


def group_header_line(group: BenchmarkGroup, *, group_index: int, groups_total: int) -> str:
    return (
        f"[GROUP {group_index:03d}/{groups_total:03d}] "
        f"seed={group.seed} profile={group.profile}"
    )


def group_summary_line(
    group: BenchmarkGroup,
    *,
    policies_complete: int,
    policies_total: int,
    group_duration: float,
    rss: int | None,
) -> str:
    return (
        f"seed={group.seed} profile={group.profile}: "
        f"{policies_complete}/{policies_total} policies complete | "
        f"group_duration={format_duration(group_duration)} | "
        f"rss={format_rss(rss)}"
    )


def aggregate_progress_line(
    *,
    groups_completed: int,
    groups_total: int,
    cells_completed: int,
    cells_total: int,
) -> str:
    return (
        f"progress: groups={groups_completed}/{groups_total} "
        f"cells={cells_completed}/{cells_total}"
    )
