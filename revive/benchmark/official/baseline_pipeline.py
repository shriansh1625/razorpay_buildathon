"""Baseline policies through shared execution engine — M13 §14."""

from __future__ import annotations

from dataclasses import dataclass, field

from revive.benchmark.config import BaselineEnvironmentConfig
from revive.benchmark.capacities import baseline_environment_for_profile, profile_from_string
from revive.benchmark.runner import run_baseline_cycle
from revive.benchmark.types import BaselineCycleContext, BaselinePolicyId
from revive.config.policy_pack import PolicyPack
from revive.decision.ledger import ReservationLedger
from revive.decision.models import AllocationDecision, AllocationSnapshot, DecisionLifecycleStatus
from revive.domain.enums import ActionCode, DecisionOutcome, OpportunityState
from revive.execution import ExecutionEnvironment, ExecutionStore, execute_authorization
from revive.measurement import measure_execution
from revive.measurement.models import RecoveryMeasurement
from revive.policy import AuthorizeContext, authorize_execution
from revive.policy.models import AuthorizationState, ExecutionAuthorization
from revive.policy.store import AuthorizationStore
from revive.recovery.candidates.generate import generate_candidates
from revive.recovery.context.assemble import assemble_context
from revive.recovery.diagnosis.diagnose import diagnose
from revive.recovery.sentinel.detect import detect
from revive.recovery.valuation.price import price_candidates
from revive.execution.models import ExecutionResult

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
    index_sentinel_by_natural_key,
    resolve_sentinel_for_world_opportunity_id,
)
from revive.recovery.valuation.config import ValuationConfig, valuation_config_for_policy


@dataclass
class BaselineRunState:
    bundle: SharedWorldBundle
    policy_id: BaselinePolicyId
    policy_pack: PolicyPack
    baseline_env: BaselineEnvironmentConfig
    baseline_context: BaselineCycleContext | None = None
    ledger: ReservationLedger = field(default_factory=ReservationLedger)
    auth_store: AuthorizationStore = field(default_factory=AuthorizationStore)
    exec_store: ExecutionStore = field(default_factory=ExecutionStore)
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
        if self.candidate_config is None:
            self.candidate_config = config_from_policy_pack(self.policy_pack.metadata)
        return self.candidate_config

    def valuation_cfg(self) -> ValuationConfig:
        if self.valuation_config is None:
            self.valuation_config = valuation_config_for_policy(self.policy_pack)
        return self.valuation_config


