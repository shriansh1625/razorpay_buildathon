"""Find slowest allocation cycle for official-scale REVIVE reproduction."""

from __future__ import annotations

import json
import time
from pathlib import Path

from revive.allocation import allocate_portfolio, default_allocator_config, default_resource_state
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


def profile_all_cycles(seed: int = 2, profile: str = "BALANCED"):
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen_config = generator_config_for_cell(config, seed, GenerationProfile(profile))
    bundle = generate_shared_world(gen_config)
    caps = benchmark_resource_capacities(profile_from_string(profile))
    cfg = default_allocator_config()
    rows = []
    for cycle_index, now_micros in enumerate(bundle.cycle_times_micros):
        world = clone_shared_world(bundle).world
        view = get_observable_state(world)
        sentinel = detect(view, now_micros)
        portfolio_items = []
        candidate_count = 0
        for opp in sentinel.opportunities:
            ctx = assemble_context(opp, view, now_micros)
            dx = diagnose(opp, ctx, view, now_micros, f"cyc_{cycle_index:04d}")
            cand_set = generate_candidates(
                opp, dx.observable_context, dx, now_micros, f"cyc_{cycle_index:04d}", policy=pack
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
            portfolio_items.append(item)
            candidate_count += len(item.candidates)
        if not portfolio_items:
            continue
        state = default_resource_state(caps)
        t0 = time.perf_counter()
        result = allocate_portfolio(
            tuple(portfolio_items),
            state,
            now_micros,
            f"cyc_{cycle_index:04d}",
            policy=pack,
            config=cfg,
        )
        elapsed = time.perf_counter() - t0
        rows.append(
            {
                "cycle": cycle_index,
                "opps": len(portfolio_items),
                "candidates": candidate_count,
                "seconds": elapsed,
                "hash": result.allocation_hash,
                "enrv": result.total_allocated_enrv_paise,
            }
        )
    rows.sort(key=lambda r: r["seconds"], reverse=True)
    return rows


if __name__ == "__main__":
    rows = profile_all_cycles()
    print(json.dumps(rows[:10], indent=2))
    total = sum(r["seconds"] for r in rows)
    print(f"cycles={len(rows)} total_allocate_seconds={total:.2f}")
