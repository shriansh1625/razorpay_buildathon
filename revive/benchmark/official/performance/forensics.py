"""Single-cell REVIVE forensics — M13.26 development only."""

from __future__ import annotations

import heapq
import statistics
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from revive.allocation import allocate_portfolio, portfolio_item_from_valuation
from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.metrics import compute_policy_metrics
from revive.benchmark.official.policies import BenchmarkPolicyId
from revive.benchmark.official.revive_pipeline import new_revive_state
from revive.benchmark.official.world import clone_shared_world, generate_shared_world
from revive.config.policy_pack import official_sealed_policy_pack
from revive.domain.enums import ActionCode
from revive.recovery.candidates.rules import enumerate_action_codes
from revive.recovery.context.assemble import assemble_context
from revive.recovery.candidates.generate import generate_candidates
from revive.recovery.diagnosis.diagnose import diagnose
from revive.recovery.sentinel.detect import detect
from revive.recovery.valuation.price import price_candidates
from revive.simulation.observation import get_observable_state
from revive.simulation.types import GenerationProfile


@dataclass
class OpportunityForensic:
    opportunity_id: str
    cycle_id: str
    m6_seconds: float
    m7_seconds: float
    action_codes_enumerated: int
    candidates_total: int
    candidates_available: int
    candidate_actions: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "cycle_id": self.cycle_id,
            "m6_seconds": self.m6_seconds,
            "m7_seconds": self.m7_seconds,
            "action_codes_enumerated": self.action_codes_enumerated,
            "candidates_total": self.candidates_total,
            "candidates_available": self.candidates_available,
            "candidate_actions": self.candidate_actions,
        }


@dataclass
class CycleForensic:
    cycle_id: str
    cycle_index: int
    wall_seconds: float
    m4_seconds: float
    m5_seconds: float
    m6_seconds: float
    m7_seconds: float
    m8_seconds: float
    m9_m12_seconds: float
    opportunity_count: int
    candidate_count: int
    valuation_count: int
    portfolio_size: int
    selected_count: int
    authorization_count: int
    execution_count: int
    measurement_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "cycle_index": self.cycle_index,
            "wall_seconds": self.wall_seconds,
            "m4_seconds": self.m4_seconds,
            "m5_seconds": self.m5_seconds,
            "m6_seconds": self.m6_seconds,
            "m7_seconds": self.m7_seconds,
            "m8_seconds": self.m8_seconds,
            "m9_m12_seconds": self.m9_m12_seconds,
            "opportunity_count": self.opportunity_count,
            "candidate_count": self.candidate_count,
            "valuation_count": self.valuation_count,
            "portfolio_size": self.portfolio_size,
            "selected_count": self.selected_count,
            "authorization_count": self.authorization_count,
            "execution_count": self.execution_count,
            "measurement_count": self.measurement_count,
        }


@dataclass
class CellForensicReport:
    seed: int
    profile: str
    wall_seconds: float
    cpu_seconds: float | None
    peak_rss_bytes: int | None
    cycle_count: int
    stage_totals: dict[str, float]
    counters: dict[str, int]
    cycles: list[CycleForensic] = field(default_factory=list)
    opportunities: list[OpportunityForensic] = field(default_factory=list)
    top_m6_opportunities: list[OpportunityForensic] = field(default_factory=list)
    top_m7_opportunities: list[OpportunityForensic] = field(default_factory=list)
    capacities: dict[str, int] = field(default_factory=dict)

    def candidate_per_opp_stats(self) -> dict[str, float]:
        counts = [
            c.candidate_count
            for c in self.cycles
            if c.opportunity_count > 0
        ]
        per_opp = []
        for cycle in self.cycles:
            if cycle.opportunity_count:
                per_opp.append(cycle.candidate_count / cycle.opportunity_count)
        if not per_opp:
            return {}
        ordered = sorted(per_opp)
        return {
            "mean": statistics.mean(per_opp),
            "median": statistics.median(per_opp),
            "p95": ordered[int(0.95 * (len(ordered) - 1))],
            "max": max(per_opp),
        }

    def cycle_time_stats(self) -> dict[str, float]:
        times = [c.wall_seconds for c in self.cycles]
        if not times:
            return {}
        ordered = sorted(times)
        return {
            "median": statistics.median(times),
            "p95": ordered[int(0.95 * (len(ordered) - 1))],
            "p99": ordered[int(0.99 * (len(ordered) - 1))],
            "max": max(times),
            "total": sum(times),
        }

    def to_dict(self, *, include_details: bool = False) -> dict[str, Any]:
        payload = {
            "seed": self.seed,
            "profile": self.profile,
            "wall_seconds": self.wall_seconds,
            "cpu_seconds": self.cpu_seconds,
            "peak_rss_bytes": self.peak_rss_bytes,
            "cycle_count": self.cycle_count,
            "stage_totals": self.stage_totals,
            "counters": self.counters,
            "capacities": self.capacities,
            "candidate_per_opportunity": self.candidate_per_opp_stats(),
            "cycle_time_stats": self.cycle_time_stats(),
        }
        if include_details:
            payload["cycles"] = [c.to_dict() for c in self.cycles]
            payload["opportunities"] = [o.to_dict() for o in self.opportunities]
        else:
            payload["slowest_cycles"] = slowest_cycles(self, 10)
            payload["top_m6_opportunities"] = [
                o.to_dict() for o in self.top_m6_opportunities
            ]
            payload["top_m7_opportunities"] = [
                o.to_dict() for o in self.top_m7_opportunities
            ]
        return payload


