"""Process worker for parallel seed/profile groups — M13.15 / M13.16."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from revive.benchmark.official.freeze_constants import OFFICIAL_BENCHMARK_ID, PREFLIGHT_BENCHMARK_ID
from revive.config.policy_pack import (
    PolicyPackStatus,
    policy_pack_from_frozen_payload,
)


def _normalize_mode(mode: str) -> str:
    return str(mode).upper()


def _is_official_payload(payload: dict[str, Any], mode: str) -> bool:
    bid = payload.get("benchmark_id")
    norm = _normalize_mode(mode)
    return bid in {OFFICIAL_BENCHMARK_ID, PREFLIGHT_BENCHMARK_ID} or norm in {
        "OFFICIAL",
        "PREFLIGHT",
    }


def config_to_worker_payload(config, policy_pack) -> dict[str, Any]:
    from revive.config.policy_pack import policy_pack_to_frozen_payload

    return {
        "benchmark_id": config.benchmark_id,
        "seed_set": list(config.seed_set),
        "profile_set": [p.value for p in config.profile_set],
        "policy_pack": policy_pack_to_frozen_payload(policy_pack),
    }


def config_from_worker_payload(payload: dict[str, Any], *, policy_pack) -> Any:
    from dataclasses import replace

    from revive.benchmark.official.config import (
        development_benchmark_config,
        official_benchmark_config,
        preflight_benchmark_config,
    )
    from revive.simulation.types import GenerationProfile

    profiles = tuple(GenerationProfile(p) for p in payload["profile_set"])
    seeds = tuple(int(s) for s in payload["seed_set"])
    norm = _normalize_mode(payload.get("mode", ""))

    if norm == "PREFLIGHT" or payload.get("benchmark_id") == PREFLIGHT_BENCHMARK_ID:
        base = preflight_benchmark_config(policy_pack=policy_pack, seeds=seeds)
        return replace(base, profile_set=profiles)

    if payload.get("benchmark_id") == OFFICIAL_BENCHMARK_ID or norm == "OFFICIAL":
        return official_benchmark_config(policy_pack=policy_pack)

    if policy_pack.is_frozen_for_benchmark:
        base = preflight_benchmark_config(policy_pack=policy_pack, seeds=seeds)
        return replace(
            base,
            profile_set=profiles,
            benchmark_id=str(payload.get("benchmark_id") or base.benchmark_id),
        )

    return development_benchmark_config(policy_pack=policy_pack, seeds=seeds, profiles=profiles)


def reconstruct_worker_policy_pack(
    config_payload: dict[str, Any],
    *,
    mode: str,
    expected_policy_pack_hash: str,
) -> Any:
    """Fail-closed PolicyPack reconstruction for spawned workers."""
    pack_payload = config_payload.get("policy_pack")
    if pack_payload is None:
        raise ValueError("worker config payload missing policy_pack")
    require_sealed = _is_official_payload(config_payload, mode)
    pack = policy_pack_from_frozen_payload(
        pack_payload,
        expected_hash=expected_policy_pack_hash,
        require_sealed=require_sealed,
    )
    if require_sealed and pack.status != PolicyPackStatus.SEALED:
        raise ValueError(
            f"official worker requires SEALED PolicyPack (got status={pack.status.value})"
        )
    if pack.config_hash() != expected_policy_pack_hash:
        raise ValueError(
            "parent/worker policy_pack_hash mismatch: "
            f"expected={expected_policy_pack_hash} got={pack.config_hash()}"
        )
    return pack


def run_seed_profile_group(
    *,
    seed: int,
    profile: str,
    cell_dicts: list[dict[str, Any]],
    cells_root: str,
    config_hash: str,
    benchmark_version: str,
    policy_pack_version: str,
    policy_pack_hash: str,
    metric_version: str,
    mode: str,
    config_payload: dict[str, Any],
) -> dict[str, Any]:
    """Execute one seed/profile group: one world, five policies, atomic cell writes."""
    from revive.benchmark.official.cells.plan import BenchmarkCell
    from revive.benchmark.official.cells.store import CellRecordContext, CellStore
    from revive.benchmark.official.config import generator_config_for_cell
    from revive.benchmark.official.hash import official_benchmark_config_hash
    from revive.benchmark.official.policies import BenchmarkPolicyId
    from revive.benchmark.official.policy_runner import run_policy_on_world
    from revive.benchmark.official.world import generate_shared_world
    from revive.simulation.types import GenerationProfile

    payload = dict(config_payload)
    payload["mode"] = _normalize_mode(mode)

    pack = reconstruct_worker_policy_pack(
        payload,
        mode=mode,
        expected_policy_pack_hash=policy_pack_hash,
    )
    if pack.version != policy_pack_version:
        raise ValueError(
            "policy pack version mismatch: "
            f"expected={policy_pack_version} got={pack.version}"
        )

    config = config_from_worker_payload(payload, policy_pack=pack)
    worker_config_hash = official_benchmark_config_hash(config)
    if worker_config_hash != config_hash:
        raise RuntimeError(
            "parent/worker config_hash mismatch for "
            f"seed={seed} profile={profile}: "
            f"expected={config_hash} got={worker_config_hash}"
        )

    cells = tuple(
        BenchmarkCell(
            index=int(d["index"]),
            seed=int(d["seed"]),
            profile=str(d["profile"]),
            policy_id=str(d["policy_id"]),
        )
        for d in cell_dicts
    )
    root = Path(cells_root)
    store = CellStore(
        root,
        CellRecordContext(
            config_hash=config_hash,
            benchmark_version=benchmark_version,
            policy_pack_version=policy_pack_version,
            policy_pack_hash=policy_pack_hash,
            metric_version=metric_version,
        ),
    )

    pending = tuple(c for c in cells if not store.is_cell_valid(c))
    if not pending:
        checksums = {
            c.key: (store.read_cell_raw(c) or {}).get("metrics_checksum")
            for c in cells
        }
        return {
            "seed": seed,
            "profile": profile,
            "cells_executed": 0,
            "cells_skipped": len(cells),
            "metrics_checksums": checksums,
            "group_seconds": 0.0,
            "peak_rss_bytes": None,
        }

    gen_config = generator_config_for_cell(config, seed, GenerationProfile(profile))
    bundle = generate_shared_world(gen_config)
    from revive.benchmark.official.cells.telemetry import PeakRssTracker, current_rss_bytes

    rss_tracker = PeakRssTracker()
    t0 = time.perf_counter()
    executed = 0
    checksums: dict[tuple[int, str, str], str | None] = {}

    for cell in cells:
        if store.is_cell_valid(cell):
            checksums[cell.key] = (store.read_cell_raw(cell) or {}).get("metrics_checksum")
            continue
        cell_start = time.perf_counter()
        metrics = run_policy_on_world(bundle, BenchmarkPolicyId(cell.policy_id), pack)
        elapsed = time.perf_counter() - cell_start
        store.write_cell(cell, metrics, telemetry={"elapsed_seconds": elapsed})
        raw = store.read_cell_raw(cell) or {}
        checksums[cell.key] = raw.get("metrics_checksum")
        executed += 1
        rss_tracker.sample()

    return {
        "seed": seed,
        "profile": profile,
        "cells_executed": executed,
        "cells_skipped": len(cells) - executed,
        "metrics_checksums": checksums,
        "group_seconds": time.perf_counter() - t0,
        "last_cell_index": max(c.index for c in cells),
        "peak_rss_bytes": rss_tracker.peak or current_rss_bytes(),
    }


def run_isolated_cell(
    cell_dict: dict[str, Any],
    cells_root: str,
    config_hash: str,
    benchmark_version: str,
    policy_pack_version: str,
    policy_pack_hash: str,
    metric_version: str,
    policy_pack_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Backward-compatible single REVIVE cell worker (M13.14 development path)."""
    from revive.config.policy_pack import official_sealed_policy_pack, policy_pack_to_frozen_payload

    if policy_pack_payload is None:
        policy_pack_payload = policy_pack_to_frozen_payload(official_sealed_policy_pack())

    result = run_seed_profile_group(
        seed=int(cell_dict["seed"]),
        profile=str(cell_dict["profile"]),
        cell_dicts=[cell_dict],
        cells_root=cells_root,
        config_hash=config_hash,
        benchmark_version=benchmark_version,
        policy_pack_version=policy_pack_version,
        policy_pack_hash=policy_pack_hash,
        metric_version=metric_version,
        mode="OFFICIAL",
        config_payload={
            "benchmark_id": OFFICIAL_BENCHMARK_ID,
            "seed_set": [int(cell_dict["seed"])],
            "profile_set": [str(cell_dict["profile"])],
            "policy_pack": policy_pack_payload,
        },
    )
    key = (int(cell_dict["seed"]), str(cell_dict["profile"]), str(cell_dict["policy_id"]))
    return {
        "cell": cell_dict,
        "elapsed_seconds": result.get("group_seconds"),
        "metrics_checksum": result.get("metrics_checksums", {}).get(key),
    }
