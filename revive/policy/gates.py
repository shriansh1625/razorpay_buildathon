"""Twelve gates G1–G12 — docs/13 §3."""

from __future__ import annotations

from typing import Any

from revive.domain.enums import ActionCode, ApprovalRequestState, GateVerdictKind
from revive.policy.config import PolicyRules, TIER_INCENTIVE_PCT
from revive.policy.context import AuthorizeContext
from revive.policy.models import GateResult

_CONTACT_ACTIONS = frozenset(
    {
        ActionCode.A03,
        ActionCode.A04,
        ActionCode.A05,
        ActionCode.A06,
        ActionCode.A07,
        ActionCode.A08,
        ActionCode.A09,
        ActionCode.A10,
        ActionCode.A11,
        ActionCode.A12,
    }
)
_RETRY_ACTIONS = frozenset({ActionCode.A01, ActionCode.A02, ActionCode.A03})
_INCENTIVE_ACTIONS = frozenset({ActionCode.A10, ActionCode.A11})


def evaluate_gates(
    action: ActionCode,
    params: dict[str, Any],
    ctx: AuthorizeContext,
    rules: PolicyRules,
    enrv_paise: int,
    enrv_lo_paise: int,
    enrv_hi_paise: int,
) -> tuple[GateResult, ...]:
    """Fixed order G1…G12 — every applicable gate recorded."""
    trace: list[GateResult] = []
    seq = 1

    trace.append(_g1_consent(action, params, ctx, seq))
    seq += 1
    trace.append(_g2_window(action, params, ctx, rules, seq))
    seq += 1
    trace.append(_g3_contact_cap(action, ctx, rules, seq))
    seq += 1
    trace.append(_g4_retry_cap(action, ctx, rules, seq))
    seq += 1
    trace.append(_g5_incentive(action, params, ctx, rules, enrv_paise, seq))
    seq += 1
    trace.append(_g6_budget_capacity(action, params, ctx, seq))
    seq += 1
    trace.append(
        _g7_approval(action, ctx, rules, enrv_paise, enrv_lo_paise, enrv_hi_paise, seq)
    )
    seq += 1
    trace.append(_g8_risk_block(ctx, seq))
    seq += 1
    trace.append(_g9_duplicate(ctx, seq))
    seq += 1
    trace.append(_g10_placeholder(seq))  # stopping evaluated separately; trace slot preserved
    seq += 1
    trace.append(_g11_channel(action, params, ctx, seq))
    seq += 1
    trace.append(_g12_amount_sanity(action, params, ctx, rules, enrv_paise, seq))

    return tuple(trace)


def worst_verdict(trace: tuple[GateResult, ...]) -> GateResult | None:
    order = {
        GateVerdictKind.DENY: 0,
        GateVerdictKind.REQUIRE_APPROVAL: 1,
        GateVerdictKind.DEFER: 2,
        GateVerdictKind.ALLOW_WITH_MODIFICATION: 3,
        GateVerdictKind.ALLOW: 4,
    }
    blocking = [g for g in trace if g.blocking or g.verdict != GateVerdictKind.ALLOW]
    if not blocking:
        return None
    return min(blocking, key=lambda g: order.get(g.verdict, 99))


def _g1_consent(action: ActionCode, params: dict, ctx: AuthorizeContext, seq: int) -> GateResult:
    if action not in _CONTACT_ACTIONS:
        return _allow("G1", seq, "CONSENT_NOT_REQUIRED")
    channel = str(params.get("channel", "SMS"))
    if ctx.opted_out:
        return _deny("G1", seq, "OPT_OUT", channel, "consent")
    if channel not in ctx.consent_channels:
        return _deny("G1", seq, "NO_CONSENT", channel, list(ctx.consent_channels))
    return _allow("G1", seq, "CONSENT_OK")


def _g2_window(
    action: ActionCode,
    params: dict,
    ctx: AuthorizeContext,
    rules: PolicyRules,
    seq: int,
) -> GateResult:
    if action not in _CONTACT_ACTIONS:
        return _allow("G2", seq, "WINDOW_NOT_APPLICABLE")
    hour = ctx.merchant_local_hour
    if rules.communication_start_hour <= hour < rules.communication_end_hour:
        return _allow("G2", seq, "WITHIN_WINDOW")
    return GateResult(
        gate_id="G2",
        sequence=seq,
        verdict=GateVerdictKind.DEFER,
        reason_code="CONTACT_WINDOW_CLOSED",
        blocking=True,
        observed_value=hour,
        limit_value=(rules.communication_start_hour, rules.communication_end_hour),
        detail={
            "allowed_window": f"{rules.communication_start_hour:02d}:00–{rules.communication_end_hour:02d}:00",
        },
    )


