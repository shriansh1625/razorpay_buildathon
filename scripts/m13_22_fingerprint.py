"""M13.22 semantic fingerprints — development only, not official evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.revive_pipeline import new_revive_state, run_revive_cycle
from revive.benchmark.official.world import clone_shared_world, generate_shared_world
from revive.config.policy_pack import official_sealed_policy_pack
from revive.recovery.candidates.generate import generate_candidates
from revive.recovery.context.assemble import assemble_context
from revive.recovery.diagnosis.diagnose import diagnose
from revive.recovery.sentinel.detect import detect
from revive.recovery.valuation.price import price_candidates
from revive.benchmark.official.performance.cycle_cache import CycleViewCache
from revive.simulation.observation import get_observable_state
from revive.simulation.types import GenerationProfile


def _sha(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def cycle_m6_m7_fingerprint(seed: int, profile: str, cycles: int = 15) -> dict:
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen = generator_config_for_cell(config, seed, GenerationProfile(profile))
    bundle = generate_shared_world(gen)
    cloned = clone_shared_world(bundle)
    view = get_observable_state(cloned.world)
    now = cloned.cycle_times_micros[0]
    cache = CycleViewCache(view, now)
    sentinel = detect(view, now)

    m6: list[dict] = []
    m7: list[dict] = []
    for opp in sentinel.opportunities:
        ctx = assemble_context(opp, view, now, cycle_cache=cache)
        dx = diagnose(opp, ctx, view, now, "cyc_0000")
        cand = generate_candidates(
            opp, dx.observable_context, dx, now, "cyc_0000", policy=pack
        )
        priced = price_candidates(
            opp, dx.observable_context, dx, cand, now, policy=pack
        )
        m6.append(
            {
                "opportunity_id": opp.opportunity_id,
                "candidates": [c.to_dict() for c in cand.candidates],
            }
        )
        m7.append(
            {
                "opportunity_id": opp.opportunity_id,
                "valuations": [v.to_dict() for v in priced.valuations],
                "p_natural": priced.p_natural,
            }
        )

    # Multi-cycle end-to-end metrics fingerprint (execution included).
    caps = benchmark_resource_capacities(profile_from_string(profile))
    state = new_revive_state(clone_shared_world(bundle), pack, caps)
    for idx in range(cycles):
        run_revive_cycle(state, f"cyc_{idx:04d}", cloned.cycle_times_micros[idx])

    from revive.benchmark.official.cells.store import metrics_checksum
    from revive.benchmark.official.metrics import compute_policy_metrics
    from revive.benchmark.official.policies import BenchmarkPolicyId

    metrics = compute_policy_metrics(
        BenchmarkPolicyId.REVIVE.value,
        cloned.seed,
        cloned.profile,
        tuple(state.measurements),
        tuple(state.executions),
        tuple(state.authorizations),
        incentive_budget_capacity_paise=caps.incentive_budget_paise,
        retry_capacity=caps.retry_slots,
        message_capacity=caps.message_capacity,
    )
    return {
        "seed": seed,
        "profile": profile,
        "cycles": cycles,
        "m4_opportunity_count": len(sentinel.opportunities),
        "m6_hash": _sha(m6),
        "m7_hash": _sha(m7),
        "metrics_checksum": metrics_checksum(metrics.to_dict()),
        "intervention_count": metrics.intervention_count,
    }


if __name__ == "__main__":
    out = Path("implementation/m13-22-m6-m7-performance")
    out.mkdir(parents=True, exist_ok=True)
    result = cycle_m6_m7_fingerprint(2, "BALANCED", cycles=15)
    (out / "fingerprint-seed2-balanced-15.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
