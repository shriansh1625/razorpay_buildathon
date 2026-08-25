"""Deterministic diagnosis rules — action-agnostic candidate cause ranking."""

from __future__ import annotations

from revive.domain.enums import CauseCode, ConfidenceBand, RiskClass
from revive.recovery.context.models import ContextObject
from revive.recovery.diagnosis.mapping import map_raw_reason
from revive.recovery.diagnosis.models import RankedCause
from revive.recovery.sentinel.models import DetectedOpportunity


def _refs_from_context(context: ContextObject) -> tuple[str, ...]:
    return tuple(e.evidence_id for e in context.evidence)


def _rank(
    cause: CauseCode,
    band: ConfidenceBand,
    context: ContextObject,
    *,
    supporting: tuple[str, ...] = (),
    contradicting: tuple[str, ...] = (),
    extra_refs: tuple[str, ...] = (),
) -> RankedCause:
    refs = tuple(dict.fromkeys(_refs_from_context(context) + extra_refs))
    if not refs:
        refs = (f"ctx:{context.opportunity_id}",)
    return RankedCause(
        cause_code=cause,
        confidence_band=band,
        evidence_refs=refs,
        supporting_features=supporting,
        contradicting_features=contradicting,
    )


def _payment_failure_causes(
    opportunity: DetectedOpportunity,
    context: ContextObject,
) -> tuple[RankedCause, ...]:
    payment = context.payment
    if payment is None:
        return (_rank(CauseCode.UNCLASSIFIED, ConfidenceBand.LOW, context),)

    mapped = map_raw_reason(payment.reason_code)
    supporting: list[str] = []
    contradicting: list[str] = []
    causes: list[RankedCause] = []

    if mapped != CauseCode.UNCLASSIFIED:
        band = ConfidenceBand.HIGH
        supporting.append("reason_code")
        causes.append(
            _rank(mapped, band, context, supporting=tuple(supporting), contradicting=tuple(contradicting))
        )
    else:
        causes.append(_rank(CauseCode.UNCLASSIFIED, ConfidenceBand.LOW, context))

    if opportunity.degradation_flag or payment.merchant_degradation_observed:
        deg_support = ("observed_failure_rate", "degradation_flag")
        deg_contra: list[str] = []
        if context.instrument and context.instrument.instrument_success_rate is not None:
            if (
                context.instrument.instrument_success_rate >= 0.7
                and context.instrument.instrument_success_count >= 3
            ):
                deg_contra.append("instrument_success_rate")
        causes.insert(
            0,
            _rank(
                CauseCode.ISSUER_DOWNTIME,
                ConfidenceBand.MED if deg_contra else ConfidenceBand.HIGH,
                context,
                supporting=deg_support,
                contradicting=tuple(deg_contra),
            ),
        )

    if payment.failure_cluster_size >= 3 and not opportunity.degradation_flag:
        causes.append(
            _rank(
                CauseCode.DO_NOT_HONOUR_AMBIGUOUS,
                ConfidenceBand.LOW,
                context,
                supporting=("failure_cluster_size",),
            )
        )

    if context.instrument and context.instrument.block_state == "BLOCKED":
        causes.insert(
            0,
            _rank(
                CauseCode.INSTRUMENT_BLOCKED,
                ConfidenceBand.HIGH,
                context,
                supporting=("block_state",),
            ),
        )

    # Deduplicate by cause_code preserving first rank order.
    seen: set[CauseCode] = set()
    unique: list[RankedCause] = []
    for cause in causes:
        if cause.cause_code in seen:
            continue
        seen.add(cause.cause_code)
        unique.append(cause)
    return tuple(unique)


def _checkout_causes(context: ContextObject) -> tuple[RankedCause, ...]:
    checkout = context.checkout
    if checkout is None:
        return (_rank(CauseCode.UNCLASSIFIED, ConfidenceBand.LOW, context),)

    causes: list[RankedCause] = []
    stage = checkout.stage_reached or ""
    if checkout.payment_initiated:
        causes.append(
            _rank(
                CauseCode.AUTH_ABANDONED_BY_CUSTOMER,
                ConfidenceBand.MED,
                context,
                supporting=("stage_reached", "payment_initiated"),
            )
        )
    elif stage in {"CART", "CHECKOUT"}:
        causes.append(
            _rank(
                CauseCode.CHECKOUT_STEP_FRICTION,
                ConfidenceBand.MED,
                context,
                supporting=("stage_reached",),
            )
        )
    else:
        causes.append(
            _rank(
                CauseCode.SESSION_INTERRUPTED,
                ConfidenceBand.LOW,
                context,
                supporting=("stage_reached",),
            )
        )

    if checkout.prior_abandonment_count >= 2:
        causes.append(
            _rank(
                CauseCode.CHECKOUT_STEP_FRICTION,
                ConfidenceBand.MED,
                context,
                supporting=("prior_abandonment_count",),
            )
        )

    if checkout.cart_value_paise and checkout.cart_value_paise >= 50000:
        causes.append(
            _rank(
                CauseCode.PRICE_OR_FEE_HESITATION,
                ConfidenceBand.LOW,
                context,
                supporting=("cart_value_paise",),
            )
        )

    seen: set[CauseCode] = set()
    unique: list[RankedCause] = []
    for cause in causes:
        if cause.cause_code in seen:
            continue
        seen.add(cause.cause_code)
        unique.append(cause)
    return tuple(unique)


