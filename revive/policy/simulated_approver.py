"""simulated_v1 — deterministic benchmark approver (docs/07 §6.2, docs/08 C-15)."""

from __future__ import annotations

import hashlib
from dataclasses import replace

from revive.domain.enums import ActionCode, ApprovalRequestState
from revive.decision.models import AllocationDecision
from revive.policy.config import PolicyRules
from revive.policy.context import AuthorizeContext
from revive.policy.gates import g7_approval_triggers

SIMULATED_V1_MODEL = "simulated_v1"
SIMULATED_V1_APPROVAL_RATE = 0.85


def _deterministic_draw(master_seed: int, idempotency_key: str) -> float:
    digest = hashlib.sha256(
        f"{master_seed}:approver:{idempotency_key}".encode()
    ).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


def simulated_v1_approval_state(
    *,
    master_seed: int,
    idempotency_key: str,
    triggers: tuple[str, ...],
    ctx: AuthorizeContext,
) -> ApprovalRequestState:
    """
    Deterministic approval outcome when G7 requires human approval.

    Rejects on observable halt/risk flags; otherwise keyed draw vs frozen rate.
    """
    if ctx.risk_flags or ctx.merchant_halt or ctx.value_written_off:
        return ApprovalRequestState.REJECTED

    draw = _deterministic_draw(master_seed, idempotency_key)
    if draw < SIMULATED_V1_APPROVAL_RATE:
        return ApprovalRequestState.APPROVED
    return ApprovalRequestState.REJECTED


def resolve_simulated_approval_state(
    *,
    model_version: str,
    master_seed: int,
    decision: AllocationDecision,
    action: ActionCode,
    ctx: AuthorizeContext,
    rules: PolicyRules,
    enrv_paise: int,
    enrv_lo_paise: int,
    enrv_hi_paise: int,
) -> ApprovalRequestState | None:
    """
    Invoke frozen simulated approver before M10 authorize_execution().

    Returns None when G7 would not require approval (G7 allows without state).
    """
    if model_version != SIMULATED_V1_MODEL:
        return None

    triggers = g7_approval_triggers(
        action,
        ctx,
        rules,
        enrv_paise,
        enrv_lo_paise,
        enrv_hi_paise,
    )
    if not triggers:
        return None

    return simulated_v1_approval_state(
        master_seed=master_seed,
        idempotency_key=decision.idempotency_key,
        triggers=triggers,
        ctx=ctx,
    )


def authorize_context_with_simulated_approval(
    base_ctx: AuthorizeContext,
    *,
    model_version: str,
    master_seed: int,
    decision: AllocationDecision,
    action: ActionCode,
    rules: PolicyRules,
    enrv_paise: int,
    enrv_lo_paise: int,
    enrv_hi_paise: int,
) -> AuthorizeContext:
    """Return AuthorizeContext with simulated_v1 approval_state when required."""
    approval_state = resolve_simulated_approval_state(
        model_version=model_version,
        master_seed=master_seed,
        decision=decision,
        action=action,
        ctx=base_ctx,
        rules=rules,
        enrv_paise=enrv_paise,
        enrv_lo_paise=enrv_lo_paise,
        enrv_hi_paise=enrv_hi_paise,
    )
    if approval_state is None:
        return base_ctx
    return replace(base_ctx, approval_state=approval_state)
