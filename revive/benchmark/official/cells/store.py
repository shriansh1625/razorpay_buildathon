"""Atomic cell result persistence and checkpoint manifest — M13.11."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from revive.benchmark.official.aggregate import BenchmarkAggregate
from revive.benchmark.official.cells.plan import BenchmarkCell, plan_benchmark_cells
from revive.benchmark.official.config import OfficialBenchmarkConfig
from revive.benchmark.official.metrics import PolicyRunMetrics

CELL_RESULT_SCHEMA_VERSION = "1"
CHECKPOINT_SCHEMA_VERSION = "1"
CHECKPOINT_MANIFEST_NAME = "checkpoint-manifest.json"


def cell_result_path(root: Path, cell: BenchmarkCell) -> Path:
    return (
        root
        / f"seed-{cell.seed:03d}"
        / cell.profile
        / f"{cell.policy_id}.json"
    )


def metrics_checksum(metrics: dict[str, Any]) -> str:
    canonical = json.dumps(metrics, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, sort_keys=True, indent=2) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


@dataclass(frozen=True, slots=True)
class CellRecordContext:
    config_hash: str
    benchmark_version: str
    policy_pack_version: str
    policy_pack_hash: str
    metric_version: str


@dataclass(frozen=True, slots=True)
class CheckpointReconciliation:
    """Result of reconciling checkpoint manifest with persisted cell files."""

    valid_cells: int
    cells_total: int
    manifest_cells_completed: int | None
    manifest_ahead: bool
    files_ahead: bool
    last_cell_invalid: bool
    repaired: bool
    last_cell_index: int | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid_cells": self.valid_cells,
            "cells_total": self.cells_total,
            "manifest_cells_completed": self.manifest_cells_completed,
            "manifest_ahead": self.manifest_ahead,
            "files_ahead": self.files_ahead,
            "last_cell_invalid": self.last_cell_invalid,
            "repaired": self.repaired,
            "last_cell_index": self.last_cell_index,
        }


def cell_from_dict(data: dict[str, Any]) -> BenchmarkCell:
    return BenchmarkCell(
        index=int(data["index"]),
        seed=int(data["seed"]),
        profile=str(data["profile"]),
        policy_id=str(data["policy_id"]),
    )


def last_completed_cell(
    store: CellStore,
    planned: tuple[BenchmarkCell, ...],
) -> BenchmarkCell | None:
    for cell in reversed(planned):
        if store.is_cell_valid(cell):
            return cell
    return None


def sync_checkpoint_from_persisted(
    store: CellStore,
    planned: tuple[BenchmarkCell, ...],
    cells_total: int,
) -> tuple[int, BenchmarkCell | None]:
    """Write checkpoint manifest from validated persisted cell files only."""
    valid_count = store.count_valid_cells(planned)
    last_cell = last_completed_cell(store, planned)
    store.write_checkpoint(
        cells_completed=valid_count,
        cells_total=cells_total,
        last_cell=last_cell,
    )
    return valid_count, last_cell


def reconcile_checkpoint(
    store: CellStore,
    planned: tuple[BenchmarkCell, ...],
    cells_total: int,
) -> CheckpointReconciliation:
    """
    Reconcile stale checkpoint state with persisted valid cells.

    Persisted valid cell files are authoritative. The manifest is repaired when
    it is ahead of durable files, behind valid files, or references an invalid
    last_completed_cell.
    """
    checkpoint = store.read_checkpoint()
    valid_count = store.count_valid_cells(planned)
    manifest_count = checkpoint.get("cells_completed") if checkpoint else None

    manifest_ahead = manifest_count is not None and manifest_count > valid_count
    files_ahead = manifest_count is not None and valid_count > manifest_count
    last_cell_invalid = False

    if checkpoint and checkpoint.get("last_completed_cell"):
        last_claimed = cell_from_dict(checkpoint["last_completed_cell"])
        if not store.is_cell_valid(last_claimed):
            last_cell_invalid = True
            manifest_ahead = True

    repaired = (
        checkpoint is None
        or manifest_ahead
        or files_ahead
        or last_cell_invalid
        or manifest_count != valid_count
    )

    synced_count, last_cell = sync_checkpoint_from_persisted(store, planned, cells_total)
    return CheckpointReconciliation(
        valid_cells=valid_count,
        cells_total=cells_total,
        manifest_cells_completed=manifest_count,
        manifest_ahead=manifest_ahead,
        files_ahead=files_ahead,
        last_cell_invalid=last_cell_invalid,
        repaired=repaired,
        last_cell_index=last_cell.index if last_cell is not None else None,
    )


class CellStore:
    """Filesystem-backed cell results with atomic writes."""

    def __init__(self, root: Path, context: CellRecordContext) -> None:
        self.root = root
        self.context = context
        self.root.mkdir(parents=True, exist_ok=True)

    def write_cell(
        self,
        cell: BenchmarkCell,
        metrics: PolicyRunMetrics,
        *,
        telemetry: dict[str, Any] | None = None,
    ) -> Path:
        metrics_dict = metrics.to_dict()
        payload: dict[str, Any] = {
            "schema_version": CELL_RESULT_SCHEMA_VERSION,
            "benchmark_version": self.context.benchmark_version,
            "config_hash": self.context.config_hash,
            "policy_pack_version": self.context.policy_pack_version,
            "policy_pack_hash": self.context.policy_pack_hash,
            "metric_version": self.context.metric_version,
            "seed": cell.seed,
            "profile": cell.profile,
            "policy_id": cell.policy_id,
            "cell_index": cell.index,
            "metrics": metrics_dict,
            "metrics_checksum": metrics_checksum(metrics_dict),
        }
        if telemetry is not None:
            payload["telemetry"] = telemetry
        path = cell_result_path(self.root, cell)
        atomic_write_json(path, payload)
        return path

    def read_cell_raw(self, cell: BenchmarkCell) -> dict[str, Any] | None:
        path = cell_result_path(self.root, cell)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def is_cell_valid(self, cell: BenchmarkCell) -> bool:
        return self.validate_cell_record(self.read_cell_raw(cell)) is None

    def validate_cell_record(self, record: dict[str, Any] | None) -> str | None:
        if record is None:
            return "missing"
        if record.get("schema_version") != CELL_RESULT_SCHEMA_VERSION:
            return "schema_version"
        if record.get("config_hash") != self.context.config_hash:
            return "config_hash"
        if record.get("benchmark_version") != self.context.benchmark_version:
            return "benchmark_version"
        if record.get("policy_pack_version") != self.context.policy_pack_version:
            return "policy_pack_version"
        if record.get("policy_pack_hash") != self.context.policy_pack_hash:
            return "policy_pack_hash"
        if record.get("metric_version") != self.context.metric_version:
            return "metric_version"
        metrics = record.get("metrics")
        if not isinstance(metrics, dict):
            return "metrics"
        expected = record.get("metrics_checksum")
        if not isinstance(expected, str) or metrics_checksum(metrics) != expected:
            return "metrics_checksum"
        if record.get("seed") != metrics.get("seed"):
            return "identity_seed"
        if record.get("profile") != metrics.get("profile"):
            return "identity_profile"
        if record.get("policy_id") != metrics.get("policy_id"):
            return "identity_policy"
        return None

    def load_metrics(self, cell: BenchmarkCell) -> PolicyRunMetrics | None:
        record = self.read_cell_raw(cell)
        if self.validate_cell_record(record) is not None:
            return None
        assert record is not None
        return PolicyRunMetrics.from_dict(record["metrics"])

    def write_checkpoint(
        self,
        *,
        cells_completed: int,
        cells_total: int,
        last_cell: BenchmarkCell | None,
    ) -> Path:
        payload: dict[str, Any] = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "cells_completed": cells_completed,
            "cells_total": cells_total,
            "config_hash": self.context.config_hash,
            "benchmark_version": self.context.benchmark_version,
            "policy_pack_version": self.context.policy_pack_version,
            "policy_pack_hash": self.context.policy_pack_hash,
            "metric_version": self.context.metric_version,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if last_cell is not None:
            payload["last_completed_cell"] = last_cell.to_dict()
        path = self.root / CHECKPOINT_MANIFEST_NAME
        atomic_write_json(path, payload)
        return path

    def read_checkpoint(self) -> dict[str, Any] | None:
        path = self.root / CHECKPOINT_MANIFEST_NAME
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def count_valid_cells(self, cells: tuple[BenchmarkCell, ...]) -> int:
        return sum(1 for cell in cells if self.is_cell_valid(cell))


def assert_checkpoint_config_compatible(
    store: CellStore,
    *,
    cells_total: int,
) -> None:
    checkpoint = store.read_checkpoint()
    if checkpoint is None:
        return
    if checkpoint.get("config_hash") != store.context.config_hash:
        raise BenchmarkConfigMismatchError(
            "stored checkpoint config_hash does not match frozen official configuration"
        )
    if checkpoint.get("benchmark_version") != store.context.benchmark_version:
        raise BenchmarkConfigMismatchError(
            "stored checkpoint benchmark_version does not match current benchmark"
        )
    stored_total = checkpoint.get("cells_total")
    if stored_total is not None and stored_total != cells_total:
        raise BenchmarkConfigMismatchError(
            f"stored checkpoint cells_total={stored_total} != planned {cells_total}"
        )


class BenchmarkConfigMismatchError(RuntimeError):
    """Attempted to resume across incompatible benchmark configuration."""


def aggregate_from_store(
    store: CellStore,
    config: OfficialBenchmarkConfig,
    *,
    cells: tuple[BenchmarkCell, ...] | None = None,
    require_complete: bool = True,
) -> BenchmarkAggregate:
    """Build aggregate from persisted cell summaries without simulation state."""
    planned = cells if cells is not None else plan_benchmark_cells(config)
    aggregate = BenchmarkAggregate()
    missing: list[BenchmarkCell] = []
    for cell in planned:
        metrics = store.load_metrics(cell)
        if metrics is None:
            missing.append(cell)
            continue
        aggregate.add(metrics)
    if require_complete and missing:
        raise ValueError(
            f"aggregate incomplete: missing {len(missing)} valid cell results"
        )
    aggregate.finalize_m10()
    return aggregate
