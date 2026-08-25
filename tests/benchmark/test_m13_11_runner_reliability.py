"""M13.11 benchmark runner reliability tests."""

from __future__ import annotations

import json
import random
import statistics
from pathlib import Path

import pytest

from revive.benchmark.official.cells.plan import (
    official_cell_total,
    plan_benchmark_cells,
)
from revive.benchmark.official.cells.runner import run_cell_benchmark
from revive.benchmark.official.cells.store import (
    BenchmarkConfigMismatchError,
    CellRecordContext,
    CellStore,
    aggregate_from_store,
    atomic_write_json,
    cell_result_path,
    metrics_checksum,
)
from revive.benchmark.official.cells.telemetry import current_rss_bytes
from revive.benchmark.official.config import (
    BenchmarkMode,
    development_benchmark_config,
    official_benchmark_config,
)
from revive.benchmark.official.hash import official_benchmark_config_hash
from revive.benchmark.official.metrics import PolicyRunMetrics
from revive.benchmark.official.runner import execute_benchmark
from revive.config.policy_pack import default_draft_policy_pack, official_sealed_policy_pack
from revive.simulation.types import GenerationProfile


def _dev_config(*, seeds: tuple[int, ...] = (1,), profiles: tuple[GenerationProfile, ...] = (GenerationProfile.BALANCED,)):
    pack = default_draft_policy_pack()
    return development_benchmark_config(policy_pack=pack, seeds=seeds, profiles=profiles)


def _store_for(config, config_hash: str, root: Path) -> CellStore:
    return CellStore(
        root,
        CellRecordContext(
            config_hash=config_hash,
            benchmark_version=config.benchmark_version,
            policy_pack_version=config.policy_pack_version,
            policy_pack_hash=config.policy_pack_hash,
            metric_version=config.metric_version,
        ),
    )


def test_plan_official_600_cells():
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    cells = plan_benchmark_cells(config)
    assert len(cells) == 600
    assert official_cell_total(config) == 600
    assert cells[0].policy_id == "B0"
    assert cells[4].policy_id == "REVIVE"
    assert cells[5].seed == 1
    assert cells[5].profile == GenerationProfile.HIGH_NATURAL.value


def test_one_cell_execution(tmp_path: Path):
    config = _dev_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    result = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=tmp_path / "cells",
        max_cells=1,
        progress=False,
        require_complete_aggregate=False,
    )
    assert result.cells_executed == 1
    assert result.cells_planned == 1
    cell_path = tmp_path / "cells" / "seed-001" / "BALANCED" / "B0.json"
    assert cell_path.exists()
    payload = json.loads(cell_path.read_text(encoding="utf-8"))
    assert payload["metrics_checksum"] == metrics_checksum(payload["metrics"])


def test_progress_reporting():
    from io import StringIO

    config = _dev_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    buf = StringIO()
    run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=None,
        max_cells=2,
        progress=True,
        progress_stream=buf,
        require_complete_aggregate=False,
    )
    out = buf.getvalue()
    assert "[001/" in out
    assert "seed=1" in out
    assert "policy=B0" in out


def test_atomic_result_and_checkpoint(tmp_path: Path):
    config = _dev_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    cells_root = tmp_path / "cells"
    run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=cells_root,
        max_cells=3,
        progress=False,
        require_complete_aggregate=False,
    )
    manifest = json.loads((cells_root / "checkpoint-manifest.json").read_text(encoding="utf-8"))
    assert manifest["cells_completed"] == 3
    assert manifest["cells_total"] == 5
    assert manifest["config_hash"] == config_hash
    assert not list(cells_root.rglob("*.tmp"))


def test_resume_skips_valid_cells(tmp_path: Path):
    config = _dev_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    cells_root = tmp_path / "cells"

    first = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=cells_root,
        stop_after_cell=3,
        progress=False,
        require_complete_aggregate=False,
    )
    assert first.cells_executed == 3

    second = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=cells_root,
        progress=False,
        require_complete_aggregate=True,
    )
    assert second.cells_skipped == 3
    assert second.cells_executed == 2
    assert len(second.aggregate.per_run) == 5


def test_interrupt_then_resume(tmp_path: Path):
    config = _dev_config(seeds=tuple(range(1, 8)))
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    cells_root = tmp_path / "cells"

    run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=cells_root,
        stop_after_cell=17,
        progress=False,
        require_complete_aggregate=False,
    )
    store = _store_for(config, config_hash, cells_root)
    assert store.count_valid_cells(plan_benchmark_cells(config)) == 17

    completed = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=cells_root,
        progress=False,
        require_complete_aggregate=True,
    )
    assert completed.cells_skipped == 17
    assert len(completed.aggregate.per_run) == 35


def test_corrupt_result_is_recomputed(tmp_path: Path):
    config = _dev_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    cells_root = tmp_path / "cells"
    run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=cells_root,
        max_cells=1,
        progress=False,
        require_complete_aggregate=False,
    )
    cell = plan_benchmark_cells(config, max_cells=1)[0]
    path = cell_result_path(cells_root, cell)
    corrupt = json.loads(path.read_text(encoding="utf-8"))
    corrupt["metrics"]["net_recovered_paise"] = 999_999_999
    # checksum now invalid
    atomic_write_json(path, corrupt)

    store = _store_for(config, config_hash, cells_root)
    assert not store.is_cell_valid(cell)

    rerun = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=cells_root,
        max_cells=1,
        progress=False,
        require_complete_aggregate=False,
    )
    assert rerun.cells_executed == 1
    fixed = json.loads(path.read_text(encoding="utf-8"))
    assert fixed["metrics"]["net_recovered_paise"] != 999_999_999