def _g3_contact_cap(
    action: ActionCode,
    ctx: AuthorizeContext,
    rules: PolicyRules,
    seq: int,
) -> GateResult:
    if action not in _CONTACT_ACTIONS:
        return _allow("G3", seq, "CONTACT_NOT_APPLICABLE")
    if ctx.contacts_today >= rules.max_contacts_per_customer:
        return _deny(
            "G3",
            seq,
            "MAX_CONTACTS_REACHED",
            ctx.contacts_today,
            rules.max_contacts_per_customer,
        )
    return _allow("G3", seq, "CONTACT_OK")


def _g4_retry_cap(
    action: ActionCode,
    ctx: AuthorizeContext,
    rules: PolicyRules,
    seq: int,
) -> GateResult:
    if action not in _RETRY_ACTIONS:
        return _allow("G4", seq, "RETRY_NOT_APPLICABLE")
    if ctx.retries_on_opportunity >= rules.max_retries_per_opportunity:
        return _deny(
            "G4",
            seq,
            "RETRY_CAP_REACHED",
            ctx.retries_on_opportunity,
            rules.max_retries_per_opportunity,
        )
    return _allow("G4", seq, "RETRY_OK")


def _g5_incentive(
    action: ActionCode,
    params: dict,
    ctx: AuthorizeContext,
    rules: PolicyRules,
    enrv_paise: int,
    seq: int,
) -> GateResult:
    if action not in _INCENTIVE_ACTIONS:
        return _allow("G5", seq, "INCENTIVE_NOT_APPLICABLE")
    tier = str(params.get("incentive_tier", "TIER_0"))
    requested_pct = float(params.get("incentive_pct", TIER_INCENTIVE_PCT.get(tier, 0.0)))
    if requested_pct <= rules.max_incentive_pct:
        return _allow("G5", seq, "INCENTIVE_OK")
    return GateResult(
        gate_id="G5",
        sequence=seq,
        verdict=GateVerdictKind.DENY,
        reason_code="MAX_DISCOUNT_EXCEEDED",
        blocking=True,
        observed_value=requested_pct,
        limit_value=rules.max_incentive_pct,
        detail={
            "proposed_pct": requested_pct,
            "allowed_pct": rules.max_incentive_pct,
            "tier": tier,
        },
    )


def _g6_budget_capacity(
    action: ActionCode,
    params: dict,
    ctx: AuthorizeContext,
    seq: int,
) -> GateResult:
    if action in _RETRY_ACTIONS and ctx.retry_slots_remaining <= 0:
        return _defer("G6", seq, "RETRY_CAPACITY_EXHAUSTED", 0, ctx.retry_slots_remaining)
    if action in _CONTACT_ACTIONS and ctx.message_capacity_remaining <= 0:
        return _defer("G6", seq, "MESSAGE_CAPACITY_EXHAUSTED", 0, ctx.message_capacity_remaining)
    tier = str(params.get("incentive_tier", "TIER_0"))
    if tier != "TIER_0" and ctx.budget_remaining_paise <= 0:
        return _defer("G6", seq, "INCENTIVE_BUDGET_EXHAUSTED", 0, ctx.budget_remaining_paise)
    return _allow("G6", seq, "CAPACITY_OK")


def g7_approval_triggers(
    action: ActionCode,
    ctx: AuthorizeContext,
    rules: PolicyRules,
    enrv_paise: int,
    enrv_lo: int,
    enrv_hi: int,
) -> tuple[str, ...]:
    """Observable G7 trigger list — shared by gate evaluation and simulated_v1."""
    triggers: list[str] = []
    if ctx.value_at_risk_paise >= rules.approval_value_threshold_paise:
        triggers.append("VALUE_THRESHOLD")
    if action.value in rules.approval_required_actions:
        triggers.append("ACTION_FAMILY")
    if ctx.first_use_action_for_merchant:
        triggers.append("FIRST_USE")
    width = enrv_hi - enrv_lo
    if enrv_paise > 0 and width / enrv_paise > rules.approval_uncertainty_ratio:
        triggers.append("UNCERTAINTY")
    return tuple(triggers)


