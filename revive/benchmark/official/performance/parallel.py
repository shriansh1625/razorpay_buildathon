"""Development-only parallel cell execution — M13.14."""

from __future__ import annotations

import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from revive.benchmark.official.cells.plan import BenchmarkCell
from revive.benchmark.official.cells.runner import run_cell_benchmark
from revive.benchmark.official.cells.store import CellRecordContext, CellStore
from revive.benchmark.official.config import OfficialBenchmarkConfig
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.benchmark.official.cells.parallel_worker import run_isolated_cell
from revive.config.policy_pack import PolicyPack

DEVELOPMENT_LABEL = "DEVELOPMENT_PARALLEL_ONLY"


@dataclass
class ParallelRunResult:
    workers: int
    cells: tuple[BenchmarkCell, ...]
    wall_seconds: float
    cell_results: list[dict[str, Any]] = field(default_factory=list)
    label: str = DEVELOPMENT_LABEL

    def fingerprints(self) -> dict[tuple[int, str, str], str]:
        out: dict[tuple[int, str, str], str] = {}
        for row in self.cell_results:
            c = row["cell"]
            fp = row.get("metrics_checksum")
            if fp:
                out[(c["seed"], c["profile"], c["policy_id"])] = fp
        return out


def run_cells_parallel(
    *,
    config: OfficialBenchmarkConfig,
    policy_pack: PolicyPack,
    cells: tuple[BenchmarkCell, ...],
    cells_root: Path,
    workers: int = 2,
) -> ParallelRunResult:
    """Run independent cells concurrently (development feasibility only)."""
    if workers < 1:
        raise ValueError("workers must be >= 1")
    cells_root.mkdir(parents=True, exist_ok=True)
    config_hash = official_benchmark_config_hash(config)

    if workers == 1:
        t0 = time.perf_counter()
        run_cell_benchmark(
            config=config,
            policy_pack=policy_pack,
            config_hash=config_hash,
            cells_root=cells_root,
            cells=cells,
            cells_total_checkpoint=len(cells),
            progress=False,
            require_complete_aggregate=False,
        )
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
        rows = []
        for cell in cells:
            raw = store.read_cell_raw(cell) or {}
            rows.append(
                {
                    "cell": cell.to_dict(),
                    "elapsed_seconds": None,
                    "metrics_checksum": raw.get("metrics_checksum"),
                }
            )
        return ParallelRunResult(
            workers=1,
            cells=cells,
            wall_seconds=time.perf_counter() - t0,
            cell_results=rows,
        )

    cell_payloads = [c.to_dict() for c in cells]
    t0 = time.perf_counter()
    results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(
                run_isolated_cell,
                payload,
                str(cells_root),
                config_hash,
                config.benchmark_version,
                config.policy_pack_version,
                config.policy_pack_hash,
                config.metric_version,
            )
            for payload in cell_payloads
        ]
        for fut in as_completed(futures):
            results.append(fut.result())
    return ParallelRunResult(
        workers=workers,
        cells=cells,
        wall_seconds=time.perf_counter() - t0,
        cell_results=results,
    )
