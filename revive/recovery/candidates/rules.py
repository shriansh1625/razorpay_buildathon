"""Cause- and class-aware action enumeration — docs/12 §8.3, docs/09 §2.4."""

from __future__ import annotations

from revive.domain.enums import ActionCode, CauseCode, RiskClass
from revive.recovery.diagnosis.models import Diagnosis

# Base action sets per risk class (before cause refinement).
_CLASS_ACTIONS: dict[RiskClass, frozenset[ActionCode]] = {
    RiskClass.PAYMENT_FAILURE: frozenset(
        {
            ActionCode.A01,
            ActionCode.A02,
            ActionCode.A03,
            ActionCode.A04,
            ActionCode.A05,
            ActionCode.A06,
            ActionCode.A10,
            ActionCode.A13,
        }
    ),
    RiskClass.CHECKOUT_ABANDONMENT: frozenset(
        {
            ActionCode.A07,
            ActionCode.A06,
            ActionCode.A05,
            ActionCode.A04,
            ActionCode.A10,
        }
    ),
    RiskClass.SUBSCRIPTION_FAILURE: frozenset(
        {
            ActionCode.A01,
            ActionCode.A02,
            ActionCode.A08,
            ActionCode.A05,
            ActionCode.A11,
            ActionCode.A13,
        }
    ),
    RiskClass.RECEIVABLE_OVERDUE: frozenset(
        {
            ActionCode.A05,
            ActionCode.A08,
            ActionCode.A09,
            ActionCode.A10,
            ActionCode.A11,
            ActionCode.A13,
            ActionCode.A14,
        }
    ),
    RiskClass.MANDATE_HEALTH: frozenset(
        {
            ActionCode.A08,
            ActionCode.A11,
            ActionCode.A05,
            ActionCode.A13,
        }
    ),
}

# Cause-level exclusions and additions (docs/12 §8.3 actionability table).
_CAUSE_EXCLUDE: dict[CauseCode, frozenset[ActionCode]] = {
    CauseCode.CARD_EXPIRED: frozenset({ActionCode.A01, ActionCode.A02}),
    CauseCode.ISSUER_DECLINE_HARD: frozenset({ActionCode.A01, ActionCode.A02}),
    CauseCode.MANDATE_REVOKED: frozenset({ActionCode.A01, ActionCode.A02}),
    CauseCode.AUTH_ABANDONED_BY_CUSTOMER: frozenset({ActionCode.A01, ActionCode.A02}),
    CauseCode.QUERY_OR_DISPUTE_RAISED: frozenset(
        {
            ActionCode.A01,
            ActionCode.A02,
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
    ),
    CauseCode.CUSTOMER_DECLINED_TO_PAY: frozenset(
        {a for a in ActionCode if a != ActionCode.A00}
    ),
    CauseCode.ORDER_NO_LONGER_WANTED: frozenset(
        {a for a in ActionCode if a != ActionCode.A00}
    ),
}

_CAUSE_PREFER_DELAYED_RETRY: frozenset[CauseCode] = frozenset(
    {
        CauseCode.INSUFFICIENT_FUNDS,
        CauseCode.ISSUER_DOWNTIME,
        CauseCode.GATEWAY_TIMEOUT,
        CauseCode.GATEWAY_ERROR,
    }
)

_CAUSE_NO_IMMEDIATE_RETRY: frozenset[CauseCode] = frozenset(
    {
        CauseCode.ISSUER_DOWNTIME,
        CauseCode.CARD_EXPIRED,
        CauseCode.ISSUER_DECLINE_HARD,
        CauseCode.MANDATE_REVOKED,
    }
)

_CAUSE_INCENTIVE_OK: frozenset[CauseCode] = frozenset(
    {
        CauseCode.PRICE_OR_FEE_HESITATION,
        CauseCode.BUYER_CASHFLOW_CONSTRAINT,
        CauseCode.INSUFFICIENT_FUNDS,
    }
)

_UNCLASSIFIED_ALLOWED: frozenset[ActionCode] = frozenset(
    {
        ActionCode.A02,
        ActionCode.A03,
        ActionCode.A05,
        ActionCode.A13,
    }
)


def primary_cause(diagnosis: Diagnosis) -> CauseCode:
    if diagnosis.ranked_causes:
        return diagnosis.ranked_causes[0].cause_code
    return CauseCode.UNCLASSIFIED


def enumerate_action_codes(
    risk_class: RiskClass,
    diagnosis: Diagnosis,
) -> frozenset[ActionCode]:
    """Return the action codes to evaluate for this opportunity."""
    base = set(_CLASS_ACTIONS.get(risk_class, frozenset()))
    cause = primary_cause(diagnosis)

    if cause == CauseCode.UNCLASSIFIED:
        base &= set(_UNCLASSIFIED_ALLOWED)

    excluded = _CAUSE_EXCLUDE.get(cause, frozenset())
    base -= set(excluded)

    # Secondary causes may add human escalation for high-value ambiguous cases.
    for ranked in diagnosis.ranked_causes[1:3]:
        if ranked.cause_code in {
            CauseCode.DO_NOT_HONOUR_AMBIGUOUS,
            CauseCode.BUYER_APPROVAL_PENDING,
        }:
            base.add(ActionCode.A13)

    if cause in _CAUSE_INCENTIVE_OK:
        base.add(ActionCode.A10)
        if risk_class == RiskClass.RECEIVABLE_OVERDUE:
            base.add(ActionCode.A11)

    base.add(ActionCode.A00)
    return frozenset(base)


def default_params_for(
    action: ActionCode,
    *,
    delay_minutes: int = 0,
    incentive_tier: str = "TIER_0",
    channel: str = "EMAIL",
) -> dict:
    params: dict = {}
    if action in {ActionCode.A02, ActionCode.A08, ActionCode.A11}:
        params["delay_minutes"] = delay_minutes
    if action in {
        ActionCode.A03,
        ActionCode.A04,
        ActionCode.A05,
        ActionCode.A06,
        ActionCode.A07,
        ActionCode.A08,
        ActionCode.A09,
    }:
        params["channel"] = channel
    if action in {ActionCode.A10, ActionCode.A11}:
        params["incentive_tier"] = incentive_tier
    return params


def prefers_delayed_retry(cause: CauseCode) -> bool:
    return cause in _CAUSE_PREFER_DELAYED_RETRY


def forbids_immediate_retry(cause: CauseCode) -> bool:
    return cause in _CAUSE_NO_IMMEDIATE_RETRY
