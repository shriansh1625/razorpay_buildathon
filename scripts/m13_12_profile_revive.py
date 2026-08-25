"""Full REVIVE cell timing breakdown — M13.12."""

from __future__ import annotations

import cProfile
import json
import pstats
import time
from io import StringIO
from pathlib import Path

from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.revive_pipeline import new_revive_state, run_revive_cycle
from revive.benchmark.official.world import generate_shared_world
from revive.config.policy_pack import official_sealed_policy_pack
from revive.simulation.types import GenerationProfile


def time_full_cell(seed: int = 2, profile: str = "BALANCED", max_cycles: int | None = None):
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen_config = generator_config_for_cell(config, seed, GenerationProfile(profile))
    bundle = generate_shared_world(gen_config)
    caps = benchmark_resource_capacities(profile_from_string(profile))
    state = new_revive_state(bundle, pack, caps)

    cycles = bundle.cycle_times_micros
    if max_cycles is not None:
        cycles = cycles[:max_cycles]

    profiler = cProfile.Profile()
    t0 = time.perf_counter()
    profiler.enable()
    for idx, now_micros in enumerate(cycles):
        run_revive_cycle(state, f"cyc_{idx:04d}", now_micros)
    profiler.disable()
    total = time.perf_counter() - t0

    s = StringIO()
    stats = pstats.Stats(profiler, stream=s)
    stats.sort_stats("cumulative")
    stats.print_stats(30)

    return {
        "seed": seed,
        "profile": profile,
        "cycles_run": len(cycles),
        "total_seconds": total,
        "measurements": len(state.measurements),
        "profile_top": s.getvalue(),
    }


if __name__ == "__main__":
    # Quick sample: 50 cycles
    data = time_full_cell(max_cycles=50)
    out = Path("implementation/m13-12-performance")
    out.mkdir(parents=True, exist_ok=True)
    (out / "revive-50cycles-profile.txt").write_text(data["profile_top"], encoding="utf-8")
    print(json.dumps({k: v for k, v in data.items() if k != "profile_top"}, indent=2))
