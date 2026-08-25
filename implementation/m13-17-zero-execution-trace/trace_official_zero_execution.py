"""M13.17 read-only diagnostic — trace zero execution on official config.

Does NOT modify repository logic or official artifacts.
Run: python implementation/m13-17-zero-execution-trace/trace_official_zero_execution.py
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from revive.allocation import allocate_portfolio, default_resource_state, portfolio_item_from_valuation
from revive.benchmark.capacities import baseline_environment_for_profile, benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.baseline_pipeline import new_baseline_state, run_baseline_cycle_full
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.revive_pipeline import new_revive_state, run_revive_cycle
from revive.benchmark.official.world import clone_shared_world, generate_shared_world
from revive.benchmark.runner import run_baseline_cycle
from revive.benchmark.types import BaselineCycleContext, BaselinePolicyId
from revive.config.policy_pack import official_sealed_policy_pack
from revive.domain.enums import ActionCode, DecisionOutcome
from revive.recovery.context.assemble import assemble_context
from revive.recovery.candidates.generate import generate_candidates
from revive.recovery.diagnosis.diagnose import diagnose
from revive.recovery.sentinel.detect import detect
from revive.recovery.valuation.price import price_candidates
from revive.simulation.observation import get_observable_state
from revive.simulation.types import GenerationProfile

OUTPUT = Path(__file__).resolve().parent / "trace_results.json"
SEED = 1
PROFILE = GenerationProfile.BALANCED


@dataclass
class BaselineTrace:
    policy: str
    cycles: int
    baseline_selected_total: int = 0
    selected_not_in_sentinel: int = 0
    skip_no_detected: int = 0
    skip_cand_missing: int = 0
    skip_val_missing: int = 0
    reached_auth_input: int = 0
    authorizations: int = 0
    executions: int = 0
    measurements: int = 0
    auth_states: dict[str, int] = field(default_factory=dict)
    block_reasons: dict[str, int] = field(default_factory=dict)


@dataclass
class ReviveTrace:
    cycles: int
    sentinel_opportunities: int = 0
    candidates: int = 0
    valuations: int = 0
    enrv_positive: int = 0
    m8_selected: int = 0
    authorizations: int = 0
    executions: int = 0
    measurements: int = 0
    auth_states: dict[str, int] = field(default_factory=dict)
    g7_triggers: dict[str, int] = field(default_factory=dict)


def _official_bundle():
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen = generator_config_for_cell(config, SEED, PROFILE)
    return pack, generate_shared_world(gen)


def trace_baseline(pack, bundle, policy_id: BaselinePolicyId) -> BaselineTrace:
    cloned = clone_shared_world(bundle)
    state = new_baseline_state(cloned, policy_id, pack)
    profile = profile_from_string(cloned.profile)
    env = baseline_environment_for_profile(profile)
    counts = Counter()

    for idx, now in enumerate(cloned.cycle_times_micros):
        view = get_observable_state(cloned.world)
        if state.baseline_context is None:
            state.baseline_context = BaselineCycleContext(
                cycle_id=f"cyc_{idx:04d}",
                now_micros=now,
                epsilon_paise=pack.epsilon_paise,
                contact_allowance_per_customer=env.contact_allowance_per_customer,
                retry_slots_per_cycle=env.retry_slots_per_cycle,
                message_capacity_per_cycle=env.message_capacity_per_cycle,
            )
        else:
            state.baseline_context.cycle_id = f"cyc_{idx:04d}"
            state.baseline_context.now_micros = now
            state.baseline_context.retry_slots_used = 0
            state.baseline_context.message_capacity_used = 0

        cycle_result = run_baseline_cycle(
            policy_id,
            view,
            cycle_id=f"cyc_{idx:04d}",
            now_micros=now,
            policy_pack=pack,
            env=env,
            persist_context=state.baseline_context,
        )
        sentinel = detect(view, now)
        det_ids = {o.opportunity_id for o in sentinel.opportunities}
        opp_by_id = {o.opportunity_id: o for o in sentinel.opportunities}

        selected = [
            d
            for d in cycle_result.decisions
            if d.outcome == DecisionOutcome.SELECTED and d.action_code != ActionCode.A00
        ]
        for bd in selected:
            counts["baseline_selected_total"] += 1
            if bd.opportunity_id not in det_ids:
                counts["selected_not_in_sentinel"] += 1
            detected = opp_by_id.get(bd.opportunity_id)
            if detected is None:
                counts["skip_no_detected"] += 1
                continue
            ctx = assemble_context(detected, view, now)
            dx = diagnose(detected, ctx, view, now, f"cyc_{idx:04d}")
            cand_set = generate_candidates(
                detected, dx.observable_context, dx, now, f"cyc_{idx:04d}", policy=pack
            )
            val_result = price_candidates(
                detected, dx.observable_context, dx, cand_set, now, policy=pack
            )
            cand = next((c for c in cand_set.candidates if c.action_code == bd.action_code), None)
            if cand is None:
                counts["skip_cand_missing"] += 1
                continue
            val = next((v for v in val_result.valuations if v.candidate_id == cand.candidate_id), None)
            if val is None:
                counts["skip_val_missing"] += 1
                continue
            counts["reached_auth_input"] += 1

        run_baseline_cycle_full(state, f"cyc_{idx:04d}", now)

    auth_states = Counter(a.authorization_state.value for a in state.authorizations)
    block_reasons = Counter(
        a.blocking_reason_code
        for a in state.authorizations
        if a.authorization_state.value != "AUTHORIZED"
    )
    return BaselineTrace(
        policy=policy_id.value,
        cycles=len(cloned.cycle_times_micros),
        baseline_selected_total=counts["baseline_selected_total"],
        selected_not_in_sentinel=counts["selected_not_in_sentinel"],
        skip_no_detected=counts["skip_no_detected"],
        skip_cand_missing=counts["skip_cand_missing"],
        skip_val_missing=counts["skip_val_missing"],
        reached_auth_input=counts["reached_auth_input"],
        authorizations=len(state.authorizations),
        executions=len(state.executions),
        measurements=len(state.measurements),
        auth_states=dict(auth_states),
        block_reasons=dict(block_reasons),
    )


def trace_revive(pack, bundle) -> ReviveTrace:
    cloned = clone_shared_world(bundle)
    caps = benchmark_resource_capacities(profile_from_string(cloned.profile))
    state = new_revive_state(cloned, pack, caps)
    counts = Counter()
    g7 = Counter()

    for idx, now in enumerate(cloned.cycle_times_micros):
        view = get_observable_state(cloned.world)
        sentinel = detect(view, now)
        counts["sentinel_opportunities"] += len(sentinel.opportunities)
        portfolio_items = []
        for opp in sentinel.opportunities:
            ctx = assemble_context(opp, view, now)
            dx = diagnose(opp, ctx, view, now, f"cyc_{idx:04d}")
            cand_set = generate_candidates(
                opp, dx.observable_context, dx, now, f"cyc_{idx:04d}", policy=pack
            )
            val_result = price_candidates(
                opp, dx.observable_context, dx, cand_set, now, policy=pack
            )
            counts["candidates"] += len(cand_set.candidates)
            counts["valuations"] += len(val_result.valuations)
            counts["enrv_positive"] += sum(
                1 for v in val_result.valuations if v.enrv_paise > pack.epsilon_paise
            )
            portfolio_items.append(
                portfolio_item_from_valuation(
                    opp.opportunity_id,
                    opp.customer_id,
                    opp.value_at_risk_paise,
                    cand_set.candidates,
                    val_result.valuations,
                )
            )
        if portfolio_items:
            allocation = allocate_portfolio(
                tuple(portfolio_items),
                state.resource_state,
                now,
                f"cyc_{idx:04d}",
                policy=pack,
            )
            counts["m8_selected"] += sum(
                1
                for a in allocation.assignments
                if a.outcome == DecisionOutcome.SELECTED and a.action_code != ActionCode.A00
            )
        run_revive_cycle(state, f"cyc_{idx:04d}", now)

    for auth in state.authorizations:
        for gate in auth.gate_trace:
            if gate.gate_id == "G7" and gate.detail and "triggers" in gate.detail:
                for trigger in gate.detail["triggers"]:
                    g7[trigger] += 1

    auth_states = Counter(a.authorization_state.value for a in state.authorizations)
    return ReviveTrace(
        cycles=len(cloned.cycle_times_micros),
        sentinel_opportunities=counts["sentinel_opportunities"],
        candidates=counts["candidates"],
        valuations=counts["valuations"],
        enrv_positive=counts["enrv_positive"],
        m8_selected=counts["m8_selected"],
        authorizations=len(state.authorizations),
        executions=len(state.executions),
        measurements=len(state.measurements),
        auth_states=dict(auth_states),
        g7_triggers=dict(g7),
    )


def main() -> None:
    pack, bundle = _official_bundle()
    results = {
        "seed": SEED,
        "profile": PROFILE.value,
        "cycles": len(bundle.cycle_times_micros),
        "world_opportunities": len(bundle.world.opportunities),
        "config_hash": official_benchmark_config(policy_pack=pack).to_dict().get(
            "generator_config"
        ),
        "baselines": {},
        "revive": None,
    }
    for pid in (BaselinePolicyId.B1, BaselinePolicyId.B2, BaselinePolicyId.B3):
        print(f"Tracing baseline {pid.value} ...")
        results["baselines"][pid.value] = asdict(trace_baseline(pack, bundle, pid))
    print("Tracing REVIVE ...")
    results["revive"] = asdict(trace_revive(pack, bundle))
    OUTPUT.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