def _push_top_opportunity(
    heap: list[tuple[float, int, OpportunityForensic]],
    item: OpportunityForensic,
    score: float,
    *,
    limit: int = 10,
) -> None:
    """Track top-N opportunities without retaining the full per-opp stream."""
    entry = (score, id(item), item)
    if len(heap) < limit:
        heapq.heappush(heap, entry)
    elif score > heap[0][0]:
        heapq.heapreplace(heap, entry)


def _finalize_top_opportunities(
    heap: list[tuple[float, int, OpportunityForensic]],
) -> list[OpportunityForensic]:
    return [item for _, _, item in sorted(heap, key=lambda x: x[0], reverse=True)]


def _profile_one_opportunity_forensic(
    *,
    opp,
    view,
    now_micros: int,
    cycle_id: str,
    state,
    cycle_cache,
) -> tuple[OpportunityForensic, object, object, object]:
    t_ctx = time.perf_counter()
    ctx = assemble_context(
        opp, view, now_micros, cycle_cache=cycle_cache
    )
    dx = diagnose(opp, ctx, view, now_micros, cycle_id)
    m5_part = time.perf_counter() - t_ctx

    action_codes = enumerate_action_codes(opp.risk_class, dx)
    t6 = time.perf_counter()
    cand_set = generate_candidates(
        opp,
        dx.observable_context,
        dx,
        now_micros,
        cycle_id,
        policy=state.policy_pack,
        config=state.candidate_cfg(),
    )
    m6 = time.perf_counter() - t6

    t7 = time.perf_counter()
    val_result = price_candidates(
        opp,
        dx.observable_context,
        dx,
        cand_set,
        now_micros,
        policy=state.policy_pack,
        config=state.valuation_cfg(),
    )
    m7 = time.perf_counter() - t7

    action_hist = Counter(c.action_code.value for c in cand_set.candidates)
    available = sum(
        1 for c in cand_set.candidates if c.action_code != ActionCode.A00
    )
    forensic = OpportunityForensic(
        opportunity_id=opp.opportunity_id,
        cycle_id=cycle_id,
        m6_seconds=m6,
        m7_seconds=m7,
        action_codes_enumerated=len(action_codes),
        candidates_total=len(cand_set.candidates),
        candidates_available=available,
        candidate_actions=dict(action_hist),
    )
    return forensic, cand_set, val_result, m5_part