def _subscription_causes(context: ContextObject) -> tuple[RankedCause, ...]:
    sub = context.subscription
    if sub is None:
        return (_rank(CauseCode.UNCLASSIFIED, ConfidenceBand.LOW, context),)

    mandate_state = (sub.mandate_state or "").upper()
    if mandate_state == "REVOKED":
        return (
            _rank(
                CauseCode.MANDATE_REVOKED,
                ConfidenceBand.HIGH,
                context,
                supporting=("mandate_state",),
            ),
        )
    if mandate_state in {"EXPIRED", "EXPIRING"}:
        return (
            _rank(
                CauseCode.MANDATE_EXPIRED,
                ConfidenceBand.HIGH,
                context,
                supporting=("mandate_state",),
            ),
        )
    if sub.failed_debit_count >= 2:
        return (
            _rank(
                CauseCode.INSUFFICIENT_FUNDS,
                ConfidenceBand.MED,
                context,
                supporting=("failed_debit_count",),
            ),
            _rank(
                CauseCode.ISSUER_DOWNTIME,
                ConfidenceBand.LOW,
                context,
                supporting=("failed_debit_count",),
            ),
        )
    return (
        _rank(
            CauseCode.MANDATE_NOT_PRESENTED,
            ConfidenceBand.LOW,
            context,
            supporting=("subscription_state",),
        ),
    )


def _receivable_causes(context: ContextObject) -> tuple[RankedCause, ...]:
    recv = context.receivable
    if recv is None:
        return (_rank(CauseCode.UNCLASSIFIED, ConfidenceBand.LOW, context),)

    if recv.disputed_amount_paise > 0:
        return (
            _rank(
                CauseCode.QUERY_OR_DISPUTE_RAISED,
                ConfidenceBand.HIGH,
                context,
                supporting=("disputed_amount_paise",),
            ),
        )

    ageing = recv.ageing_days or 0
    if ageing <= 15:
        primary = CauseCode.OVERSIGHT_OR_FORGOTTEN
        band = ConfidenceBand.LOW
    elif ageing <= 30:
        primary = CauseCode.BUYER_CASHFLOW_CONSTRAINT
        band = ConfidenceBand.MED
    else:
        primary = CauseCode.BUYER_CASHFLOW_CONSTRAINT
        band = ConfidenceBand.HIGH

    causes: list[RankedCause] = [
        _rank(
            primary,
            band,
            context,
            supporting=("ageing_days", "ageing_bucket"),
        )
    ]
    if recv.prior_overdue_count >= 2:
        causes.append(
            _rank(
                CauseCode.BUYER_CASHFLOW_CONSTRAINT,
                ConfidenceBand.MED,
                context,
                supporting=("prior_overdue_count",),
            )
        )
    return tuple(causes)


def _mandate_causes(context: ContextObject) -> tuple[RankedCause, ...]:
    sub = context.subscription
    if sub is None:
        return (_rank(CauseCode.UNCLASSIFIED, ConfidenceBand.LOW, context),)
    state = (sub.mandate_state or "").upper()
    if state == "REVOKED":
        return (
            _rank(
                CauseCode.MANDATE_REVOKED,
                ConfidenceBand.HIGH,
                context,
                supporting=("mandate_state",),
            ),
        )
    return (
        _rank(
            CauseCode.MANDATE_EXPIRED,
            ConfidenceBand.HIGH,
            context,
            supporting=("mandate_state", "mandate_expires_at_micros"),
        ),
    )


def _ambiguous_causes(context: ContextObject) -> tuple[RankedCause, ...]:
    return (
        _rank(
            CauseCode.UNCLASSIFIED,
            ConfidenceBand.LOW,
            context,
            supporting=("insufficient_evidence",),
        ),
    )


def rank_causes(
    opportunity: DetectedOpportunity,
    context: ContextObject,
) -> tuple[RankedCause, ...]:
    if opportunity.risk_class == RiskClass.PAYMENT_FAILURE:
        return _payment_failure_causes(opportunity, context)
    if opportunity.risk_class == RiskClass.CHECKOUT_ABANDONMENT:
        return _checkout_causes(context)
    if opportunity.risk_class == RiskClass.SUBSCRIPTION_FAILURE:
        return _subscription_causes(context)
    if opportunity.risk_class == RiskClass.RECEIVABLE_OVERDUE:
        return _receivable_causes(context)
    if opportunity.risk_class == RiskClass.MANDATE_HEALTH:
        return _mandate_causes(context)
    return _ambiguous_causes(context)
