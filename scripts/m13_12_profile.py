"""M13.12 baseline profiling for lagrangian_allocate — development only."""

from __future__ import annotations

import cProfile
import json
import pstats
import time
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from revive.allocation import allocate_portfolio, default_allocator_config, default_resource_state
from revive.allocation.lagrangian import lagrangian_allocate
from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.world import clone_shared_world, generate_shared_world
from revive.config.policy_pack import official_sealed_policy_pack
from revive.simulation.observation import get_observable_state
from revive.simulation.types import GenerationProfile
from revive.recovery.context.assemble import assemble_context
from revive.recovery.candidates.generate import generate_candidates
from revive.recovery.diagnosis.diagnose import diagnose
from revive.recovery.sentinel.detect import detect
from revive.recovery.valuation.price import price_candidates
from revive.allocation.resources import portfolio_item_from_valuation


@dataclass
class CycleAllocationSnapshot:
  seed: int
  profile: str
  cycle_index: int
  opportunity_count: int
  portfolio_item_count: int
  candidate_count: int
  lagrangian_seconds: float
  allocate_seconds: float
  iterations: int | None
  allocation_hash: str | None


def build_portfolio_for_cycle(bundle, policy_pack, cycle_index: int):
    world = clone_shared_world(bundle).world
    cycle_times = bundle.cycle_times_micros
    now_micros = cycle_times[cycle_index]
    view = get_observable_state(world)
    sentinel = detect(view, now_micros)
    portfolio_items = []
    candidate_count = 0
    for opp in sentinel.opportunities:
        ctx = assemble_context(opp, view, now_micros)
        dx = diagnose(opp, ctx, view, now_micros, f"cyc_{cycle_index:04d}")
        cand_set = generate_candidates(
            opp, dx.observable_context, dx, now_micros, f"cyc_{cycle_index:04d}", policy=policy_pack
        )
        val_result = price_candidates(
            opp, dx.observable_context, dx, cand_set, now_micros, policy=policy_pack
        )
        item = portfolio_item_from_valuation(
            opp.opportunity_id,
            opp.customer_id,
            opp.value_at_risk_paise,
            cand_set.candidates,
            val_result.valuations,
        )
        portfolio_items.append(item)
        candidate_count += len(item.candidates)
    return tuple(portfolio_items), candidate_count, len(sentinel.opportunities)


def profile_slow_case(seed: int = 2, profile: str = "BALANCED", cycle_index: int = 0):
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen_config = generator_config_for_cell(config, seed, GenerationProfile(profile))
    bundle = generate_shared_world(gen_config)
    caps = benchmark_resource_capacities(profile_from_string(profile))
    state = default_resource_state(caps)
    cfg = default_allocator_config()

    items, candidate_count, opp_count = build_portfolio_for_cycle(bundle, pack, cycle_index)
    now_micros = bundle.cycle_times_micros[cycle_index]

    # Profile lagrangian_allocate only
    profiler = cProfile.Profile()
    t0 = time.perf_counter()
    profiler.enable()
    relaxed, lambdas, gap, mode = lagrangian_allocate(items, state, pack.epsilon_paise, cfg)
    profiler.disable()
    lag_s = time.perf_counter() - t0

    # Full allocate_portfolio
    state2 = default_resource_state(caps)
    t1 = time.perf_counter()
    result = allocate_portfolio(items, state2, now_micros, f"cyc_{cycle_index:04d}", policy=pack, config=cfg)
    alloc_s = time.perf_counter() - t1

    s = StringIO()
    stats = pstats.Stats(profiler, stream=s)
    stats.sort_stats("cumulative")
    stats.print_stats(40)

    return {
        "seed": seed,
        "profile": profile,
        "cycle_index": cycle_index,
        "opportunity_count": opp_count,
        "portfolio_item_count": len(items),
        "candidate_count": candidate_count,
        "lagrangian_seconds": lag_s,
        "allocate_seconds": alloc_s,
        "mode": mode.value,
        "duality_gap": gap,
        "allocation_hash": result.allocation_hash,
        "total_enrv": result.total_allocated_enrv_paise,
        "profile_text": s.getvalue(),
    }


if __name__ == "__main__":
    out_dir = Path("implementation/m13-12-performance")
    out_dir.mkdir(parents=True, exist_ok=True)
    data = profile_slow_case()
    (out_dir / "baseline-profile-raw.json").write_text(
        json.dumps({k: v for k, v in data.items() if k != "profile_text"}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "baseline-profile-cumulative.txt").write_text(data["profile_text"], encoding="utf-8")
    print(json.dumps({k: v for k, v in data.items() if k != "profile_text"}, indent=2))
