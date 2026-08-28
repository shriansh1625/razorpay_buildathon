"""Traced recovery cycle — product path only.

Calls the same engine primitives as `run_revive_cycle` and keeps every
intermediate. Does not import or monkeypatch the official benchmark runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from revive.allocation import (
    allocate_portfolio,
    default_resource_state,
    portfolio_item_from_valuation,
    ResourceCapacities,
    ResourceState,
)
from revive.allocation.models import AllocationAssignment, AllocationResult
from revive.benchmark.official.freeze_constants import OFFICIAL_APPROVER_VERSION
from revive.benchmark.official.performance.cycle_cache import CycleViewCache
from revive.benchmark.official.world import (
    SharedWorldBundle,
    find_opportunity,
    increment_contact,
    mark_recovered,
)
from revive.config.policy_pack import PolicyPack
from revive.decision.ledger import ReservationLedger
from revive.decision.models import AllocationDecision
from revive.decision.seal import seal_allocation
from revive.domain.enums import ActionCode, DecisionOutcome, OpportunityState
from revive.execution import ExecutionEnvironment, ExecutionStore, execute_authorization
from revive.execution.models import ExecutionResult, ExecutionStage
from revive.measurement import measure_execution
from revive.measurement.models import RecoveryMeasurement
from revive.policy import AuthorizeContext, authorize_execution
from revive.policy.config import PolicyRules
from revive.policy.models import AuthorizationState, ExecutionAuthorization
from revive.policy.simulated_approver import authorize_context_with_simulated_approval
from revive.policy.store import AuthorizationStore
from revive.recovery.candidates.generate import generate_candidates
from revive.recovery.candidates.models import RecoveryCandidate
from revive.recovery.context.assemble import assemble_context
from revive.recovery.diagnosis.diagnose import diagnose
from revive.recovery.diagnosis.models import Diagnosis
from revive.recovery.sentinel.detect import detect
from revive.recovery.sentinel.identity_bridge import index_world_opportunities_by_natural_key
from revive.recovery.sentinel.models import DetectedOpportunity
from revive.recovery.valuation.models import CandidateValuation
from revive.recovery.valuation.price import price_candidates
from revive.recovery.candidates.config import CandidateConfig, config_from_policy_pack
from revive.recovery.valuation.config import ValuationConfig, valuation_config_for_policy
from revive.simulation.observation import get_observable_state

# Actions that consume a customer contact allowance when they reach the adapter.
_CONTACT_ACTIONS = frozenset(
    {
        ActionCode.A04,
        ActionCode.A05,
        ActionCode.A06,
        ActionCode.A07,
        ActionCode.A08,
        ActionCode.A09,
        ActionCode.A11,
    }
)


@dataclass
class OpportunityTrace:
    """One opportunity through one cycle — all engine artefacts retained."""

    cycle_id: str
    now_micros: int
    opportunity: DetectedOpportunity
    diagnosis: Diagnosis
    candidates: tuple[RecoveryCandidate, ...]
    valuations: tuple[CandidateValuation, ...]
    p_natural: float
    assignment: AllocationAssignment | None
    decision: AllocationDecision | None
    authorization: ExecutionAuthorization | None
    execution: ExecutionResult | None
    measurement: RecoveryMeasurement | None
    allocator_mode: str
    allocator_version: str
    shadow_prices: dict[str, float]
    constraint_summary: tuple[str, ...]
    allocation_hash: str


@dataclass
class PendingScheduledExecution:
    """A delayed action (A02 retry) awaiting its scheduled virtual time.

    The engine returns an ExecutionStage.SCHEDULED result when an action is not
    yet due. Completing it requires re-invoking `execute_authorization` with the
    *same* reservation ledger once `now_micros >= scheduled_at_micros`. Holding
    the inputs here lets the product path settle those retries instead of
    leaving them permanently unobservable.
    """

    scheduled_at_micros: int
    trace: "OpportunityTrace"
    opportunity: DetectedOpportunity
    candidate: RecoveryCandidate
    valuation: CandidateValuation
    decision: AllocationDecision
    authorization: ExecutionAuthorization
    ledger: ReservationLedger
    world_opportunity_id: str


@dataclass
class CycleTrace:
    cycle_id: str
    now_micros: int
    allocator_mode: str
    allocator_version: str
    allocation_hash: str
    total_allocated_enrv_paise: int
    shadow_prices: dict[str, float]
    resource_usage: dict[str, int]
    constraint_summary: tuple[str, ...]
    opportunities: tuple[OpportunityTrace, ...]
    detected_count: int
    diagnosed_count: int
    optimized_count: int
    guarded_count: int
    authorized_count: int
    blocked_count: int
    executed_count: int
    measured_count: int


@dataclass
class ProductRunState:
    bundle: SharedWorldBundle
    policy_pack: PolicyPack
    resource_state: ResourceState
    ledger: ReservationLedger
    auth_store: AuthorizationStore
    exec_store: ExecutionStore
    cycles: list[CycleTrace] = field(default_factory=list)
    policy_rules: PolicyRules | None = None
    candidate_config: CandidateConfig | None = None
    valuation_config: ValuationConfig | None = None
    contact_counts: dict[str, int] = field(default_factory=dict)
    pending_scheduled: list[PendingScheduledExecution] = field(default_factory=list)
    settled_count: int = 0
    fixture_label: str = "Demonstration fixture — synthetic. Not official benchmark evidence."

    def rules(self) -> PolicyRules:
        if self.policy_rules is None:
            self.policy_rules = PolicyRules.from_policy_metadata(self.policy_pack.metadata)
        return self.policy_rules

    def candidate_cfg(self) -> CandidateConfig:
        if self.candidate_config is None:
            self.candidate_config = config_from_policy_pack(self.policy_pack.metadata)
        return self.candidate_config

    def valuation_cfg(self) -> ValuationConfig:
        if self.valuation_config is None:
            self.valuation_config = valuation_config_for_policy(self.policy_pack)
        return self.valuation_config

    def begin_cycle(self) -> None:
        self.resource_state.retry_slots_used = 0
        self.resource_state.message_capacity_used = 0
        self.resource_state.voice_minutes_used = 0
        self.resource_state.human_review_slots_used = 0
        self.resource_state.incentive_budget_used_paise = 0


def new_product_state(
    bundle: SharedWorldBundle,
    policy_pack: PolicyPack,
    capacities: ResourceCapacities | None = None,
    *,
    fixture_label: str | None = None,
) -> ProductRunState:
    caps = capacities or ResourceCapacities()
    state = ProductRunState(
        bundle=bundle,
        policy_pack=policy_pack,
        resource_state=default_resource_state(caps),
        ledger=ReservationLedger(),
        auth_store=AuthorizationStore(),
        exec_store=ExecutionStore(),
    )
    if fixture_label is not None:
        state.fixture_label = fixture_label
    return state


def settle_scheduled_executions(state: ProductRunState, now_micros: int) -> int:
    """Complete delayed actions whose scheduled virtual time has arrived.

    Uses the same engine primitives as the in-cycle path: re-invokes
    `execute_authorization` with the retained reservation ledger, then
    re-measures. Mutates the originating OpportunityTrace in place so receipts,
    graphs and the audit ledger reflect the settled outcome instead of a
    permanently `SCHEDULED` intervention. Returns the number settled.
    """
    if not state.pending_scheduled:
        return 0

    due = [p for p in state.pending_scheduled if p.scheduled_at_micros <= now_micros]
    if not due:
        return 0
    state.pending_scheduled = [
        p for p in state.pending_scheduled if p.scheduled_at_micros > now_micros
    ]

    settled = 0
    for pend in due:
        opp = pend.opportunity
        env = ExecutionEnvironment(
            oracle_partition=state.bundle.oracle_partition,
            world=state.bundle.world,
            contact_counts=dict(state.contact_counts),
            value_at_risk_paise=opp.value_at_risk_paise,
            customer_id=opp.customer_id,
            opportunity_state=OpportunityState.AUTHORISED,
            in_degradation_window=bool(opp.degradation_flag),
        )
        execution = execute_authorization(
            pend.authorization,
            pend.decision,
            pend.candidate,
            pend.valuation,
            env,
            pend.ledger,
            now_micros,
            store=state.exec_store,
        )
        if execution.execution_stage == ExecutionStage.SCHEDULED:
            # Still not due according to the engine — keep waiting.
            state.pending_scheduled.append(pend)
            continue

        state.contact_counts.update(env.contact_counts)
        measurement = measure_execution(
            execution,
            pend.valuation,
            pend.decision,
            value_at_risk_paise=opp.value_at_risk_paise,
            partition=state.bundle.oracle_partition,
        )
        pend.trace.execution = execution
        pend.trace.measurement = measurement
        settled += 1

        if execution.action_code in _CONTACT_ACTIONS:
            increment_contact(state.bundle.world, pend.world_opportunity_id)
        if measurement.gross_recovered_paise > 0:
            mark_recovered(state.bundle.world, pend.world_opportunity_id)

    state.settled_count += settled
    return settled


def run_traced_cycle(
    state: ProductRunState,
    cycle_id: str,
    now_micros: int,
) -> CycleTrace:
    """Detect → measure, retaining graph / counterfactual / receipt inputs."""
    state.begin_cycle()
    # Delayed retries authorized in earlier cycles may now be due.
    settle_scheduled_executions(state, now_micros)
    view = get_observable_state(state.bundle.world)
    cycle_cache = CycleViewCache(view, now_micros)
    world_by_natural_key = index_world_opportunities_by_natural_key(view)
    sentinel = detect(view, now_micros)

    portfolio_items = []
    built: dict[str, dict[str, Any]] = {}

    for opp in sentinel.opportunities:
        ctx = assemble_context(opp, view, now_micros, cycle_cache=cycle_cache)
        dx = diagnose(opp, ctx, view, now_micros, cycle_id)
        cand_set = generate_candidates(
            opp,
            dx.observable_context,
            dx,
            now_micros,
            cycle_id,
            policy=state.policy_pack,
            config=state.candidate_cfg(),
        )
        val_result = price_candidates(
            opp,
            dx.observable_context,
            dx,
            cand_set,
            now_micros,
            policy=state.policy_pack,
            config=state.valuation_cfg(),
        )
        item = portfolio_item_from_valuation(
            opp.opportunity_id,
            opp.customer_id,
            opp.value_at_risk_paise,
            cand_set.candidates,
            val_result.valuations,
        )
        portfolio_items.append(item)
        built[opp.opportunity_id] = {
            "opp": opp,
            "diagnosis": dx,
            "candidates": cand_set.candidates,
            "valuations": val_result.valuations,
            "p_natural": val_result.p_natural,
        }

    if not portfolio_items:
        empty = CycleTrace(
            cycle_id=cycle_id,
            now_micros=now_micros,
            allocator_mode="",
            allocator_version="",
            allocation_hash="",
            total_allocated_enrv_paise=0,
            shadow_prices={},
            resource_usage={},
            constraint_summary=(),
            opportunities=(),
            detected_count=0,
            diagnosed_count=0,
            optimized_count=0,
            guarded_count=0,
            authorized_count=0,
            blocked_count=0,
            executed_count=0,
            measured_count=0,
        )
        state.cycles.append(empty)
        return empty

    allocation = allocate_portfolio(
        tuple(portfolio_items),
        state.resource_state,
        now_micros,
        cycle_id,
        policy=state.policy_pack,
    )
    assignment_by_opp = {a.opportunity_id: a for a in allocation.assignments}
    item_map = {i.opportunity_id: i for i in portfolio_items}
    policy_rules = state.rules()
    capacities = state.resource_state.capacities

    traces: list[OpportunityTrace] = []
    authorized_count = 0
    blocked_count = 0
    executed_count = 0
    measured_count = 0
    guarded_count = 0

    for opp_id, payload in built.items():
        opp: DetectedOpportunity = payload["opp"]
        assignment = assignment_by_opp.get(opp_id)
        decision = None
        authorization = None
        execution = None
        measurement = None
        pending_settlement: dict[str, Any] | None = None

        if (
            assignment is not None
            and assignment.outcome == DecisionOutcome.SELECTED
            and assignment.action_code != ActionCode.A00
        ):
            item = item_map[opp_id]
            cand = next(
                (c for c in payload["candidates"] if c.candidate_id == assignment.candidate_id),
                None,
            )
            val = next(
                (v for v in payload["valuations"] if v.candidate_id == assignment.candidate_id),
                None,
            )
            if cand is not None and val is not None:
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
                bundle = seal_allocation(
                    single_alloc,
                    (item,),
                    capacities,
                    policy=state.policy_pack,
                    ledger=cycle_ledger,
                )
                decision = next(
                    (d for d in bundle.decisions if d.outcome == DecisionOutcome.SELECTED),
                    None,
                )
                if decision is not None:
                    world_opp_id = world_by_natural_key.get(opp.natural_key)
                    if world_opp_id is not None:
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
                        authorization = authorize_execution(
                            decision,
                            cand,
                            val,
                            auth_ctx,
                            policy=state.policy_pack,
                            store=state.auth_store,
                        )
                        guarded_count += 1
                        if authorization.authorization_state == AuthorizationState.AUTHORIZED:
                            authorized_count += 1
                            env = ExecutionEnvironment(
                                oracle_partition=state.bundle.oracle_partition,
                                world=state.bundle.world,
                                contact_counts=dict(state.contact_counts),
                                value_at_risk_paise=opp.value_at_risk_paise,
                                customer_id=opp.customer_id,
                                opportunity_state=OpportunityState.AUTHORISED,
                                in_degradation_window=bool(opp.degradation_flag),
                            )
                            execution = execute_authorization(
                                authorization,
                                decision,
                                cand,
                                val,
                                env,
                                cycle_ledger,
                                now_micros + 1000,
                                store=state.exec_store,
                            )
                            executed_count += 1
                            state.contact_counts.update(env.contact_counts)
                            measurement = measure_execution(
                                execution,
                                val,
                                decision,
                                value_at_risk_paise=opp.value_at_risk_paise,
                                partition=state.bundle.oracle_partition,
                            )
                            if execution.execution_stage == ExecutionStage.SCHEDULED:
                                # Not due yet: record the provisional measurement
                                # and settle it once virtual time reaches the
                                # scheduled instant (see settle_scheduled_executions).
                                pending_settlement = {
                                    "scheduled_at_micros": execution.scheduled_at_micros
                                    or now_micros,
                                    "opportunity": opp,
                                    "candidate": cand,
                                    "valuation": val,
                                    "decision": decision,
                                    "authorization": authorization,
                                    "ledger": cycle_ledger,
                                    "world_opportunity_id": world_opp_id,
                                }
                            else:
                                measured_count += 1
                                if execution.action_code in _CONTACT_ACTIONS:
                                    increment_contact(state.bundle.world, world_opp_id)
                                if measurement.gross_recovered_paise > 0:
                                    mark_recovered(state.bundle.world, world_opp_id)
                        else:
                            blocked_count += 1

        trace = OpportunityTrace(
            cycle_id=cycle_id,
            now_micros=now_micros,
            opportunity=opp,
            diagnosis=payload["diagnosis"],
            candidates=payload["candidates"],
            valuations=payload["valuations"],
            p_natural=payload["p_natural"],
            assignment=assignment,
            decision=decision,
            authorization=authorization,
            execution=execution,
            measurement=measurement,
            allocator_mode=allocation.allocator_mode.value,
            allocator_version=allocation.allocator_version,
            shadow_prices=dict(allocation.shadow_prices),
            constraint_summary=allocation.constraint_summary,
            allocation_hash=allocation.allocation_hash,
        )
        traces.append(trace)
        if pending_settlement is not None:
            state.pending_scheduled.append(
                PendingScheduledExecution(trace=trace, **pending_settlement)
            )

    cycle = CycleTrace(
        cycle_id=cycle_id,
        now_micros=now_micros,
        allocator_mode=allocation.allocator_mode.value,
        allocator_version=allocation.allocator_version,
        allocation_hash=allocation.allocation_hash,
        total_allocated_enrv_paise=allocation.total_allocated_enrv_paise,
        shadow_prices=dict(allocation.shadow_prices),
        resource_usage=dict(allocation.resource_usage),
        constraint_summary=allocation.constraint_summary,
        opportunities=tuple(traces),
        detected_count=len(traces),
        diagnosed_count=len(traces),
        optimized_count=len(traces),
        guarded_count=guarded_count,
        authorized_count=authorized_count,
        blocked_count=blocked_count,
        executed_count=executed_count,
        measured_count=measured_count,
    )
    state.cycles.append(cycle)
    return cycle
