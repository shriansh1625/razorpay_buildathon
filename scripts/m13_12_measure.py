"""M13.12 performance measurement script."""

from __future__ import annotations

import json
import time
from pathlib import Path

from revive.allocation import allocate_portfolio, default_allocator_config, default_resource_state
from revive.allocation.lagrangian import lagrangian_allocate as lagrangian_opt
from revive.allocation.lagrangian_reference import lagrangian_allocate as lagrangian_ref
from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.world import generate_shared_world
from revive.config.policy_pack import official_sealed_policy_pack
from revive.simulation.types import GenerationProfile
from revive.recovery.context.assemble import assemble_context
from revive.recovery.candidates.generate import generate_candidates
from revive.recovery.diagnosis.diagnose import diagnose
from revive.recovery.sentinel.detect import detect
from revive.recovery.valuation.price import price_candidates
from revive.allocation.resources import portfolio_item_from_valuation
from revive.simulation.observation import get_observable_state


def portfolio(seed, profile, cycle):
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen_config = generator_config_for_cell(config, seed, GenerationProfile(profile))
    bundle = generate_shared_world(gen_config)
    now_micros = bundle.cycle_times_micros[cycle]
    view = get_observable_state(bundle.world)
    sentinel = detect(view, now_micros)
    items = []
    candidates = 0
    for opp in sentinel.opportunities:
        ctx = assemble_context(opp, view, now_micros)
        dx = diagnose(opp, ctx, view, now_micros, f"cyc_{cycle:04d}")
        cand_set = generate_candidates(
            opp, dx.observable_context, dx, now_micros, f"cyc_{cycle:04d}", policy=pack
        )
        val_result = price_candidates(
            opp, dx.observable_context, dx, cand_set, now_micros, policy=pack
        )
        item = portfolio_item_from_valuation(
            opp.opportunity_id,
            opp.customer_id,
            opp.value_at_risk_paise,
            cand_set.candidates,
            val_result.valuations,
        )
        items.append(item)
        candidates += len(item.candidates)
    return tuple(items), pack, candidates, len(sentinel.opportunities)


def bench_lagrangian(fn, items, state, epsilon, cfg, runs=5):
    for _ in range(2):
        fn(items, default_resource_state(state.capacities), epsilon, cfg)
    start = time.perf_counter()
    for _ in range(runs):
        fn(items, default_resource_state(state.capacities), epsilon, cfg)
    return (time.perf_counter() - start) / runs


def main():
    cfg = default_allocator_config()
    cases = [
        (2, "BALANCED", 0),
        (2, "BALANCED", 1457),
        (5, "SCARCE", 500),
        (7, "HIGH_NATURAL", 800),
        (3, "ABUNDANT", 400),
        (4, "HOSTILE", 600),
        (6, "DEGRADED", 700),
    ]
    rows = []
    for seed, profile, cycle in cases:
        items, pack, cand_count, opp_count = portfolio(seed, profile, cycle)
        caps = benchmark_resource_capacities(profile_from_string(profile))
        state = default_resource_state(caps)
        ref_t = bench_lagrangian(lagrangian_ref, items, state, pack.epsilon_paise, cfg)
        opt_t = bench_lagrangian(lagrangian_opt, items, state, pack.epsilon_paise, cfg)
        ref_alloc = allocate_portfolio(items, default_resource_state(caps), 1, "r", policy=pack, config=cfg)
        opt_alloc = allocate_portfolio(items, default_resource_state(caps), 1, "o", policy=pack, config=cfg)
        rows.append(
            {
                "seed": seed,
                "profile": profile,
                "cycle": cycle,
                "opportunities": opp_count,
                "candidates": cand_count,
                "lagrangian_ref_seconds": round(ref_t, 4),
                "lagrangian_opt_seconds": round(opt_t, 4),
                "speedup": round(ref_t / opt_t, 2) if opt_t else None,
                "allocation_hash_match": ref_alloc.allocation_hash == opt_alloc.allocation_hash,
            }
        )
    out = Path("implementation/m13-12-performance/performance-results.json")
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
