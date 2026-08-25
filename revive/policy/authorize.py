"""Authorization entry — M9 decision → execution authorization artifact."""

from __future__ import annotations

import hashlib

from revive.config.policy_pack import PolicyPack, PolicyPackStatus, default_draft_policy_pack
from revive.domain.enums import ActionCode, ApprovalRequestState, DecisionOutcome
from revive.decision.models import AllocationDecision, DecisionLifecycleStatus
from revive.policy.config import AUTHORIZATION_VERSION, PolicyRules, default_policy_rules
from revive.policy.context import AuthorizeContext
from revive.policy.gates import evaluate_gates, worst_verdict
from revive.policy.models import AuthorizationState, ExecutionAuthorization, GateResult
from revive.policy.stopping import any_blocking_stopping, evaluate_stopping_rules
from revive.policy.store import AuthorizationStore
from revive.recovery.candidates.models import RecoveryCandidate
from revive.recovery.valuation.models import CandidateValuation


def authorization_id_for(decision_id: str, configuration_hash: str) -> str:
    digest = hashlib.sha256(f"{decision_id}:{configuration_hash}".encode()).hexdigest()
    return f"auth_{digest[:26]}"


def authorize_execution(
    decision: AllocationDecision,
    candidate: RecoveryCandidate | None,
    valuation: CandidateValuation | None,
    ctx: AuthorizeContext,
    policy: PolicyPack | None = None,
    rules: PolicyRules | None = None,
    store: AuthorizationStore | None = None,
) -> ExecutionAuthorization:
    """
    Evaluate gates and stopping rules for an already-selected allocation.

    Does NOT execute, re-allocate, or substitute actions.
    """
    pol = policy or default_draft_policy_pack()
    rule_set = rules or PolicyRules.from_policy_metadata(pol.metadata)
    auth_store = store or AuthorizationStore()

    action = decision.action_code
    params = dict(candidate.params) if candidate else {}
    enrv = valuation.enrv_paise if valuation else decision.enrv_paise
    enrv_lo = valuation.enrv_lo_paise if valuation else enrv
    enrv_hi = valuation.enrv_hi_paise if valuation else enrv

    # --- M9 validity pre-checks ---
    if ctx.reconciliation_status == "STALE":
        return _blocked_authorization(
            decision, candidate, valuation, pol, rule_set,
            AuthorizationState.STALE, "STALE_DECISION", "M9", ctx.now_micros,
        )
    if ctx.reconciliation_status == "EXPIRED" or ctx.now_micros > decision.expires_at_micros:
        return _blocked_authorization(
            decision, candidate, valuation, pol, rule_set,
            AuthorizationState.EXPIRED, "EXPIRED_DECISION", "M9", ctx.now_micros,
        )
    if decision.lifecycle_status in {
        DecisionLifecycleStatus.SUPERSEDED,
        DecisionLifecycleStatus.CANCELLED,
    }:
        return _blocked_authorization(
            decision, candidate, valuation, pol, rule_set,
            AuthorizationState.STALE, "DECISION_INVALID", "M9", ctx.now_micros,
        )
    if ctx.configuration_hash and ctx.configuration_hash != decision.configuration_hash:
        return _blocked_authorization(
            decision, candidate, valuation, pol, rule_set,
            AuthorizationState.REPLAN_REQUIRED, "CONFIGURATION_MISMATCH", "M9", ctx.now_micros,
        )
    if pol.status == PolicyPackStatus.DRAFT and ctx.policy_pack_hash:
        if ctx.policy_pack_hash != pol.config_hash():
            return _blocked_authorization(
                decision, candidate, valuation, pol, rule_set,
                AuthorizationState.REPLAN_REQUIRED, "POLICY_PACK_MISMATCH", "M9", ctx.now_micros,
            )

    if decision.outcome != DecisionOutcome.SELECTED or action == ActionCode.A00:
        return _blocked_authorization(
            decision, candidate, valuation, pol, rule_set,
            AuthorizationState.BLOCKED, decision.reason_code, "M9", ctx.now_micros,
        )

    if candidate is None or valuation is None:
        return _blocked_authorization(
            decision, candidate, valuation, pol, rule_set,
            AuthorizationState.BLOCKED, "CANDIDATE_MISSING", "M9", ctx.now_micros,
        )

    if auth_store.is_idempotency_claimed(decision.idempotency_key):
        return _finalize(
            decision, candidate, valuation, pol, rule_set, ctx,
            AuthorizationState.BLOCKED,
            "DUPLICATE_IDEMPOTENCY",
            "G9",
            tuple(),
            tuple(),
            False,
            ctx.approval_state,
            auth_store,
        )

    # Stopping rules (pre-execution — docs/14 §3)
    stopping = evaluate_stopping_rules(action, ctx, rule_set)
    blocking_stop = any_blocking_stopping(stopping)
    if blocking_stop is not None:
        return _finalize(
            decision, candidate, valuation, pol, rule_set, ctx,
            AuthorizationState.BLOCKED,
            blocking_stop.reason_code,
            "G10",
            tuple(),
            stopping,
            False,
            ctx.approval_state,
            auth_store,
        )

    # Gates G1–G12
    gate_trace = evaluate_gates(
        action, params, ctx, rule_set, enrv, enrv_lo, enrv_hi,
    )
    worst = worst_verdict(gate_trace)

    if worst is None:
        state = AuthorizationState.AUTHORIZED
        reason = "AUTHORIZED"
        gate_id = None
        approval_req = False
    elif worst.verdict.value == "REQUIRE_APPROVAL":
        if ctx.approval_state == ApprovalRequestState.APPROVED:
            state = AuthorizationState.AUTHORIZED
            reason = "APPROVAL_GRANTED"
            gate_id = None
            approval_req = True
        else:
            state = AuthorizationState.REQUIRES_HUMAN_APPROVAL
            reason = worst.reason_code
            gate_id = worst.gate_id
            approval_req = True
    elif worst.verdict.value == "DEFER":
        state = AuthorizationState.REPLAN_REQUIRED
        reason = worst.reason_code
        gate_id = worst.gate_id
        approval_req = False
    else:
        state = AuthorizationState.BLOCKED
        reason = worst.reason_code
        gate_id = worst.gate_id
        approval_req = False

    return _finalize(
        decision, candidate, valuation, pol, rule_set, ctx,
        state, reason, gate_id, gate_trace, stopping,
        approval_req, ctx.approval_state, auth_store,
    )