def _g7_approval(
    action: ActionCode,
    ctx: AuthorizeContext,
    rules: PolicyRules,
    enrv_paise: int,
    enrv_lo: int,
    enrv_hi: int,
    seq: int,
) -> GateResult:
    triggers = list(
        g7_approval_triggers(action, ctx, rules, enrv_paise, enrv_lo, enrv_hi)
    )
    if not triggers:
        return _allow("G7", seq, "APPROVAL_NOT_REQUIRED")
    if ctx.approval_state == ApprovalRequestState.APPROVED:
        return _allow("G7", seq, "APPROVAL_GRANTED")
    if ctx.approval_state == ApprovalRequestState.REJECTED:
        return _deny("G7", seq, "APPROVAL_DENIED", triggers, None)
    return GateResult(
        gate_id="G7",
        sequence=seq,
        verdict=GateVerdictKind.REQUIRE_APPROVAL,
        reason_code="REQUIRES_HUMAN_APPROVAL",
        blocking=True,
        observed_value=triggers,
        detail={"triggers": triggers},
    )


def _g8_risk_block(ctx: AuthorizeContext, seq: int) -> GateResult:
    if ctx.risk_flags:
        return _deny("G8", seq, "RISK_BLOCK", list(ctx.risk_flags), None)
    return _allow("G8", seq, "RISK_OK")


def _g9_duplicate(ctx: AuthorizeContext, seq: int) -> GateResult:
    if ctx.duplicate_idempotency_claimed:
        return _deny("G9", seq, "DUPLICATE_IDEMPOTENCY", True, None)
    if ctx.duplicate_semantic_recent:
        return _deny("G9", seq, "DUPLICATE_SEMANTIC", True, None)
    return _allow("G9", seq, "DUPLICATE_OK")


def _g10_placeholder(seq: int) -> GateResult:
    return _allow("G10", seq, "STOPPING_EVALUATED_EXTERNALLY")


def _g11_channel(
    action: ActionCode,
    params: dict,
    ctx: AuthorizeContext,
    seq: int,
) -> GateResult:
    if action not in _CONTACT_ACTIONS:
        return _allow("G11", seq, "CHANNEL_NOT_APPLICABLE")
    channel = str(params.get("channel", "SMS"))
    if channel in ctx.channel_degraded:
        return _deny("G11", seq, "CHANNEL_DEGRADED", channel, None)
    return _allow("G11", seq, "CHANNEL_OK")


def _g12_amount_sanity(
    action: ActionCode,
    params: dict,
    ctx: AuthorizeContext,
    rules: PolicyRules,
    enrv_paise: int,
    seq: int,
) -> GateResult:
    if ctx.value_at_risk_paise > rules.amount_sanity_max_paise:
        return _deny(
            "G12",
            seq,
            "AMOUNT_SANITY_ABSOLUTE",
            ctx.value_at_risk_paise,
            rules.amount_sanity_max_paise,
        )
    if action in _RETRY_ACTIONS and ctx.transaction_amount_paise is not None:
        if ctx.transaction_amount_paise != ctx.value_at_risk_paise:
            return _deny(
                "G12",
                seq,
                "RETRY_AMOUNT_MISMATCH",
                ctx.transaction_amount_paise,
                ctx.value_at_risk_paise,
            )
    if enrv_paise < 0:
        return _deny("G12", seq, "NEGATIVE_ENRV", enrv_paise, 0)
    return _allow("G12", seq, "AMOUNT_OK")


def _allow(gate: str, seq: int, reason: str) -> GateResult:
    return GateResult(
        gate_id=gate,
        sequence=seq,
        verdict=GateVerdictKind.ALLOW,
        reason_code=reason,
        blocking=False,
    )


def _deny(
    gate: str,
    seq: int,
    reason: str,
    observed: Any,
    limit: Any,
) -> GateResult:
    return GateResult(
        gate_id=gate,
        sequence=seq,
        verdict=GateVerdictKind.DENY,
        reason_code=reason,
        blocking=True,
        observed_value=observed,
        limit_value=limit,
    )


def _defer(
    gate: str,
    seq: int,
    reason: str,
    observed: Any,
    limit: Any,
) -> GateResult:
    return GateResult(
        gate_id=gate,
        sequence=seq,
        verdict=GateVerdictKind.DEFER,
        reason_code=reason,
        blocking=True,
        observed_value=observed,
        limit_value=limit,
    )
