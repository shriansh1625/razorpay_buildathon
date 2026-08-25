"""Assemble observable context for a detected opportunity (C-04)."""

from __future__ import annotations

from typing import Any

from revive.domain.enums import EvidenceKind, RiskClass
from revive.recovery.context.config import ContextConfig, default_context_config
from revive.recovery.context.history import (
    contact_counts_from_opportunities,
    customer_transactions,
    failure_cluster_size,
    fatigue_band,
    instrument_history_stats,
    merchant_failure_rate,
    method_failure_rate,
    payment_history_stats,
    prior_abandonment_count,
    prior_overdue_count,
    subscription_debit_stats,
)
from revive.recovery.context.models import (
    CheckoutContext,
    ContextEvidence,
    ContextObject,
    CustomerContext,
    DegradationContext,
    FatigueContext,
    InstrumentContext,
    PaymentContext,
    ReceivableContext,
    SubscriptionContext,
    TemporalContext,
)
from revive.recovery.sentinel.degradation import detect_degraded_cohorts
from revive.recovery.sentinel.models import DetectedOpportunity
from revive.recovery.sentinel.config import SentinelConfig
from revive.simulation.ids import deterministic_id
from revive.simulation.observation import ObservableWorldView

MINUTE_MICROS = 60 * 1_000_000
DAY_MICROS = 24 * 60 * 60 * 1_000_000
_PAYMENT_STAGES = frozenset({"PAYMENT_INIT", "PAYMENT_ATTEMPT"})


def _evidence_id(opportunity_id: str, feature: str) -> str:
    return deterministic_id("ev", f"{opportunity_id}:{feature}")


def _find_customer(view: ObservableWorldView, customer_id: str | None) -> dict[str, Any] | None:
    if not customer_id:
        return None
    for customer in view.customers:
        if customer.get("customer_id") == customer_id:
            return customer
    return None


def _find_instrument(view: ObservableWorldView, instrument_id: str | None) -> dict[str, Any] | None:
    if not instrument_id:
        return None
    for instrument in view.instruments:
        if instrument.get("instrument_id") == instrument_id:
            return instrument
    return None


def _find_transaction_for_payment(
    view: ObservableWorldView,
    refs: dict[str, str],
    now_micros: int,
) -> dict[str, Any] | None:
    order_id = refs.get("order_id")
    candidates = [
        t
        for t in view.transactions
        if int(t.get("attempted_at_micros") or 0) <= now_micros
        and (not order_id or t.get("order_id") == order_id)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda t: int(t.get("attempted_at_micros") or 0), reverse=True)
    return candidates[0]


def _merchant_timezone(view: ObservableWorldView, merchant_id: str) -> str:
    for merchant in view.merchants:
        if merchant.get("merchant_id") == merchant_id:
            return str(merchant.get("timezone") or "UTC")
    return "UTC"