def _blocked_authorization(
    decision: AllocationDecision,
    candidate: RecoveryCandidate | None,
    valuation: CandidateValuation | None,
    policy: PolicyPack,
    rules: PolicyRules,
    state: AuthorizationState,
    reason: str,
    gate_id: str | None,
    now_micros: int,
) -> ExecutionAuthorization:
    return _finalize(
        decision,
        candidate,
        valuation,
        policy,
        rules,
        AuthorizeContext(
            now_micros=now_micros,
            opportunity_state="UNKNOWN",
            value_at_risk_paise=0,
            customer_id=None,
        ),
        state,
        reason,
        gate_id,
        tuple(),
        tuple(),
        False,
        None,
        AuthorizationStore(),
    )


def _finalize(
    decision: AllocationDecision,
    candidate: RecoveryCandidate | None,
    valuation: CandidateValuation | None,
    policy: PolicyPack,
    rules: PolicyRules,
    ctx: AuthorizeContext,
    state: AuthorizationState,
    reason: str,
    gate_id: str | None,
    gate_trace: tuple[GateResult, ...],
    stopping: tuple,
    approval_req: bool,
    approval_state: ApprovalRequestState | None,
    store: AuthorizationStore,
) -> ExecutionAuthorization:
    action = decision.action_code
    params = dict(candidate.params) if candidate else {}
    enrv = valuation.enrv_paise if valuation else decision.enrv_paise
    auth_id = authorization_id_for(decision.decision_id, decision.configuration_hash)
    expires = (
        ctx.now_micros + rules.authorization_ttl_micros
        if state == AuthorizationState.AUTHORIZED
        else None
    )
    authorized_at = ctx.now_micros if state == AuthorizationState.AUTHORIZED else None

    explanation: list[str] = [
        f"authorization_state={state.value}",
        f"action={action.value}",
    ]
    if gate_id:
        explanation.append(f"blocking_gate={gate_id}")
    if reason:
        explanation.append(f"reason={reason}")

    auth = ExecutionAuthorization(
        authorization_id=auth_id,
        decision_id=decision.decision_id,
        opportunity_id=decision.opportunity_id,
        candidate_id=decision.candidate_id,
        action_code=action,
        authorized_parameters=params if state == AuthorizationState.AUTHORIZED else params,
        authorization_state=state,
        gate_trace=gate_trace,
        stopping_results=stopping,
        approval_requirement=approval_req,
        approval_state=approval_state,
        policy_pack_version=policy.version,
        configuration_hash=decision.configuration_hash,
        allocator_version=decision.allocator_version,
        valuation_version=decision.valuation_version,
        authorization_version=AUTHORIZATION_VERSION,
        authorized_at_micros=authorized_at,
        expires_at_micros=expires,
        idempotency_key=decision.idempotency_key,
        enrv_paise=enrv,
        blocking_gate_id=gate_id,
        blocking_reason_code=reason if state != AuthorizationState.AUTHORIZED else None,
        audit_reference=f"auth:{auth_id}",
        explanation=tuple(explanation),
    )
    return store.record(auth)
