"""Bounded recovery execution — M11."""

from __future__ import annotations

import hashlib

from revive.domain.enums import ActionCode, InterventionState
from revive.decision.ledger import ReservationLedger
from revive.decision.models import AllocationDecision
from revive.policy.models import AuthorizationState, ExecutionAuthorization
from revive.recovery.candidates.models import RecoveryCandidate
from revive.recovery.valuation.models import CandidateValuation
from revive.simulation.oracle.resolve import OutcomeResult
from revive.simulation.types import AdapterResult

from revive.audit.journal import AuditEventType, AuditJournal
from revive.execution.adapters import simulated as adapter_layer
from revive.execution.authorised import mint_authorised_action
from revive.execution.config import EXECUTION_VERSION, MINUTE_MICROS
from revive.execution.environment import ExecutionEnvironment
from revive.execution.models import (
    AuthorisedAction,
    ExecutionResult,
    ExecutionStage,
    RealizedOutcome,
    RejectionReason,
)
from revive.execution.settlement import realized_cost_paise, settle_reservations
from revive.execution.store import ExecutionStore
from revive.execution.world_update import (
    apply_intervention_transition,
    customer_response_for,
    intervention_state_for,
    payment_state_for,
    transition_opportunity_state,
)

__all__ = [
    "EXECUTION_VERSION",
    "ExecutionAgent",
    "ExecutionEnvironment",
    "ExecutionResult",
    "ExecutionStore",
    "AuthorisedAction",
    "mint_authorised_action",
    "execute_authorization",
    "execute",
]


class ExecutionAgent:
    """Single execution path — docs/15 §1, RR-GUARD-021."""

    def __init__(
        self,
        store: ExecutionStore | None = None,
        audit: AuditJournal | None = None,
    ) -> None:
        self._store = store or ExecutionStore()
        self._audit = audit or AuditJournal()

    @property
    def store(self) -> ExecutionStore:
        return self._store

    @property
    def audit(self) -> AuditJournal:
        return self._audit

    def execute(
        self,
        authorised: AuthorisedAction,
        decision: AllocationDecision,
        candidate: RecoveryCandidate,
        valuation: CandidateValuation,
        env: ExecutionEnvironment,
        ledger: ReservationLedger,
        now_micros: int,
        *,
        skip_delay: bool = False,
    ) -> ExecutionResult:
        return _execute_impl(
            authorised,
            decision,
            candidate,
            valuation,
            env,
            ledger,
            now_micros,
            self._store,
            self._audit,
            skip_delay=skip_delay,
        )


def execute(
    authorised: AuthorisedAction,
    decision: AllocationDecision,
    candidate: RecoveryCandidate,
    valuation: CandidateValuation,
    env: ExecutionEnvironment,
    ledger: ReservationLedger,
    now_micros: int,
    *,
    store: ExecutionStore | None = None,
    audit: AuditJournal | None = None,
    skip_delay: bool = False,
) -> ExecutionResult:
    return _execute_impl(
        authorised,
        decision,
        candidate,
        valuation,
        env,
        ledger,
        now_micros,
        store or ExecutionStore(),
        audit or AuditJournal(),
        skip_delay=skip_delay,
    )


def execute_authorization(
    authorization: ExecutionAuthorization,
    decision: AllocationDecision,
    candidate: RecoveryCandidate,
    valuation: CandidateValuation,
    env: ExecutionEnvironment,
    ledger: ReservationLedger,
    now_micros: int,
    *,
    store: ExecutionStore | None = None,
    audit: AuditJournal | None = None,
    skip_delay: bool = False,
) -> ExecutionResult:
    """Execute from authorization artifact — rejects non-AUTHORIZED states."""
    exec_store = store or ExecutionStore()
    exec_audit = audit or AuditJournal()

    if authorization.authorization_state != AuthorizationState.AUTHORIZED:
        return _rejection_result(
            authorization,
            decision,
            valuation,
            now_micros,
            RejectionReason.NOT_AUTHORIZED,
            authorization.blocking_reason_code or authorization.authorization_state.value,
            exec_store,
        )

    if authorization.expires_at_micros is not None and now_micros > authorization.expires_at_micros:
        return _rejection_result(
            authorization,
            decision,
            valuation,
            now_micros,
            RejectionReason.AUTHORIZATION_EXPIRED,
            "AUTHORIZATION_EXPIRED",
            exec_store,
        )

    authorised = mint_authorised_action(authorization)
    return _execute_impl(
        authorised,
        decision,
        candidate,
        valuation,
        env,
        ledger,
        now_micros,
        exec_store,
        exec_audit,
        skip_delay=skip_delay,
    )


