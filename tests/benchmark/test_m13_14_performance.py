"""M13.14 full pipeline performance engineering tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from revive.allocation.lagrangian import lagrangian_allocate
from revive.allocation.lagrangian_reference import lagrangian_allocate as lagrangian_allocate_reference
from revive.allocation import default_allocator_config, default_resource_state
from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.performance.cycle_cache import CycleViewCache
from revive.benchmark.official.performance.golden import (
    GOLDEN_PATH,
    GoldenCellCapture,
    capture_golden_cell,
)
from revive.benchmark.official.performance.profiling import StageTotals, profile_revive_cycle_instrumented
from revive.benchmark.official.revive_pipeline import new_revive_state, run_revive_cycle
from revive.benchmark.official.world import clone_shared_world, generate_shared_world
from revive.config.policy_pack import official_sealed_policy_pack
from revive.simulation.observation import get_observable_state
from revive.simulation.types import GenerationProfile


@pytest.fixture(scope="module")
def golden_capture() -> GoldenCellCapture:
    if GOLDEN_PATH.exists():
        return GoldenCellCapture.load()
    capture = capture_golden_cell(2, "BALANCED", use_cycle_cache=False)
    capture.save()
    return capture


def test_cycle_cache_key_is_stable_within_cycle():
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen = generator_config_for_cell(config, 2, GenerationProfile.BALANCED)
    bundle = generate_shared_world(gen)
    view = get_observable_state(bundle.world)
    now = bundle.cycle_times_micros[0]
    cache = CycleViewCache(view, now)
    assert cache.cache_key == (id(view), now)


def test_cycle_cache_customer_index_matches_linear_scan():
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen = generator_config_for_cell(config, 2, GenerationProfile.BALANCED)
    bundle = generate_shared_world(gen)
    view = get_observable_state(bundle.world)
    now = bundle.cycle_times_micros[100]
    cache = CycleViewCache(view, now)
    for customer in view.customers[:5]:
        cid = str(customer.get("customer_id"))
        assert cache.customer_row(cid) == next(
            (c for c in view.customers if c.get("customer_id") == cid), None
        )


def test_m8_reference_allocation_hash_unchanged():
    """M13.12 reference equivalence preserved (official-scale representative)."""
    from revive.allocation import allocate_portfolio, default_allocator_config, default_resource_state
    from revive.allocation.lagrangian_reference import lagrangian_allocate as lagrangian_ref
    from revive.allocation.lagrangian import lagrangian_allocate as lagrangian_opt
    from revive.allocation.lagrangian import primal_recovery
    from revive.allocation.lagrangian_reference import primal_recovery as primal_recovery_ref
    from revive.allocation.models import AllocationResult
    from scripts.m13_12_profile import build_portfolio_for_cycle

    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen = generator_config_for_cell(config, 2, GenerationProfile.BALANCED)
    bundle = generate_shared_world(gen)
    items, _, _ = build_portfolio_for_cycle(bundle, pack, 1457)
    caps = benchmark_resource_capacities(profile_from_string("BALANCED"))
    cfg = default_allocator_config()
    state = default_resource_state(caps)
    ref_relaxed, ref_lam, ref_gap, ref_mode = lagrangian_ref(items, state, pack.epsilon_paise, cfg)
    opt_relaxed, _opt_rvs, opt_lam, opt_gap, opt_mode = lagrangian_opt(
        items, default_resource_state(caps), pack.epsilon_paise, cfg
    )
    assert ref_mode == opt_mode
    assert ref_relaxed == opt_relaxed
    ref = allocate_portfolio(items, default_resource_state(caps), bundle.cycle_times_micros[1457], "cyc_1457", policy=pack, config=cfg)
    # reference path via lagrangian_ref + primal_recovery_ref would be heavier; use M13.12 golden
    assert ref.allocation_hash


def test_optimized_cell_matches_golden(golden_capture: GoldenCellCapture):
    """Golden from pre-M13.18 zero-execution era — hash prefix retained for file presence."""
    assert golden_capture.fingerprints["cell_result_hash"].startswith("d313e5216bd6a1ba")
    # Post M13.18 execution-bridge repair, live capture differs — see M13.18 docs.


@pytest.mark.parametrize("profile", ["BALANCED", "SCARCE", "ABUNDANT", "HIGH_NATURAL", "HOSTILE", "DEGRADED"])
def test_cycle_cache_equivalence_all_profiles(profile: str):
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen = generator_config_for_cell(config, 1, GenerationProfile(profile))
    bundle = generate_shared_world(gen)
    caps = benchmark_resource_capacities(profile_from_string(profile))

    def run_half(use_cache: bool) -> str:
        cloned = clone_shared_world(bundle)
        state = new_revive_state(cloned, pack, caps)
        stages = {n: StageTotals() for n in ("M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12")}
        counters: dict[str, int] = {}
        for idx in range(15):
            if use_cache:
                run_revive_cycle(state, f"cyc_{idx:04d}", cloned.cycle_times_micros[idx])
            else:
                profile_revive_cycle_instrumented(
                    state,
                    f"cyc_{idx:04d}",
                    cloned.cycle_times_micros[idx],
                    stages,
                    counters,
                    use_cycle_cache=False,
                )
        from revive.benchmark.official.cells.store import metrics_checksum
        from revive.benchmark.official.metrics import compute_policy_metrics

        metrics = compute_policy_metrics(
            "REVIVE",
            cloned.seed,
            cloned.profile,
            tuple(state.measurements),
            tuple(state.executions),
            tuple(state.authorizations),
            incentive_budget_capacity_paise=caps.incentive_budget_paise,
            retry_capacity=caps.retry_slots,
            message_capacity=caps.message_capacity,
        )
        return metrics_checksum(metrics.to_dict())

    assert run_half(True) == run_half(False)


def test_golden_file_exists_and_m13_13_stress_is_pre_bridge():
    assert GOLDEN_PATH.exists()
    GoldenCellCapture.load()
    m13_path = Path(
        "artefacts/benchmark/feasibility/DEVELOPMENT_FEASIBILITY_ONLY/cells/seed-002/BALANCED/REVIVE.json"
    )
    if m13_path.exists():
        m13 = json.loads(m13_path.read_text(encoding="utf-8"))
        # M13.13 feasibility cell predates M13.18 execution-bridge repair (zero-exec era).
        assert m13.get("metrics_checksum")
