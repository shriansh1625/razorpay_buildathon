"""Instrumented REVIVE cell profiling — M13.14 development only."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, replace
from typing import Any

from revive.allocation import allocate_portfolio, portfolio_item_from_valuation
from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.benchmark.official.cells.store import metrics_checksum
from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.benchmark.official.metrics import compute_policy_metrics
from revive.benchmark.official.performance.cycle_cache import CycleViewCache
from revive.benchmark.official.policies import BenchmarkPolicyId
from revive.benchmark.official.revive_pipeline import ReviveRunState, new_revive_state
from revive.benchmark.official.world import clone_shared_world, generate_shared_world
from revive.config.policy_pack import official_sealed_policy_pack
from revive.decision.seal import seal_allocation
from revive.domain.enums import ActionCode, DecisionOutcome, OpportunityState
from revive.execution import ExecutionEnvironment, execute_authorization
from revive.measurement import measure_execution
from revive.policy import AuthorizeContext, authorize_execution
from revive.policy.config import PolicyRules
from revive.policy.models import AuthorizationState
from revive.policy.simulated_approver import authorize_context_with_simulated_approval
from revive.benchmark.official.freeze_constants import OFFICIAL_APPROVER_VERSION
from revive.recovery.sentinel.identity_bridge import index_world_opportunities_by_natural_key
from revive.recovery.context.assemble import assemble_context
from revive.recovery.candidates.generate import generate_candidates
from revive.recovery.diagnosis.diagnose import diagnose
from revive.recovery.sentinel.detect import detect
from revive.recovery.valuation.price import price_candidates
from revive.simulation.observation import get_observable_state
from revive.simulation.types import GenerationProfile

from revive.benchmark.official.world import find_opportunity, increment_contact, mark_recovered
from revive.decision.ledger import ReservationLedger
from revive.allocation.models import AllocationResult


@dataclass
class StageTotals:
    seconds: float = 0.0
    count: int = 0

    def add(self, elapsed: float, n: int = 1) -> None:
        self.seconds += elapsed
        self.count += n


@dataclass
class CellStageProfile:
    seed: int
    profile: str
    total_seconds: float
    cycle_count: int
    stages: dict[str, StageTotals]
    counters: dict[str, int] = field(default_factory=dict)
    peak_rss_bytes: int | None = None

    def stage_share(self, name: str) -> float:
        total = self.total_seconds or 1.0
        return self.stages[name].seconds / total

    def classify(self, name: str) -> str:
        share = self.stage_share(name) * 100
        if share < 10:
            return "GREEN"
        if share <= 25:
            return "YELLOW"
        return "RED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "profile": self.profile,
            "total_seconds": self.total_seconds,
            "cycle_count": self.cycle_count,
            "stages": {
                k: {"seconds": v.seconds, "count": v.count, "share_pct": self.stage_share(k) * 100}
                for k, v in self.stages.items()
            },
            "hotspots": {k: self.classify(k) for k in self.stages},
            "counters": self.counters,
            "peak_rss_bytes": self.peak_rss_bytes,
        }


def _fingerprint_metrics(metrics) -> str:
    return metrics_checksum(metrics.to_dict())


def profile_revive_cycle_instrumented(
    state: ReviveRunState,
    cycle_id: str,
    now_micros: int,
    stages: dict[str, StageTotals],
    counters: dict[str, int],
    *,
    use_cycle_cache: bool = True,
) -> None:
    """One REVIVE cycle with per-stage timing (mirrors revive_pipeline semantics)."""
    from revive.allocation.resources import clear_usage_cache

    state.begin_cycle()
    clear_usage_cache()

    t0 = time.perf_counter()
    view = get_observable_state(state.bundle.world)
    cycle_cache = CycleViewCache(view, now_micros) if use_cycle_cache else None
    world_by_natural_key = index_world_opportunities_by_natural_key(view)
    sentinel = detect(view, now_micros)
    stages["M4"].add(time.perf_counter() - t0)
    counters["m4_opportunities"] = counters.get("m4_opportunities", 0) + len(sentinel.opportunities)

    portfolio_items = []
    opp_data: dict[str, tuple] = {}
    m5 = StageTotals()
    m6 = StageTotals()
    m7 = StageTotals()

    for opp in sentinel.opportunities:
        t = time.perf_counter()
        ctx = assemble_context(
            opp, view, now_micros, cycle_cache=cycle_cache if use_cycle_cache else None
        )
        m5.add(time.perf_counter() - t)

        t = time.perf_counter()
        dx = diagnose(opp, ctx, view, now_micros, cycle_id)
        m5.add(time.perf_counter() - t)

        t = time.perf_counter()
        cand_set = generate_candidates(
            opp,
            dx.observable_context,
            dx,
            now_micros,
            cycle_id,
            policy=state.policy_pack,
            config=state.candidate_cfg(),
        )
        m6.add(time.perf_counter() - t)
        counters["m6_candidates"] = counters.get("m6_candidates", 0) + len(cand_set.candidates)

        t = time.perf_counter()
        val_result = price_candidates(
            opp,
            dx.observable_context,
            dx,
            cand_set,
            now_micros,
            policy=state.policy_pack,
            config=state.valuation_cfg(),
        )
        m7.add(time.perf_counter() - t)
        counters["m7_valuations"] = counters.get("m7_valuations", 0) + len(val_result.valuations)

        item = portfolio_item_from_valuation(
            opp.opportunity_id,
            opp.customer_id,
            opp.value_at_risk_paise,
            cand_set.candidates,
            val_result.valuations,
        )
        portfolio_items.append(item)
        opp_data[opp.opportunity_id] = (opp, cand_set, val_result)

    stages["M5"].seconds += m5.seconds
    stages["M5"].count += m5.count or len(sentinel.opportunities)
    stages["M6"].seconds += m6.seconds
    stages["M6"].count += m6.count or len(sentinel.opportunities)
    stages["M7"].seconds += m7.seconds
    stages["M7"].count += m7.count or len(sentinel.opportunities)

    if not portfolio_items:
        return

    t = time.perf_counter()
    allocation = allocate_portfolio(
        tuple(portfolio_items),
        state.resource_state,
        now_micros,
        cycle_id,
        policy=state.policy_pack,
    )
    stages["M8"].add(time.perf_counter() - t)
    counters["m8_allocations"] = counters.get("m8_allocations", 0) + 1

    capacities = state.resource_state.capacities
    item_map = {i.opportunity_id: i for i in portfolio_items}
    policy_rules = state.rules() if hasattr(state, "rules") else PolicyRules.from_policy_metadata(state.policy_pack.metadata)
    m9 = StageTotals()
    m10 = StageTotals()
    m11 = StageTotals()
    m12 = StageTotals()

    for assignment in allocation.assignments:
        if assignment.outcome != DecisionOutcome.SELECTED or assignment.action_code == ActionCode.A00:
            continue
        item = item_map.get(assignment.opportunity_id)
        if item is None:
            continue
        data = opp_data.get(assignment.opportunity_id)
        if data is None:
            continue
        opp, cand_set, val_result = data
        cand = next((c for c in cand_set.candidates if c.candidate_id == assignment.candidate_id), None)
        val = next((v for v in val_result.valuations if v.candidate_id == assignment.candidate_id), None)
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

        t = time.perf_counter()
        cycle_ledger = ReservationLedger()
        bundle = seal_allocation(
            single_alloc,
            (item,),
            capacities,
            policy=state.policy_pack,
            ledger=cycle_ledger,
        )
        m9.add(time.perf_counter() - t)
        counters["m9_decisions"] = counters.get("m9_decisions", 0) + len(bundle.decisions)

        decision = next((d for d in bundle.decisions if d.outcome == DecisionOutcome.SELECTED), None)
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

        t = time.perf_counter()
        auth = authorize_execution(
            decision,
            cand,
            val,
            auth_ctx,
            policy=state.policy_pack,
            store=state.auth_store,
        )
        m10.add(time.perf_counter() - t)
        counters["m10_authorizations"] = counters.get("m10_authorizations", 0) + 1
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

        t = time.perf_counter()
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
        m11.add(time.perf_counter() - t)
        counters["m11_executions"] = counters.get("m11_executions", 0) + 1
        state.executions.append(result)
        state.contact_counts.update(env.contact_counts)

        t = time.perf_counter()
        measurement = measure_execution(
            result,
            val,
            decision,
            value_at_risk_paise=opp.value_at_risk_paise,
            partition=state.bundle.oracle_partition,
        )
        m12.add(time.perf_counter() - t)
        counters["m12_measurements"] = counters.get("m12_measurements", 0) + 1
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

    for name, bucket in (("M9", m9), ("M10", m10), ("M11", m11), ("M12", m12)):
        stages[name].seconds += bucket.seconds
        stages[name].count += bucket.count


def profile_revive_cell(
    seed: int = 2,
    profile: str = "BALANCED",
    *,
    use_cycle_cache: bool = True,
) -> tuple[CellStageProfile, dict[str, Any]]:
    """Profile full official-scale REVIVE cell with stage breakdown."""
    from revive.benchmark.official.cells.telemetry import PeakRssTracker

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

    tracker = PeakRssTracker()
    t0 = time.perf_counter()
    for idx, now_micros in enumerate(cloned.cycle_times_micros):
        profile_revive_cycle_instrumented(
            state,
            f"cyc_{idx:04d}",
            now_micros,
            stages,
            counters,
            use_cycle_cache=use_cycle_cache,
        )
        if idx % 50 == 0:
            tracker.sample()
    total = time.perf_counter() - t0
    tracker.sample()

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
    cell_hash = _fingerprint_metrics(metrics)

    result = CellStageProfile(
        seed=seed,
        profile=profile,
        total_seconds=total,
        cycle_count=len(cloned.cycle_times_micros),
        stages=stages,
        counters=counters,
        peak_rss_bytes=tracker.peak,
    )
    return result, {"cell_result_hash": cell_hash, "metrics": metrics.to_dict()}