def _execute_impl(
    authorised: AuthorisedAction,
    decision: AllocationDecision,
    candidate: RecoveryCandidate,
    valuation: CandidateValuation,
    env: ExecutionEnvironment,
    ledger: ReservationLedger,
    now_micros: int,
    store: ExecutionStore,
    audit: AuditJournal,
    *,
    skip_delay: bool = False,
) -> ExecutionResult:
    existing = store.get_by_idempotency(authorised.idempotency_key)
    completing_scheduled = (
        existing is not None
        and existing.execution_stage == ExecutionStage.SCHEDULED
        and (
            skip_delay
            or (
                existing.scheduled_at_micros is not None
                and now_micros >= existing.scheduled_at_micros
            )
        )
    )

    if authorised.expires_at_micros is not None and now_micros > authorised.expires_at_micros:
        return _build_rejection_from_authorised(
            authorised,
            decision,
            valuation,
            now_micros,
            RejectionReason.AUTHORIZATION_EXPIRED,
            "AUTHORIZATION_EXPIRED",
            store,
        )

    if existing is not None and not completing_scheduled:
        return _duplicate_result(existing)

    if not ledger.has_active(decision.decision_id) and not ledger.is_committed(decision.decision_id):
        return _build_rejection_from_authorised(
            authorised,
            decision,
            valuation,
            now_micros,
            RejectionReason.RESERVATION_INVALID,
            "RESERVATION_INVALID",
            store,
        )

    # Delayed retry scheduling (A02) — do not execute before scheduled time
    scheduled_at: int | None = None
    if not skip_delay and authorised.action_code == ActionCode.A02:
        delay_minutes = int(
            authorised.authorized_parameters.get(
                "delay_minutes",
                candidate.params.get("delay_minutes", 0),
            )
        )
        earliest = candidate.earliest_eligible_at_micros
        if earliest is not None:
            scheduled_at = earliest
        elif delay_minutes > 0:
            scheduled_at = now_micros + delay_minutes * MINUTE_MICROS
        if scheduled_at is not None and now_micros < scheduled_at:
            if existing is None and not store.claim(authorised.idempotency_key):
                dup = store.get_by_idempotency(authorised.idempotency_key)
                if dup:
                    return _duplicate_result(dup)
            intent_ref = _write_intent_audit(
                audit, authorised, decision, now_micros, scheduled_at=scheduled_at
            )
            result = _build_scheduled_result(
                authorised, decision, valuation, now_micros, scheduled_at, intent_ref
            )
            return store.record(result)
        elif scheduled_at is not None and now_micros >= scheduled_at and completing_scheduled:
            pass  # complete scheduled execution below

    if not completing_scheduled and not store.claim(authorised.idempotency_key):
        dup = store.get_by_idempotency(authorised.idempotency_key)
        if dup:
            return _duplicate_result(dup)

    if completing_scheduled and existing is not None and existing.audit_intent_ref:
        intent_ref = existing.audit_intent_ref
    else:
        intent_ref = _write_intent_audit(
            audit, authorised, decision, now_micros,
            scheduled_at=existing.scheduled_at_micros if completing_scheduled and existing else None,
        )

    intervention_state = InterventionState.INTENDED
    intervention_state = apply_intervention_transition(
        intervention_state, InterventionState.IN_FLIGHT
    )

    if authorised.action_code in {ActionCode.A03, ActionCode.A04, ActionCode.A05}:
        env.increment_contact(env.customer_id)

    outcome_result = adapter_layer.invoke(authorised, env, now_micros)
    realized = _realized_from_outcome(outcome_result)

    settlement, consumed = settle_reservations(
        outcome_result.adapter_result, ledger, decision.decision_id
    )
    predicted_cost = valuation.cost_paise + valuation.expected_incentive_paise
    realized_cost = realized_cost_paise(
        outcome_result.adapter_result, predicted_cost, consumed
    )

    opp_state = transition_opportunity_state(
        env, outcome_result.adapter_result, realized
    )
    final_intervention = intervention_state_for(outcome_result.adapter_result)
    final_intervention = apply_intervention_transition(
        intervention_state, final_intervention
    )

    stage = _stage_for_adapter(outcome_result.adapter_result)
    result_ref = audit.append(
        AuditEventType.ACTION_RESULT,
        now_micros,
        _correlation(authorised, decision),
        {
            "adapter_result": outcome_result.adapter_result.value,
            "execution_stage": stage.value,
            "realized_cost_paise": realized_cost,
            "predicted_cost_paise": predicted_cost,
            "ledger_settlement": settlement.value,
            "realized_outcome": realized.to_dict(),
        },
    ).audit_id

    result = ExecutionResult(
        execution_id=_execution_id_for(authorised),
        authorization_id=authorised.authorization_id,
        decision_id=decision.decision_id,
        opportunity_id=authorised.opportunity_id,
        candidate_id=authorised.candidate_id,
        action_code=authorised.action_code,
        intervention_id=_intervention_id_for(authorised),
        execution_stage=stage,
        adapter_result=outcome_result.adapter_result,
        predicted_cost_paise=predicted_cost,
        realized_cost_paise=realized_cost,
        predicted_enrv_paise=valuation.enrv_paise,
        idempotency_key=authorised.idempotency_key,
        executed_at_micros=now_micros,
        duplicate=False,
        failure_reason=None,
        ledger_settlement=settlement,
        intervention_state=final_intervention,
        opportunity_state=opp_state,
        payment_state=payment_state_for(
            authorised.action_code.value,
            outcome_result.adapter_result,
            realized,
        ),
        customer_response=customer_response_for(outcome_result.adapter_result),
        realized_outcome=realized,
        resource_consumed=consumed,
        scheduled_at_micros=None,
        audit_intent_ref=intent_ref,
        audit_result_ref=result_ref,
        configuration_hash=authorised.configuration_hash,
        authorization_version=authorised.authorization_version,
        execution_version=EXECUTION_VERSION,
    )
    return store.record(result)