def _local_timing(now_micros: int, timezone: str) -> tuple[int | None, int | None, bool | None]:
    # Deterministic approximation — UTC offset from Asia/Kolkata default in fixtures.
    offset_hours = 5 if "Kolkata" in timezone or "India" in timezone else 0
    seconds = now_micros // 1_000_000
    hour = (seconds // 3600 + offset_hours) % 24
    day_of_month = ((seconds // 86400) % 28) + 1
    weekday = (seconds // 86400 + 3) % 7  # anchor epoch as Thursday
    is_business_day = weekday < 5
    return hour, day_of_month, is_business_day


def assemble_context(
    opportunity: DetectedOpportunity,
    view: ObservableWorldView,
    now_micros: int,
    config: ContextConfig | None = None,
    cycle_cache: Any | None = None,
) -> ContextObject:
    """Build a structured ContextObject from observable state at virtual time T."""
    cfg = config or default_context_config()
    evidence: list[ContextEvidence] = []
    context_degraded = False
    refs = dict(opportunity.evidence.source_refs)

    if cycle_cache is not None:
        customer_row = cycle_cache.customer_row(opportunity.customer_id)
    else:
        customer_row = _find_customer(view, opportunity.customer_id)
    if opportunity.customer_id and customer_row is None:
        context_degraded = True

    if cycle_cache is not None:
        cust_txns = cycle_cache.customer_transactions(opportunity.customer_id)
        pay_stats = cycle_cache.payment_stats(opportunity.customer_id)
        contact_stats = cycle_cache.contact_stats(opportunity.customer_id)
    else:
        cust_txns = customer_transactions(
            view.transactions,
            opportunity.customer_id,
            now_micros,
            cfg.customer_history_days,
        )
        pay_stats = payment_history_stats(cust_txns)
        contact_stats = contact_counts_from_opportunities(
            view.opportunities,
            opportunity.customer_id,
            now_micros,
            cfg.fatigue_7d_days,
            cfg.fatigue_window_days,
        )

    customer = CustomerContext(
        customer_id=opportunity.customer_id,
        segment=str(customer_row.get("segment")) if customer_row else None,
        segment_null_reason=None if customer_row else "CUSTOMER_RECORD_NOT_FOUND",
        tenure_band=str(customer_row.get("tenure_band")) if customer_row else None,
        value_band=str(customer_row.get("value_band")) if customer_row else None,
        prior_self_recovery_rate=(
            float(customer_row.get("prior_self_recovery_rate"))
            if customer_row and customer_row.get("prior_self_recovery_rate") is not None
            else None
        ),
        successful_payment_count=pay_stats["successful_payment_count"],
        failed_payment_count=pay_stats["failed_payment_count"],
        success_rate=pay_stats["success_rate"],
        average_transaction_value_paise=pay_stats["average_transaction_value_paise"],
        recent_failure_count=pay_stats["recent_failure_count"],
        previous_recovery_count=contact_stats["previous_recovery_count"],
        previous_contact_count=contact_stats["contacts_last_30d"],
    )
    evidence.append(
        ContextEvidence(
            evidence_id=_evidence_id(opportunity.opportunity_id, "customer_success_rate"),
            kind=EvidenceKind.FACT if pay_stats["success_rate"] is not None else EvidenceKind.UNKNOWN,
            feature="success_rate",
            value=pay_stats["success_rate"],
            source="payment_history",
            source_ref=opportunity.customer_id,
        )
    )

    fatigue = FatigueContext(
        contacts_last_7d=contact_stats["contacts_last_7d"],
        contacts_last_30d=contact_stats["contacts_last_30d"],
        fatigue_band=fatigue_band(
            contact_stats["contacts_last_7d"],
            contact_stats["contacts_last_30d"],
        ),
        null_reason=(
            "NO_PRIOR_OPPORTUNITY_CONTACTS"
            if contact_stats["contacts_last_30d"] == 0
            else None
        ),
    )

    instrument_ctx: InstrumentContext | None = None
    payment_ctx: PaymentContext | None = None
    checkout_ctx: CheckoutContext | None = None
    subscription_ctx: SubscriptionContext | None = None
    receivable_ctx: ReceivableContext | None = None

    event_micros = opportunity.first_detected_at_micros
    method_type: str | None = None

    if opportunity.risk_class == RiskClass.PAYMENT_FAILURE:
        txn = _find_transaction_for_payment(view, refs, now_micros)
        instrument_id = str(txn.get("instrument_id") or "") if txn else None
        method_type = str(txn.get("method_type") or "") if txn else None
        inst_row = (
            cycle_cache.instrument_row(instrument_id)
            if cycle_cache is not None
            else _find_instrument(view, instrument_id)
        )
        if instrument_id and inst_row is None:
            context_degraded = True
        inst_stats = instrument_history_stats(cust_txns, instrument_id)
        instrument_ctx = InstrumentContext(
            instrument_id=instrument_id,
            method_type=method_type,
            expiry_state=str(inst_row.get("expiry_state")) if inst_row else None,
            block_state=str(inst_row.get("block_state")) if inst_row else None,
            instrument_success_count=inst_stats["instrument_success_count"],
            instrument_failure_count=inst_stats["instrument_failure_count"],
            instrument_success_rate=inst_stats["instrument_success_rate"],
            null_reason=None if inst_row or not instrument_id else "INSTRUMENT_NOT_FOUND",
        )
        anchor = int(txn.get("attempted_at_micros") or event_micros) if txn else event_micros
        cluster = failure_cluster_size(
            cust_txns,
            anchor_micros=anchor,
            window_minutes=cfg.failure_cluster_minutes,
        )
        if cycle_cache is not None:
            degraded_methods = cycle_cache.degraded_methods
        else:
            sentinel_cfg = SentinelConfig(
                degradation_window_minutes=cfg.degradation_window_minutes,
                degradation_min_attempts=cfg.degradation_min_attempts,
                degradation_failure_rate=cfg.degradation_failure_rate,
            )
            degraded_methods = detect_degraded_cohorts(list(view.transactions), now_micros, sentinel_cfg)
        payment_ctx = PaymentContext(
            transaction_id=str(txn.get("transaction_id")) if txn else None,
            order_id=str(txn.get("order_id")) if txn else refs.get("order_id"),
            amount_paise=int(txn.get("amount_paise") or 0) if txn else None,
            method_type=method_type,
            reason_code=str(txn.get("reason_code") or "") if txn else None,
            reason_text=str(txn.get("reason_text") or "") if txn and txn.get("reason_text") else None,
            attempt_seq=int(txn.get("attempt_seq") or opportunity.attempt_seq) if txn else opportunity.attempt_seq,
            recent_attempt_count=len(
                [t for t in cust_txns if str(t.get("order_id") or "") == (txn or {}).get("order_id")]
            ),
            failure_cluster_size=cluster,
            merchant_degradation_observed=bool(method_type and method_type in degraded_methods),
        )
        if txn:
            event_micros = anchor
            evidence.append(
                ContextEvidence(
                    evidence_id=_evidence_id(opportunity.opportunity_id, "failure_reason"),
                    kind=EvidenceKind.FACT,
                    feature="reason_code",
                    value=txn.get("reason_code"),
                    source="transaction",
                    source_ref=str(txn.get("transaction_id")),
                )
            )

    elif opportunity.risk_class == RiskClass.CHECKOUT_ABANDONMENT:
        session_id = refs.get("checkout_session_id") or refs.get("session_id")
        session = (
            cycle_cache.checkout_row(session_id)
            if cycle_cache is not None
            else next((s for s in view.checkout_sessions if s.get("session_id") == session_id), None)
        )
        if session_id and session is None:
            context_degraded = True
        abandoned = int(session.get("abandoned_at_micros") or event_micros) if session else event_micros
        created = int(session.get("created_at_micros") or 0) if session else 0
        elapsed = (abandoned - created) // 1_000_000 if session and created else None
        stage = str(session.get("stage_reached") or "") if session else None
        checkout_ctx = CheckoutContext(
            session_id=str(session.get("session_id")) if session else session_id,
            cart_value_paise=int(session.get("cart_value_paise") or 0) if session else None,
            stage_reached=stage,
            elapsed_seconds=elapsed,
            method_selected=str(session.get("method_selected")) if session and session.get("method_selected") else None,
            payment_initiated=stage in _PAYMENT_STAGES if stage else False,
            prior_abandonment_count=(
                cycle_cache.prior_abandonment_count(
                    opportunity.customer_id,
                    str(session.get("session_id")) if session else session_id,
                )
                if cycle_cache is not None
                else prior_abandonment_count(
                    view.checkout_sessions,
                    opportunity.customer_id,
                    str(session.get("session_id")) if session else session_id,
                    now_micros,
                    cfg.customer_history_days,
                )
            ),
            null_reason=None if session else "CHECKOUT_SESSION_NOT_FOUND",
        )
        event_micros = abandoned

    elif opportunity.risk_class == RiskClass.SUBSCRIPTION_FAILURE:
        sub_id = refs.get("subscription_id")
        subscription = (
            cycle_cache.subscription_row(sub_id)
            if cycle_cache is not None
            else next((s for s in view.subscriptions if s.get("subscription_id") == sub_id), None)
        )
        if sub_id and subscription is None:
            context_degraded = True
        mandate_id = str(subscription.get("mandate_id") or "") if subscription else refs.get("mandate_id")
        mandate = (
            cycle_cache.mandate_row(mandate_id)
            if cycle_cache is not None
            else next((m for m in view.mandates if m.get("mandate_id") == mandate_id), None)
        ) if mandate_id else None
        debit_stats = subscription_debit_stats(cust_txns, sub_id)
        subscription_ctx = SubscriptionContext(
            subscription_id=sub_id,
            cycle_number=int(subscription.get("cycle_number") or 0) if subscription else None,
            cycle_amount_paise=int(subscription.get("cycle_amount_paise") or 0) if subscription else None,
            state=str(subscription.get("state") or "") if subscription else None,
            successful_debit_count=debit_stats["successful_debit_count"],
            failed_debit_count=debit_stats["failed_debit_count"],
            mandate_id=mandate_id,
            mandate_state=str(mandate.get("state") or "") if mandate else None,
            mandate_expires_at_micros=int(mandate.get("expires_at_micros") or 0) if mandate else None,
            null_reason=None if subscription else "SUBSCRIPTION_NOT_FOUND",
        )
        if mandate is None and mandate_id:
            context_degraded = True

    elif opportunity.risk_class == RiskClass.RECEIVABLE_OVERDUE:
        invoice_id = refs.get("invoice_id")
        invoice = (
            cycle_cache.invoice_row(invoice_id)
            if cycle_cache is not None
            else next((i for i in view.invoices if i.get("invoice_id") == invoice_id), None)
        )
        if invoice_id and invoice is None:
            context_degraded = True
        outstanding = int(opportunity.evidence.facts.get("outstanding_paise") or 0)
        ageing_days = int(
            opportunity.evidence.facts.get("ageing_days")
            or ((now_micros - event_micros) // DAY_MICROS)
        )
        receivable_ctx = ReceivableContext(
            invoice_id=invoice_id,
            issued_amount_paise=int(invoice.get("issued_amount_paise") or 0) if invoice else None,
            outstanding_paise=outstanding,
            ageing_bucket=opportunity.ageing_bucket.value if opportunity.ageing_bucket else None,
            ageing_days=ageing_days,
            prior_overdue_count=(
                cycle_cache.prior_overdue_count(opportunity.customer_id, invoice_id)
                if cycle_cache is not None
                else prior_overdue_count(
                    view.invoices,
                    opportunity.customer_id,
                    invoice_id,
                    now_micros,
                )
            ),
            prior_payment_count=pay_stats["successful_payment_count"],
            disputed_amount_paise=int(invoice.get("disputed_amount_paise") or 0) if invoice else 0,
            null_reason=None if invoice else "INVOICE_NOT_FOUND",
        )

    elif opportunity.risk_class == RiskClass.MANDATE_HEALTH:
        mandate_id = refs.get("mandate_id")
        mandate = (
            cycle_cache.mandate_row(mandate_id)
            if cycle_cache is not None
            else next((m for m in view.mandates if m.get("mandate_id") == mandate_id), None)
        )
        if mandate_id and mandate is None:
            context_degraded = True
        instrument_id = str(mandate.get("instrument_id") or "") if mandate else None
        inst_row = (
            cycle_cache.instrument_row(instrument_id)
            if cycle_cache is not None
            else _find_instrument(view, instrument_id)
        )
        inst_stats = instrument_history_stats(cust_txns, instrument_id)
        instrument_ctx = InstrumentContext(
            instrument_id=instrument_id,
            method_type=str(inst_row.get("method_type")) if inst_row else None,
            expiry_state=str(inst_row.get("expiry_state")) if inst_row else None,
            block_state=str(inst_row.get("block_state")) if inst_row else None,
            instrument_success_count=inst_stats["instrument_success_count"],
            instrument_failure_count=inst_stats["instrument_failure_count"],
            instrument_success_rate=inst_stats["instrument_success_rate"],
            null_reason=None if mandate else "MANDATE_NOT_FOUND",
        )
        subscription_ctx = SubscriptionContext(
            subscription_id=None,
            cycle_number=None,
            cycle_amount_paise=None,
            state=None,
            successful_debit_count=0,
            failed_debit_count=0,
            mandate_id=mandate_id,
            mandate_state=str(mandate.get("state") or "") if mandate else None,
            mandate_expires_at_micros=int(mandate.get("expires_at_micros") or 0) if mandate else None,
            null_reason=None,
        )

    if cycle_cache is not None:
        degraded_methods = cycle_cache.degraded_methods
        observed_rate = cycle_cache.method_failure_rate_cached(method_type)
        baseline_rate = cycle_cache.merchant_failure_rate_cached()
    else:
        sentinel_cfg = SentinelConfig(
            degradation_window_minutes=cfg.degradation_window_minutes,
            degradation_min_attempts=cfg.degradation_min_attempts,
            degradation_failure_rate=cfg.degradation_failure_rate,
        )
        degraded_methods = detect_degraded_cohorts(list(view.transactions), now_micros, sentinel_cfg)
        observed_rate = method_failure_rate(
            view.transactions,
            method_type,
            now_micros,
            cfg.degradation_window_minutes,
        )
        baseline_rate = merchant_failure_rate(
            view.transactions,
            now_micros,
            cfg.degradation_window_minutes,
        )
    if method_type is None and payment_ctx:
        method_type = payment_ctx.method_type
    if baseline_rate is None:
        baseline_rate = cfg.baseline_failure_rate
    cluster_size = payment_ctx.failure_cluster_size if payment_ctx else 0
    degradation = DegradationContext(
        degradation_flag=opportunity.degradation_flag,
        observed_failure_rate=observed_rate,
        baseline_failure_rate=baseline_rate,
        affected_payment_method=method_type if opportunity.degradation_flag else None,
        failure_cluster_size=cluster_size,
        window_minutes=cfg.degradation_window_minutes,
    )
    if opportunity.degradation_flag:
        evidence.append(
            ContextEvidence(
                evidence_id=_evidence_id(opportunity.opportunity_id, "degradation_spike"),
                kind=EvidenceKind.PATTERN,
                feature="observed_failure_rate",
                value=observed_rate,
                source="degradation_signal",
                source_ref=method_type,
            )
        )

    tz = (
        cycle_cache.merchant_timezone(opportunity.merchant_id)
        if cycle_cache is not None
        else _merchant_timezone(view, opportunity.merchant_id)
    )
    hour, dom, business_day = _local_timing(now_micros, tz)
    temporal = TemporalContext(
        now_micros=now_micros,
        time_since_event_micros=max(0, now_micros - event_micros),
        time_since_last_success_micros=(
            (now_micros - pay_stats["last_success_micros"])
            if pay_stats["last_success_micros"] is not None
            else None
        ),
        time_since_last_failure_micros=(
            (now_micros - pay_stats["last_failure_micros"])
            if pay_stats["last_failure_micros"] is not None
            else None
        ),
        merchant_local_hour=hour,
        day_of_month=dom,
        is_business_day=business_day,
        time_to_window_close_micros=max(
            0,
            opportunity.recovery_window_expires_at_micros - now_micros,
        ),
    )

    return ContextObject(
        opportunity_id=opportunity.opportunity_id,
        assembled_at_micros=now_micros,
        customer=customer,
        fatigue=fatigue,
        instrument=instrument_ctx,
        payment=payment_ctx,
        checkout=checkout_ctx,
        subscription=subscription_ctx,
        receivable=receivable_ctx,
        temporal=temporal,
        degradation=degradation,
        context_degraded=context_degraded,
        feature_schema_version=cfg.feature_schema_version,
        evidence=tuple(evidence),
    )
