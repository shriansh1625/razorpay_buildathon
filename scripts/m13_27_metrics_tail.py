"""M13.27 metrics tail before/after measurement — development only."""

from __future__ import annotations

import json
import time
from pathlib import Path

OUTPUT = Path("implementation/m13-27-metrics-tail-rescue")


def _run_abundant_population():
    from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
    from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
    from revive.benchmark.official.policies import BenchmarkPolicyId
    from revive.benchmark.official.revive_pipeline import new_revive_state, run_revive_cycle
    from revive.benchmark.official.world import clone_shared_world, generate_shared_world
    from revive.config.policy_pack import official_sealed_policy_pack
    from revive.simulation.types import GenerationProfile

    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen_config = generator_config_for_cell(config, 1, GenerationProfile("ABUNDANT"))
    bundle = generate_shared_world(gen_config)
    cloned = clone_shared_world(bundle)
    caps = benchmark_resource_capacities(profile_from_string("ABUNDANT"))
    state = new_revive_state(cloned, pack, caps)
    for idx, now_micros in enumerate(cloned.cycle_times_micros):
        run_revive_cycle(state, f"cyc_{idx:04d}", now_micros)
    return (
        tuple(state.measurements),
        tuple(state.executions),
        tuple(state.authorizations),
        caps,
        cloned.seed,
        cloned.profile,
        BenchmarkPolicyId.REVIVE.value,
    )


def main() -> None:
    from revive.benchmark.official.cells.store import metrics_checksum
    from revive.benchmark.official.metrics import compute_policy_metrics

    OUTPUT.mkdir(parents=True, exist_ok=True)
    (
        measurements,
        executions,
        authorizations,
        caps,
        seed,
        profile,
        policy_id,
    ) = _run_abundant_population()

    kwargs = {
        "policy_id": policy_id,
        "seed": seed,
        "profile": profile,
        "measurements": measurements,
        "executions": executions,
        "authorizations": authorizations,
        "incentive_budget_capacity_paise": caps.incentive_budget_paise,
        "retry_capacity": caps.retry_slots,
        "message_capacity": caps.message_capacity,
    }

    cpu0 = time.process_time()
    t0 = time.perf_counter()
    metrics = compute_policy_metrics(**kwargs)
    wall = time.perf_counter() - t0
    cpu = time.process_time() - cpu0
    payload = metrics.to_dict()
    checksum = metrics_checksum(payload)

    report = {
        "seed": seed,
        "profile": profile,
        "policy": policy_id,
        "execution_count": len(executions),
        "authorization_count": len(authorizations),
        "measurement_count": len(measurements),
        "metrics_checksum": checksum,
        "metrics": payload,
        "compute_policy_metrics_wall_seconds": wall,
        "compute_policy_metrics_cpu_seconds": cpu,
    }
    (OUTPUT / "abundant-metrics-tail.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({k: report[k] for k in report if k != "metrics"}, indent=2))


if __name__ == "__main__":
    main()
