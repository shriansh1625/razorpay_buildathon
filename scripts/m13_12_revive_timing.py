"""Compare REVIVE 50-cycle wall time before/after M13.12."""

from __future__ import annotations

import json
import time

from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.revive_pipeline import new_revive_state, run_revive_cycle
from revive.benchmark.official.world import generate_shared_world
from revive.config.policy_pack import official_sealed_policy_pack
from revive.simulation.types import GenerationProfile


def run_cycles(max_cycles: int = 50, seed: int = 2, profile: str = "BALANCED") -> float:
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen_config = generator_config_for_cell(config, seed, GenerationProfile(profile))
    bundle = generate_shared_world(gen_config)
    caps = benchmark_resource_capacities(profile_from_string(profile))
    state = new_revive_state(bundle, pack, caps)
    cycles = bundle.cycle_times_micros[:max_cycles]
    t0 = time.perf_counter()
    for idx, now_micros in enumerate(cycles):
        run_revive_cycle(state, f"cyc_{idx:04d}", now_micros)
    return time.perf_counter() - t0


if __name__ == "__main__":
    seconds = run_cycles()
    print(json.dumps({"seed": 2, "profile": "BALANCED", "cycles": 50, "seconds": round(seconds, 2)}))