def _realized_from_outcome(outcome: OutcomeResult) -> RealizedOutcome:
    recovered_at = (
        outcome.recovered_at.epoch_micros if outcome.recovered_at is not None else None
    )
    return RealizedOutcome(
        outcome_kind=outcome.outcome_kind,
        recovered_amount_paise=outcome.recovered_amount_paise,
        recovered_at_micros=recovered_at,
        observed_within_horizon=outcome.observed_within_horizon,
        late_recovery=outcome.late_recovery,
        attribution_class=outcome.attribution_class.value,
    )


def _stage_for_adapter(adapter_result: AdapterResult) -> ExecutionStage:
    mapping = {
        AdapterResult.SUCCESS: ExecutionStage.SUCCEEDED,
        AdapterResult.FAILED_RETRYABLE: ExecutionStage.RETRYABLE,
        AdapterResult.FAILED_TERMINAL: ExecutionStage.PERMANENT_FAILURE,
        AdapterResult.TIMEOUT_UNKNOWN: ExecutionStage.FAILED,
        AdapterResult.REJECTED_BY_PROVIDER: ExecutionStage.FAILED,
    }
    return mapping.get(adapter_result, ExecutionStage.FAILED)


def _execution_id_for(authorised: AuthorisedAction) -> str:
    digest = hashlib.sha256(
        f"{authorised.idempotency_key}:{authorised.authorization_id}".encode()
    ).hexdigest()
    return f"exec_{digest[:26]}"