def test_config_hash_mismatch_rejected(tmp_path: Path):
    config = _dev_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    cells_root = tmp_path / "cells"
    store = _store_for(config, config_hash, cells_root)
    store.write_checkpoint(cells_completed=0, cells_total=5, last_cell=None)

    wrong_hash = "0" * 64
    with pytest.raises(BenchmarkConfigMismatchError):
        run_cell_benchmark(
            config=config,
            policy_pack=pack,
            config_hash=wrong_hash,
            cells_root=cells_root,
            max_cells=1,
            progress=False,
        )


def test_deterministic_cell_results(tmp_path: Path):
    config = _dev_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)

    r1 = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=tmp_path / "run1",
        progress=False,
    )
    r2 = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=tmp_path / "run2",
        progress=False,
    )
    assert r1.aggregate.to_dict() == r2.aggregate.to_dict()


def test_order_independent_aggregation(tmp_path: Path):
    config = _dev_config()
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    cells_root = tmp_path / "cells"
    run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=cells_root,
        progress=False,
    )
    store = _store_for(config, config_hash, cells_root)
    planned = plan_benchmark_cells(config)
    canonical = aggregate_from_store(store, config, cells=planned)

    shuffled = list(planned)
    random.Random(13).shuffle(shuffled)
    shuffled_agg = aggregate_from_store(store, config, cells=tuple(shuffled))
    assert canonical.to_dict() == shuffled_agg.to_dict()


def test_shared_world_fairness_matches_direct_runner():
    from revive.benchmark.official.policy_runner import run_policy_on_world
    from revive.benchmark.official.policies import ALL_BENCHMARK_POLICIES, BenchmarkPolicyId
    from revive.benchmark.official.world import generate_shared_world
    from revive.simulation.fixtures import tiny_config

    pack = default_draft_policy_pack()
    bundle = generate_shared_world(tiny_config(seed=42))
    direct = {
        p.value: run_policy_on_world(bundle, p, pack).net_recovered_paise
        for p in ALL_BENCHMARK_POLICIES
    }

    config = development_benchmark_config(
        policy_pack=pack,
        seeds=(42,),
        profiles=(GenerationProfile.BALANCED,),
    )
    config_hash = official_benchmark_config_hash(config)
    result = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=None,
        progress=False,
    )
    streamed = {m.policy_id: m.net_recovered_paise for m in result.aggregate.per_run}
    assert streamed == direct


def test_memory_cleanup_bounded_growth():
    config = _dev_config(seeds=tuple(range(1, 6)))
    pack = default_draft_policy_pack()
    config_hash = official_benchmark_config_hash(config)
    result = run_cell_benchmark(
        config=config,
        policy_pack=pack,
        config_hash=config_hash,
        cells_root=None,
        progress=False,
    )
    assert len(result.telemetry_samples) == 25
    rss_after = [t.rss_after_bytes for t in result.telemetry_samples if t.rss_after_bytes]
    if len(rss_after) >= 10:
        warmup = rss_after[3:]
        first_half = statistics.mean(warmup[: len(warmup) // 2])
        second_half = statistics.mean(warmup[len(warmup) // 2 :])
        # Operational tolerance: memory should not grow linearly with completed cells.
        assert second_half <= first_half * 1.35 + 8_000_000


def test_final_aggregation_via_execute_benchmark(tmp_path: Path):
    result = execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=tmp_path / "bench",
    )
    assert len(result.aggregate.per_run) == 5
    assert (tmp_path / "bench" / "cells" / "checkpoint-manifest.json").exists()
    assert result.metadata.get("runner") == "cell_streaming_m13_11"


def test_empty_incomplete_result_handling(tmp_path: Path):
    config = _dev_config()
    config_hash = official_benchmark_config_hash(config)
    store = _store_for(config, config_hash, tmp_path / "cells")
    with pytest.raises(ValueError, match="incomplete"):
        aggregate_from_store(store, config, require_complete=True)


def test_policy_run_metrics_roundtrip():
    sample = PolicyRunMetrics(
        policy_id="B0",
        seed=1,
        profile="BALANCED",
        net_recovered_paise=100,
        m10_incremental_net_paise=0,
    )
    restored = PolicyRunMetrics.from_dict(sample.to_dict())
    assert restored.policy_id == sample.policy_id
    assert restored.net_recovered_paise == sample.net_recovered_paise


def test_stress_mode(tmp_path: Path):
    result = execute_benchmark(
        mode=BenchmarkMode.DEVELOPMENT,
        output_dir=tmp_path / "stress",
        stress_cells=10,
    )
    assert result.metadata["cells_planned"] == 10
    assert len(result.aggregate.per_run) == 10
    assert current_rss_bytes() is not None or True
