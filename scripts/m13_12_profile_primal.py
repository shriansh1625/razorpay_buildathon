"""Profile primal_recovery vs lagrangian for worst cycle."""

from __future__ import annotations

import cProfile
import pstats
import time
from io import StringIO

from revive.allocation import default_allocator_config, default_resource_state
from revive.allocation.lagrangian import lagrangian_allocate, primal_recovery, _reduced_value_paise
from scripts.m13_12_profile import build_portfolio_for_cycle
from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.world import generate_shared_world
from revive.config.policy_pack import official_sealed_policy_pack
from revive.simulation.types import GenerationProfile


def main():
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen_config = generator_config_for_cell(config, 2, GenerationProfile.BALANCED)
    bundle = generate_shared_world(gen_config)
    caps = benchmark_resource_capacities(profile_from_string("BALANCED"))
    cfg = default_allocator_config()
    items, _, _ = build_portfolio_for_cycle(bundle, pack, 1457)
    state = default_resource_state(caps)

    profiler = cProfile.Profile()
    profiler.enable()
    t0 = time.perf_counter()
    picks, lambdas, gap, mode = lagrangian_allocate(items, state, pack.epsilon_paise, cfg)
    t1 = time.perf_counter()
    best_rvs = {}
    for item in items:
        pc = picks.get(item.opportunity_id)
        if pc is not None:
            best_rvs[item.opportunity_id] = _reduced_value_paise(pc, lambdas, item.customer_id)
        else:
            best_rvs[item.opportunity_id] = 0
    state2 = default_resource_state(caps)
    primal_recovery(items, picks, best_rvs, state2, pack.epsilon_paise, lambdas)
    t2 = time.perf_counter()
    profiler.disable()
    print(f"lagrangian={t1-t0:.3f}s primal={t2-t1:.3f}s")
    s = StringIO()
    pstats.Stats(profiler, stream=s).sort_stats("cumulative").print_stats(25)
    print(s.getvalue())


if __name__ == "__main__":
    main()