def _intervention_id_for(authorised: AuthorisedAction) -> str:
    digest = hashlib.sha256(
        f"int:{authorised.decision_id}:{authorised.action_code.value}".encode()
    ).hexdigest()
    return f"int_{digest[:26]}"


def _correlation(
    authorised: AuthorisedAction,
    decision: AllocationDecision,
) -> dict[str, str]:
    return {
        "cycle_id": decision.cycle_id,
        "opportunity_id": authorised.opportunity_id,
        "decision_id": decision.decision_id,
        "authorization_id": authorised.authorization_id,
        "intervention_id": _intervention_id_for(authorised),
    }


def _write_intent_audit(
    audit: AuditJournal,
    authorised: AuthorisedAction,
    decision: AllocationDecision,
    now_micros: int,
    scheduled_at: int | None = None,
) -> str:
    payload: dict[str, object] = {
        "action_code": authorised.action_code.value,
        "authorized_parameters": dict(authorised.authorized_parameters),
        "idempotency_key": authorised.idempotency_key,
        "configuration_hash": authorised.configuration_hash,
    }
    if scheduled_at is not None:
        payload["scheduled_at_micros"] = scheduled_at
    return audit.append(
        AuditEventType.ACTION_INTENT,
        now_micros,
        _correlation(authorised, decision),
        payload,
    ).audit_id


def _duplicate_result(existing: ExecutionResult) -> ExecutionResult:
    return ExecutionResult(
        execution_id=existing.execution_id,
        authorization_id=existing.authorization_id,
        decision_id=existing.decision_id,
        opportunity_id=existing.opportunity_id,
        candidate_id=existing.candidate_id,
        action_code=existing.action_code,
        intervention_id=existing.intervention_id,
        execution_stage=existing.execution_stage,
        adapter_result=existing.adapter_result,
        predicted_cost_paise=existing.predicted_cost_paise,
        realized_cost_paise=existing.realized_cost_paise,
        predicted_enrv_paise=existing.predicted_enrv_paise,
        idempotency_key=existing.idempotency_key,
        executed_at_micros=existing.executed_at_micros,
        duplicate=True,
        failure_reason=None,
        ledger_settlement=existing.ledger_settlement,
        intervention_state=existing.intervention_state,
        opportunity_state=existing.opportunity_state,
        payment_state=existing.payment_state,
        customer_response=existing.customer_response,
        realized_outcome=existing.realized_outcome,
        resource_consumed=existing.resource_consumed,
        scheduled_at_micros=existing.scheduled_at_micros,
        audit_intent_ref=existing.audit_intent_ref,
        audit_result_ref=existing.audit_result_ref,
        configuration_hash=existing.configuration_hash,
        authorization_version=existing.authorization_version,
        execution_version=existing.execution_version,
    )


def _build_scheduled_result(
    authorised: AuthorisedAction,
    decision: AllocationDecision,
    valuation: CandidateValuation,
    now_micros: int,
    scheduled_at: int,
    intent_ref: str,
) -> ExecutionResult:
    predicted_cost = valuation.cost_paise + valuation.expected_incentive_paise
    return ExecutionResult(
        execution_id=_execution_id_for(authorised),
        authorization_id=authorised.authorization_id,
        decision_id=decision.decision_id,
        opportunity_id=authorised.opportunity_id,
        candidate_id=authorised.candidate_id,
        action_code=authorised.action_code,
        intervention_id=_intervention_id_for(authorised),
        execution_stage=ExecutionStage.SCHEDULED,
        adapter_result=None,
        predicted_cost_paise=predicted_cost,
        realized_cost_paise=0,
        predicted_enrv_paise=valuation.enrv_paise,
        idempotency_key=authorised.idempotency_key,
        executed_at_micros=now_micros,
        duplicate=False,
        failure_reason=None,
        ledger_settlement=None,
        intervention_state=InterventionState.INTENDED,
        opportunity_state=env_opportunity_state_placeholder(),
        payment_state=None,
        customer_response=None,
        realized_outcome=None,
        resource_consumed=(),
        scheduled_at_micros=scheduled_at,
        audit_intent_ref=intent_ref,
        audit_result_ref=None,
        configuration_hash=authorised.configuration_hash,
        authorization_version=authorised.authorization_version,
        execution_version=EXECUTION_VERSION,
    )