def profile_revive_cell_forensic(
    seed: int,
    profile: str,
    *,
    progress_every: int = 100,
    progress_callback=None,
) -> CellForensicReport:
    """Full official-scale REVIVE cell with per-cycle and per-opportunity forensics."""
    import os

    from revive.allocation.resources import clear_usage_cache
    from revive.benchmark.official.cells.telemetry import PeakRssTracker
    from revive.benchmark.official.performance.profiling import StageTotals
    from revive.recovery.sentinel.identity_bridge import index_world_opportunities_by_natural_key
    from revive.domain.enums import DecisionOutcome, OpportunityState
    from revive.decision.seal import seal_allocation
    from revive.policy import AuthorizeContext, authorize_execution
    from revive.policy.models import AuthorizationState
    from revive.policy.simulated_approver import authorize_context_with_simulated_approval
    from revive.benchmark.official.freeze_constants import OFFICIAL_APPROVER_VERSION
    from revive.execution import ExecutionEnvironment, execute_authorization
    from revive.measurement import measure_execution
    from revive.policy.config import PolicyRules
    from revive.benchmark.official.world import find_opportunity, increment_contact, mark_recovered
    from revive.decision.ledger import ReservationLedger
    from revive.allocation.models import AllocationResult
    from dataclasses import replace

    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen_config = generator_config_for_cell(config, seed, GenerationProfile(profile))
    bundle = generate_shared_world(gen_config)
    cloned = clone_shared_world(bundle)
    caps = benchmark_resource_capacities(profile_from_string(profile))
    state = new_revive_state(cloned, pack, caps)

    stage_names = ("M4", "M5", "M6", "M7", "M8", "M9", "M10", "M11", "M12")
    stages = {name: StageTotals() for name in stage_names}
    counters: dict[str, int] = {}
    cycles: list[CycleForensic] = []
    m6_top_heap: list[tuple[float, int, OpportunityForensic]] = []
    m7_top_heap: list[tuple[float, int, OpportunityForensic]] = []

    tracker = PeakRssTracker()
    wall_start = time.perf_counter()
    cpu_start = time.process_time()

    for idx, now_micros in enumerate(cloned.cycle_times_micros):
        cycle_id = f"cyc_{idx:04d}"
        cycle_start = time.perf_counter()
        pre_m8 = {k: stages[k].seconds for k in stage_names}

        state.begin_cycle()
        clear_usage_cache()

        t0 = time.perf_counter()
        view = get_observable_state(state.bundle.world)
        from revive.benchmark.official.performance.cycle_cache import CycleViewCache

        cycle_cache = CycleViewCache(view, now_micros)
        world_by_natural_key = index_world_opportunities_by_natural_key(view)
        sentinel = detect(view, now_micros)
        m4 = time.perf_counter() - t0
        stages["M4"].add(m4)
        counters["m4_opportunities"] = counters.get("m4_opportunities", 0) + len(
            sentinel.opportunities
        )

        portfolio_items = []
        opp_data: dict[str, tuple] = {}
        m5_cycle = 0.0
        m6_cycle = 0.0
        m7_cycle = 0.0
        candidate_count = 0
        valuation_count = 0

        for opp in sentinel.opportunities:
            forensic, cand_set, val_result, m5_part = _profile_one_opportunity_forensic(
                opp=opp,
                view=view,
                now_micros=now_micros,
                cycle_id=cycle_id,
                state=state,
                cycle_cache=cycle_cache,
            )
            _push_top_opportunity(m6_top_heap, forensic, forensic.m6_seconds)
            _push_top_opportunity(m7_top_heap, forensic, forensic.m7_seconds)
            m5_cycle += m5_part
            m6_cycle += forensic.m6_seconds
            m7_cycle += forensic.m7_seconds
            candidate_count += forensic.candidates_total
            valuation_count += len(val_result.valuations)
            counters["m6_candidates"] = counters.get("m6_candidates", 0) + len(
                cand_set.candidates
            )
            counters["m6_feasibility_checks"] = counters.get(
                "m6_feasibility_checks", 0
            ) + forensic.action_codes_enumerated
            counters["m7_valuations"] = counters.get("m7_valuations", 0) + len(
                val_result.valuations
            )

            item = portfolio_item_from_valuation(
                opp.opportunity_id,
                opp.customer_id,
                opp.value_at_risk_paise,
                cand_set.candidates,
                val_result.valuations,
            )
            portfolio_items.append(item)
            opp_data[opp.opportunity_id] = (opp, cand_set, val_result)

        stages["M5"].add(m5_cycle)
        stages["M6"].add(m6_cycle)
        stages["M7"].add(m7_cycle)

        selected_count = 0
        auth_count = 0
        exec_count = 0
        meas_count = 0
        m8_cycle = 0.0
        m9_m12_cycle = 0.0

        if portfolio_items:
            t8 = time.perf_counter()
            allocation = allocate_portfolio(
                tuple(portfolio_items),
                state.resource_state,
                now_micros,
                cycle_id,
                policy=state.policy_pack,
            )
            m8_cycle = time.perf_counter() - t8
            stages["M8"].add(m8_cycle)
            counters["m8_allocations"] = counters.get("m8_allocations", 0) + 1
            selected_count = sum(
                1
                for a in allocation.assignments
                if a.outcome == DecisionOutcome.SELECTED
                and a.action_code != ActionCode.A00
            )

            capacities = state.resource_state.capacities
            item_map = {i.opportunity_id: i for i in portfolio_items}
            policy_rules = PolicyRules.from_policy_metadata(state.policy_pack.metadata)
            post_start = time.perf_counter()

            for assignment in allocation.assignments:
                if (
                    assignment.outcome != DecisionOutcome.SELECTED
                    or assignment.action_code == ActionCode.A00
                ):
                    continue
                item = item_map.get(assignment.opportunity_id)
                if item is None:
                    continue
                data = opp_data.get(assignment.opportunity_id)
                if data is None:
                    continue
                opp, cand_set, val_result = data
                cand = next(
                    (c for c in cand_set.candidates if c.candidate_id == assignment.candidate_id),
                    None,
                )
                val = next(
                    (v for v in val_result.valuations if v.candidate_id == assignment.candidate_id),
                    None,
                )
                if cand is None or val is None:
                    continue

                single_alloc = AllocationResult(
                    cycle_id=allocation.cycle_id,
                    produced_at_micros=allocation.produced_at_micros,
                    assignments=(assignment,),
                    allocator_mode=allocation.allocator_mode,
                    allocator_version=allocation.allocator_version,
                    policy_pack_version=allocation.policy_pack_version,
                    total_allocated_enrv_paise=assignment.enrv_paise,
                    shadow_prices=dict(allocation.shadow_prices),
                    shadow_price_method=allocation.shadow_price_method,
                    resource_usage=dict(allocation.resource_usage),
                    budget_usage_paise=allocation.budget_usage_paise,
                    constraint_summary=allocation.constraint_summary,
                    allocation_hash=allocation.allocation_hash,
                    duality_gap=allocation.duality_gap,
                    optimality_gap=allocation.optimality_gap,
                )
                cycle_ledger = ReservationLedger()
                bundle_out = seal_allocation(
                    single_alloc,
                    (item,),
                    capacities,
                    policy=state.policy_pack,
                    ledger=cycle_ledger,
                )
                counters["m9_decisions"] = counters.get("m9_decisions", 0) + len(
                    bundle_out.decisions
                )
                decision = next(
                    (d for d in bundle_out.decisions if d.outcome == DecisionOutcome.SELECTED),
                    None,
                )
                if decision is None:
                    continue
                world_opp_id = world_by_natural_key.get(opp.natural_key)
                if world_opp_id is None:
                    continue
                decision = replace(decision, opportunity_id=world_opp_id)
                world_opp = find_opportunity(state.bundle.world, world_opp_id)
                recovery_expires = (
                    world_opp.recovery_window_expires_at_micros
                    if world_opp
                    else now_micros + 10_000_000_000
                )
                auth_ctx = AuthorizeContext(
                    now_micros=now_micros,
                    opportunity_state=OpportunityState.AUTHORISED.value,
                    value_at_risk_paise=opp.value_at_risk_paise,
                    customer_id=opp.customer_id,
                    recovery_window_expires_at_micros=recovery_expires,
                    merchant_local_hour=12,
                    configuration_hash=decision.configuration_hash,
                    reconciliation_status="VALID",
                    policy_pack_hash=state.policy_pack.config_hash(),
                )
                auth_ctx = authorize_context_with_simulated_approval(
                    auth_ctx,
                    model_version=OFFICIAL_APPROVER_VERSION,
                    master_seed=state.bundle.seed,
                    decision=decision,
                    action=assignment.action_code,
                    rules=policy_rules,
                    enrv_paise=val.enrv_paise,
                    enrv_lo_paise=val.enrv_lo_paise,
                    enrv_hi_paise=val.enrv_hi_paise,
                )
                auth = authorize_execution(
                    decision,
                    cand,
                    val,
                    auth_ctx,
                    policy=state.policy_pack,
                    store=state.auth_store,
                )
                counters["m10_authorizations"] = counters.get("m10_authorizations", 0) + 1
                auth_count += 1
                state.authorizations.append(auth)
                if auth.authorization_state != AuthorizationState.AUTHORIZED:
                    continue
                env = ExecutionEnvironment(
                    oracle_partition=state.bundle.oracle_partition,
                    world=state.bundle.world,
                    contact_counts=dict(state.contact_counts),
                    value_at_risk_paise=opp.value_at_risk_paise,
                    customer_id=opp.customer_id,
                    opportunity_state=OpportunityState.AUTHORISED,
                    in_degradation_window=bool(opp.degradation_flag),
                )
                result = execute_authorization(
                    auth,
                    decision,
                    cand,
                    val,
                    env,
                    cycle_ledger,
                    now_micros + 1000,
                    store=state.exec_store,
                )
                counters["m11_executions"] = counters.get("m11_executions", 0) + 1
                exec_count += 1
                state.executions.append(result)
                state.contact_counts.update(env.contact_counts)
                measurement = measure_execution(
                    result,
                    val,
                    decision,
                    value_at_risk_paise=opp.value_at_risk_paise,
                    partition=state.bundle.oracle_partition,
                )
                counters["m12_measurements"] = counters.get("m12_measurements", 0) + 1
                meas_count += 1
                state.measurements.append(measurement)
                if result.action_code in {
                    ActionCode.A04,
                    ActionCode.A05,
                    ActionCode.A06,
                    ActionCode.A07,
                    ActionCode.A08,
                    ActionCode.A09,
                    ActionCode.A11,
                }:
                    increment_contact(state.bundle.world, world_opp_id)
                if measurement.gross_recovered_paise > 0:
                    mark_recovered(state.bundle.world, world_opp_id)

            m9_m12_cycle = time.perf_counter() - post_start
            for name in ("M9", "M10", "M11", "M12"):
                stages[name].add(m9_m12_cycle / 4.0)

        cycle_wall = time.perf_counter() - cycle_start
        cycles.append(
            CycleForensic(
                cycle_id=cycle_id,
                cycle_index=idx,
                wall_seconds=cycle_wall,
                m4_seconds=m4,
                m5_seconds=m5_cycle,
                m6_seconds=m6_cycle,
                m7_seconds=m7_cycle,
                m8_seconds=m8_cycle,
                m9_m12_seconds=m9_m12_cycle,
                opportunity_count=len(sentinel.opportunities),
                candidate_count=candidate_count,
                valuation_count=valuation_count,
                portfolio_size=len(portfolio_items),
                selected_count=selected_count,
                authorization_count=auth_count,
                execution_count=exec_count,
                measurement_count=meas_count,
            )
        )

        if progress_callback and (idx % progress_every == 0 or idx == len(cloned.cycle_times_micros) - 1):
            progress_callback(idx, len(cloned.cycle_times_micros), cycle_wall)
        if idx % 50 == 0:
            tracker.sample()

    wall = time.perf_counter() - wall_start
    cpu = time.process_time() - cpu_start
    tracker.sample()

    counters["intervention_count"] = compute_policy_metrics(
        BenchmarkPolicyId.REVIVE.value,
        cloned.seed,
        cloned.profile,
        tuple(state.measurements),
        tuple(state.executions),
        tuple(state.authorizations),
        incentive_budget_capacity_paise=caps.incentive_budget_paise,
        retry_capacity=caps.retry_slots,
        message_capacity=caps.message_capacity,
    ).intervention_count

    return CellForensicReport(
        seed=seed,
        profile=profile,
        wall_seconds=wall,
        cpu_seconds=cpu,
        peak_rss_bytes=tracker.peak,
        cycle_count=len(cloned.cycle_times_micros),
        stage_totals={k: stages[k].seconds for k in stage_names},
        counters=counters,
        cycles=cycles,
        top_m6_opportunities=_finalize_top_opportunities(m6_top_heap),
        top_m7_opportunities=_finalize_top_opportunities(m7_top_heap),
        capacities={
            "retry_slots": caps.retry_slots,
            "message_capacity": caps.message_capacity,
            "voice_minutes": caps.voice_minutes,
            "human_review_slots": caps.human_review_slots,
            "incentive_budget_paise": caps.incentive_budget_paise,
            "contact_allowance_per_customer": caps.contact_allowance_per_customer,
        },
    )


def slowest_cycles(report: CellForensicReport, limit: int = 10) -> list[dict[str, Any]]:
    ranked = sorted(report.cycles, key=lambda c: c.wall_seconds, reverse=True)
    return [c.to_dict() for c in ranked[:limit]]