def run_baseline_cycle_full(
    state: BaselineRunState,
    cycle_id: str,
    now_micros: int,
) -> None:
    """Baseline decisions → authorize → execute → measure."""
    from revive.simulation.observation import get_observable_state

    view = get_observable_state(state.bundle.world)

    if state.baseline_context is None:
        state.baseline_context = BaselineCycleContext(
            cycle_id=cycle_id,
            now_micros=now_micros,
            epsilon_paise=state.policy_pack.epsilon_paise,
            contact_allowance_per_customer=state.baseline_env.contact_allowance_per_customer,
            retry_slots_per_cycle=state.baseline_env.retry_slots_per_cycle,
            message_capacity_per_cycle=state.baseline_env.message_capacity_per_cycle,
        )
    else:
        state.baseline_context.cycle_id = cycle_id
        state.baseline_context.now_micros = now_micros
        state.baseline_context.retry_slots_used = 0
        state.baseline_context.message_capacity_used = 0

    cycle_result = run_baseline_cycle(
        state.policy_id,
        view,
        cycle_id=cycle_id,
        now_micros=now_micros,
        policy_pack=state.policy_pack,
        env=state.baseline_env,
        persist_context=state.baseline_context,
    )

    sentinel = detect(view, now_micros)
    sentinel_index = index_sentinel_by_natural_key(sentinel)
    policy_rules = state.rules()

    config_hash = f"baseline_{state.policy_id.value}"

    for bd in cycle_result.decisions:
        if bd.outcome != DecisionOutcome.SELECTED or bd.action_code == ActionCode.A00:
            continue

        detected = resolve_sentinel_for_world_opportunity_id(
            bd.opportunity_id,
            view,
            sentinel_index,
        )
        if detected is None:
            continue

        ctx = assemble_context(detected, view, now_micros)
        dx = diagnose(detected, ctx, view, now_micros, cycle_id)
        cand_set = generate_candidates(
            detected,
            dx.observable_context,
            dx,
            now_micros,
            cycle_id,
            policy=state.policy_pack,
            config=state.candidate_cfg(),
        )
        val_result = price_candidates(
            detected,
            dx.observable_context,
            dx,
            cand_set,
            now_micros,
            policy=state.policy_pack,
            config=state.valuation_cfg(),
        )

        cand = next(
            (c for c in cand_set.candidates if c.action_code == bd.action_code),
            None,
        )
        if cand is None:
            continue
        val = next(
            (v for v in val_result.valuations if v.candidate_id == cand.candidate_id),
            None,
        )
        if val is None:
            continue

        decision = AllocationDecision(
            decision_id=f"dec_baseline_{bd.policy_id.value}_{bd.opportunity_id}_{bd.cycle_id}",
            cycle_id=bd.cycle_id,
            opportunity_id=bd.opportunity_id,
            customer_id=detected.customer_id,
            outcome=bd.outcome,
            action_code=bd.action_code,
            candidate_id=cand.candidate_id,
            enrv_paise=val.enrv_paise,
            reason_code=bd.reason_code,
            idempotency_key=f"idem_{bd.opportunity_id}_{bd.action_code.value}_{bd.cycle_id}",
            created_at_micros=bd.decision_at_micros,
            expires_at_micros=bd.decision_at_micros + 999_999_999,
            allocator_version="baseline",
            allocator_mode="BASELINE",
            policy_pack_version=state.policy_pack.version,
            policy_pack_status=state.policy_pack.status,
            configuration_hash=config_hash,
            strategy_version=val.strategy_version,
            valuation_version=val.valuation_version,
            allocation_hash="baseline",
            snapshot=AllocationSnapshot(
                opportunity_id=detected.opportunity_id,
                customer_id=detected.customer_id,
                value_at_risk_paise=detected.value_at_risk_paise,
                candidate_ids=(cand.candidate_id,),
                valuation_ids=(val.valuation_id,),
                valuation_version=val.valuation_version,
                strategy_version=val.strategy_version,
                resource_capacities_digest="baseline",
                simulation_time_micros=now_micros,
                opportunity_state="AUTHORISED",
            ),
            lifecycle_status=DecisionLifecycleStatus.RESERVED,
        )

        world_opp = find_opportunity(state.bundle.world, bd.opportunity_id)
        recovery_expires = (
            world_opp.recovery_window_expires_at_micros
            if world_opp
            else now_micros + 10_000_000_000
        )

        auth_ctx = AuthorizeContext(
            now_micros=now_micros,
            opportunity_state=OpportunityState.AUTHORISED.value,
            value_at_risk_paise=detected.value_at_risk_paise,
            customer_id=detected.customer_id,
            recovery_window_expires_at_micros=recovery_expires,
            merchant_local_hour=12,
            configuration_hash=config_hash,
            reconciliation_status="VALID",
            policy_pack_hash=state.policy_pack.config_hash(),
        )
        auth_ctx = authorize_context_with_simulated_approval(
            auth_ctx,
            model_version=OFFICIAL_APPROVER_VERSION,
            master_seed=state.bundle.seed,
            decision=decision,
            action=bd.action_code,
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
            value_at_risk_paise=detected.value_at_risk_paise,
            customer_id=detected.customer_id,
            opportunity_state=OpportunityState.AUTHORISED,
            in_degradation_window=bool(detected.degradation_flag),
        )

        result = execute_authorization(
            auth,
            decision,
            cand,
            val,
            env,
            state.ledger,
            now_micros + 1000,
            store=state.exec_store,
        )
        state.executions.append(result)
        state.contact_counts.update(env.contact_counts)

        measurement = measure_execution(
            result,
            val,
            decision,
            value_at_risk_paise=detected.value_at_risk_paise,
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
            increment_contact(state.bundle.world, bd.opportunity_id)

        if measurement.gross_recovered_paise > 0:
            mark_recovered(state.bundle.world, bd.opportunity_id)


def new_baseline_state(
    bundle: SharedWorldBundle,
    policy_id: BaselinePolicyId,
    policy_pack: PolicyPack,
    baseline_env: BaselineEnvironmentConfig | None = None,
) -> BaselineRunState:
    profile = profile_from_string(bundle.profile)
    env = baseline_env or baseline_environment_for_profile(profile)
    return BaselineRunState(
        bundle=bundle,
        policy_id=policy_id,
        policy_pack=policy_pack,
        baseline_env=env,
    )
