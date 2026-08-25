"""REVIVE full M4–M12 pipeline on a shared world — M13 §15."""

from __future__ import annotations

from dataclasses import dataclass, field

from dataclasses import replace

from revive.allocation import (
    allocate_portfolio,
    default_resource_state,
    portfolio_item_from_valuation,
    ResourceCapacities,
    ResourceState,
)
from revive.config.policy_pack import PolicyPack
from revive.decision.ledger import ReservationLedger
from revive.decision.seal import seal_allocation
from revive.domain.enums import ActionCode, DecisionOutcome, OpportunityState
from revive.execution import ExecutionEnvironment, ExecutionStore, execute_authorization
from revive.measurement import measure_execution
from revive.measurement.models import RecoveryMeasurement
from revive.policy import AuthorizeContext, authorize_execution
from revive.policy.models import AuthorizationState, ExecutionAuthorization
from revive.policy.store import AuthorizationStore
from revive.recovery.context.assemble import assemble_context
from revive.recovery.candidates.generate import generate_candidates
from revive.recovery.diagnosis.diagnose import diagnose
from revive.recovery.sentinel.detect import detect
from revive.recovery.valuation.price import price_candidates
from revive.execution.models import ExecutionResult

from revive.benchmark.official.performance.cycle_cache import CycleViewCache
from revive.benchmark.official.world import (
    increment_contact,
    mark_recovered,
    SharedWorldBundle,
    find_opportunity,
)
from revive.benchmark.official.freeze_constants import OFFICIAL_APPROVER_VERSION
from revive.policy.config import PolicyRules
from revive.policy.simulated_approver import authorize_context_with_simulated_approval
from revive.recovery.candidates.config import CandidateConfig, config_from_policy_pack
from revive.recovery.sentinel.identity_bridge import (
    index_world_opportunities_by_natural_key,
)
from revive.recovery.valuation.config import ValuationConfig, valuation_config_for_policy


@dataclass
class ReviveRunState:
    bundle: SharedWorldBundle
    policy_pack: PolicyPack
    resource_state: ResourceState
    ledger: ReservationLedger
    auth_store: AuthorizationStore
    exec_store: ExecutionStore
    measurements: list[RecoveryMeasurement] = field(default_factory=list)
    executions: list[ExecutionResult] = field(default_factory=list)
    authorizations: list[ExecutionAuthorization] = field(default_factory=list)
    contact_counts: dict[str, int] = field(default_factory=dict)
    policy_rules: PolicyRules | None = None
    candidate_config: CandidateConfig | None = None
    valuation_config: ValuationConfig | None = None

    def rules(self) -> PolicyRules:
        if self.policy_rules is None:
            self.policy_rules = PolicyRules.from_policy_metadata(self.policy_pack.metadata)
        return self.policy_rules

    def candidate_cfg(self) -> CandidateConfig:
        """Cell-scoped CandidateConfig — PolicyPack is immutable for the run."""
        if self.candidate_config is None:
            self.candidate_config = config_from_policy_pack(self.policy_pack.metadata)
        return self.candidate_config

    def valuation_cfg(self) -> ValuationConfig:
        """Cell-scoped ValuationConfig — PolicyPack is immutable for the run."""
        if self.valuation_config is None:
            self.valuation_config = valuation_config_for_policy(self.policy_pack)
        return self.valuation_config

    def begin_cycle(self) -> None:
        self.resource_state.retry_slots_used = 0
        self.resource_state.message_capacity_used = 0
        self.resource_state.voice_minutes_used = 0
        self.resource_state.human_review_slots_used = 0
        self.resource_state.incentive_budget_used_paise = 0


def run_revive_cycle(
    state: ReviveRunState,
    cycle_id: str,
    now_micros: int,
) -> None:
    """One complete REVIVE cycle: detect → measure."""
    from revive.simulation.observation import get_observable_state

    state.begin_cycle()
    view = get_observable_state(state.bundle.world)
    cycle_cache = CycleViewCache(view, now_micros)
    world_by_natural_key = index_world_opportunities_by_natural_key(view)
    sentinel = detect(view, now_micros)

    portfolio_items = []
    opp_data: dict[str, tuple] = {}

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
        opp_data[opp.opportunity_id] = (opp, cand_set, val_result)

    if not portfolio_items:
        return

    allocation = allocate_portfolio(
        tuple(portfolio_items),
        state.resource_state,
        now_micros,
        cycle_id,
        policy=state.policy_pack,
    )

    capacities = state.resource_state.capacities
    item_map = {i.opportunity_id: i for i in portfolio_items}
    policy_rules = state.rules()

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

        from revive.allocation.models import AllocationResult

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
        state.executions.append(result)
        state.contact_counts.update(env.contact_counts)

        measurement = measure_execution(
            result,
            val,
            decision,
            value_at_risk_paise=opp.value_at_risk_paise,
            partition=state.bundle.oracle_partition,
        )
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


def new_revive_state(
    bundle: SharedWorldBundle,
    policy_pack: PolicyPack,
    capacities: ResourceCapacities | None = None,
) -> ReviveRunState:
    caps = capacities or ResourceCapacities()
    return ReviveRunState(
        bundle=bundle,
        policy_pack=policy_pack,
        resource_state=default_resource_state(caps),
        ledger=ReservationLedger(),
        auth_store=AuthorizationStore(),
        exec_store=ExecutionStore(),
    )