def env_opportunity_state_placeholder() -> str:
    return "AUTHORISED"


def _rejection_result(
    authorization: ExecutionAuthorization,
    decision: AllocationDecision,
    valuation: CandidateValuation,
    now_micros: int,
    reason: RejectionReason,
    detail: str,
    store: ExecutionStore,
) -> ExecutionResult:
    existing = store.get_by_idempotency(authorization.idempotency_key)
    if existing is not None and existing.execution_stage != ExecutionStage.SCHEDULED:
        return _duplicate_result(existing)
    predicted_cost = valuation.cost_paise + valuation.expected_incentive_paise
    result = ExecutionResult(
        execution_id=_execution_id_for_rejection(authorization),
        authorization_id=authorization.authorization_id,
        decision_id=decision.decision_id,
        opportunity_id=authorization.opportunity_id,
        candidate_id=authorization.candidate_id,
        action_code=authorization.action_code,
        intervention_id=_intervention_id_for_auth(authorization),
        execution_stage=ExecutionStage.CANCELLED,
        adapter_result=None,
        predicted_cost_paise=predicted_cost,
        realized_cost_paise=0,
        predicted_enrv_paise=valuation.enrv_paise,
        idempotency_key=authorization.idempotency_key,
        executed_at_micros=now_micros,
        duplicate=False,
        failure_reason=f"{reason.value}:{detail}",
        ledger_settlement=None,
        intervention_state=InterventionState.INTENDED,
        opportunity_state=None,
        payment_state=None,
        customer_response=None,
        realized_outcome=None,
        resource_consumed=(),
        scheduled_at_micros=None,
        audit_intent_ref=None,
        audit_result_ref=None,
        configuration_hash=authorization.configuration_hash,
        authorization_version=authorization.authorization_version,
        execution_version=EXECUTION_VERSION,
    )
    return store.record(result)


def _build_rejection_from_authorised(
    authorised: AuthorisedAction,
    decision: AllocationDecision,
    valuation: CandidateValuation,
    now_micros: int,
    reason: RejectionReason,
    detail: str,
    store: ExecutionStore,
) -> ExecutionResult:
    auth_like = ExecutionAuthorization(
        authorization_id=authorised.authorization_id,
        decision_id=authorised.decision_id,
        opportunity_id=authorised.opportunity_id,
        candidate_id=authorised.candidate_id,
        action_code=authorised.action_code,
        authorized_parameters=authorised.authorized_parameters,
        authorization_state=AuthorizationState.BLOCKED,
        gate_trace=(),
        stopping_results=(),
        approval_requirement=False,
        approval_state=None,
        policy_pack_version=authorised.policy_pack_version,
        configuration_hash=authorised.configuration_hash,
        allocator_version=authorised.allocator_version,
        valuation_version=authorised.valuation_version,
        authorization_version=authorised.authorization_version,
        authorized_at_micros=None,
        expires_at_micros=authorised.expires_at_micros,
        idempotency_key=authorised.idempotency_key,
        enrv_paise=authorised.enrv_paise,
        blocking_gate_id=None,
        blocking_reason_code=detail,
        audit_reference=authorised.audit_reference,
        explanation=(),
    )
    return _rejection_result(
        auth_like, decision, valuation, now_micros, reason, detail, store
    )


def _execution_id_for_rejection(authorization: ExecutionAuthorization) -> str:
    digest = hashlib.sha256(
        f"rej:{authorization.idempotency_key}".encode()
    ).hexdigest()
    return f"exec_{digest[:26]}"


def _intervention_id_for_auth(authorization: ExecutionAuthorization) -> str:
    digest = hashlib.sha256(
        f"int:{authorization.decision_id}:{authorization.action_code.value}".encode()
    ).hexdigest()
    return f"int_{digest[:26]}"
