"""Revenue Sentinel — detect revenue-at-risk from observable state (C-02)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from revive.domain.enums import RiskClass
from revive.recovery.sentinel.addressability import ageing_bucket_days, classify_addressability
from revive.recovery.sentinel.config import SentinelConfig, default_sentinel_config
from revive.recovery.sentinel.degradation import detect_degraded_cohorts
from revive.recovery.sentinel.identity import (
    natural_key_checkout,
    natural_key_mandate,
    natural_key_payment,
    natural_key_receivable,
    natural_key_subscription,
    opportunity_id_for,
)
from revive.recovery.sentinel.metrics import compute_metrics
from revive.recovery.sentinel.models import (
    DetectedOpportunity,
    EvidenceRecord,
    SentinelResult,
)
from revive.recovery.sentinel.signals import ingest_signals
from revive.recovery.sentinel.valuation import (
    checkout_value_paise,
    compute_value_at_risk,
    receivable_outstanding_paise,
    subscription_value_paise,
)
from revive.simulation.observation import ObservableWorldView

MINUTE_MICROS = 60 * 1_000_000
DAY_MICROS = 24 * 60 * 60 * 1_000_000

_CHECKOUT_RISK_STAGES = frozenset(
    {"CART", "CHECKOUT", "PAYMENT_INIT", "PAYMENT_ATTEMPT"}
)
_SETTLED_STATUSES = frozenset({"SUCCESS", "PAID", "SETTLED", "CAPTURED"})


@dataclass
class _Draft:
    risk_class: RiskClass
    natural_key: str
    merchant_id: str
    customer_id: str | None
    gross_paise: int
    first_detected_at_micros: int
    attempt_seq: int = 1
    linked_refs: dict[str, str] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)
    signal_ids: list[str] = field(default_factory=list)
    invoice: dict | None = None
    subscription: dict | None = None
    method_type: str | None = None
    disputed: bool = False
    written_off: bool = False
    already_settled: bool = False
    amount_determinable: bool = True
    secondary_class: RiskClass | None = None


def detect(
    view: ObservableWorldView,
    now_micros: int,
    config: SentinelConfig | None = None,
) -> SentinelResult:
    """Detect opportunities from observable world at virtual time `now_micros`."""
    cfg = config or default_sentinel_config()
    accepted, quarantined, _future = ingest_signals(view.signals, now_micros)

    drafts: dict[str, _Draft] = {}
    dedupe_merges = 0

    def merge(draft: _Draft) -> None:
        nonlocal dedupe_merges
        existing = drafts.get(draft.natural_key)
        if existing is None:
            drafts[draft.natural_key] = draft
            return
        dedupe_merges += 1
        existing.attempt_seq = max(existing.attempt_seq, draft.attempt_seq)
        existing.first_detected_at_micros = min(
            existing.first_detected_at_micros, draft.first_detected_at_micros
        )
        existing.gross_paise = max(existing.gross_paise, draft.gross_paise)
        existing.linked_refs.update(draft.linked_refs)
        existing.facts.update(draft.facts)
        existing.signal_ids.extend(draft.signal_ids)
        if existing.secondary_class is None and draft.risk_class != existing.risk_class:
            existing.secondary_class = draft.risk_class

    for txn in view.transactions:
        attempted = int(txn.get("attempted_at_micros") or 0)
        if attempted > now_micros:
            continue
        status = str(txn.get("status") or "").upper()
        order_id = str(txn.get("order_id") or "")
        customer_id = txn.get("customer_id")
        if not order_id or not customer_id:
            continue
        if status in _SETTLED_STATUSES:
            key = natural_key_payment(customer_id=str(customer_id), order_id=order_id)
            if key in drafts:
                drafts[key].already_settled = True
                drafts[key].gross_paise = 0
            continue
        if status != "FAILED":
            continue
        amount = int(txn.get("amount_paise") or 0)
        merchant_id = _merchant_for_order(view, order_id) or _first_merchant(view)
        merge(
            _Draft(
                risk_class=RiskClass.PAYMENT_FAILURE,
                natural_key=natural_key_payment(customer_id=str(customer_id), order_id=order_id),
                merchant_id=merchant_id,
                customer_id=str(customer_id),
                gross_paise=amount,
                first_detected_at_micros=attempted,
                attempt_seq=int(txn.get("attempt_seq") or 1),
                linked_refs={"order_id": order_id, "transaction_id": str(txn.get("transaction_id") or "")},
                facts={
                    "failure_reason": txn.get("reason_code"),
                    "method_type": txn.get("method_type"),
                    "gross_amount_paise": amount,
                },
                method_type=str(txn.get("method_type") or "") or None,
            )
        )

    for session in view.checkout_sessions:
        abandoned_at = session.get("abandoned_at_micros")
        if abandoned_at is None:
            continue
        abandoned_at = int(abandoned_at)
        if abandoned_at > now_micros:
            continue
        stage = str(session.get("stage_reached") or "")
        if stage not in _CHECKOUT_RISK_STAGES:
            continue
        cart = checkout_value_paise(session)
        session_id = str(session.get("session_id") or "")
        customer_id = session.get("customer_id")
        identity = str(customer_id) if customer_id else session_id
        if not session_id:
            continue
        merge(
            _Draft(
                risk_class=RiskClass.CHECKOUT_ABANDONMENT,
                natural_key=natural_key_checkout(identity=identity, cart_fingerprint=session_id),
                merchant_id=str(session.get("merchant_id") or _first_merchant(view)),
                customer_id=str(customer_id) if customer_id else None,
                gross_paise=cart or 0,
                first_detected_at_micros=abandoned_at,
                linked_refs={"checkout_session_id": session_id},
                facts={
                    "checkout_stage": stage,
                    "cart_value_paise": cart,
                    "method_selected": session.get("method_selected"),
                },
                amount_determinable=cart is not None,
            )
        )

    for sub in view.subscriptions:
        next_charge = int(sub.get("next_charge_at_micros") or 0)
        state = str(sub.get("state") or "")
        if state != "PAST_DUE" and next_charge > now_micros:
            continue
        if next_charge > now_micros and state != "PAST_DUE":
            continue
        detected_at = min(next_charge, now_micros) if next_charge else now_micros
        if detected_at > now_micros:
            continue
        sub_id = str(sub.get("subscription_id") or "")
        cycle = int(sub.get("cycle_number") or 0)
        if not sub_id:
            continue
        value = subscription_value_paise(sub, cfg)
        merge(
            _Draft(
                risk_class=RiskClass.SUBSCRIPTION_FAILURE,
                natural_key=natural_key_subscription(subscription_id=sub_id, cycle_number=cycle),
                merchant_id=_first_merchant(view),
                customer_id=str(sub.get("customer_id") or "") or None,
                gross_paise=value,
                first_detected_at_micros=detected_at,
                linked_refs={
                    "subscription_id": sub_id,
                    "mandate_id": str(sub.get("mandate_id") or ""),
                },
                facts={"cycle_number": cycle, "subscription_state": state},
                subscription=dict(sub),
            )
        )

    for invoice in view.invoices:
        due_at = int(invoice.get("due_at_micros") or 0)
        if due_at > now_micros:
            continue
        outstanding = receivable_outstanding_paise(invoice)
        invoice_id = str(invoice.get("invoice_id") or "")
        if not invoice_id:
            continue
        state = str(invoice.get("state") or "")
        disputed = int(invoice.get("disputed_amount_paise") or 0) > 0 or state == "DISPUTED"
        written_off = int(invoice.get("written_off_amount_paise") or 0) > 0 and outstanding == 0
        already_settled = outstanding == 0 and int(invoice.get("paid_amount_paise") or 0) > 0
        if outstanding == 0 and not already_settled and not written_off and not disputed:
            continue
        if outstanding == 0 and already_settled:
            continue
        detected_at = due_at
        merge(
            _Draft(
                risk_class=RiskClass.RECEIVABLE_OVERDUE,
                natural_key=natural_key_receivable(invoice_id=invoice_id),
                merchant_id=str(invoice.get("merchant_id") or _first_merchant(view)),
                customer_id=str(invoice.get("customer_id") or "") or None,
                gross_paise=outstanding,
                first_detected_at_micros=detected_at,
                linked_refs={"invoice_id": invoice_id},
                facts={
                    "issued_amount_paise": invoice.get("issued_amount_paise"),
                    "outstanding_paise": outstanding,
                    "ageing_days": invoice.get("ageing_days"),
                },
                invoice=dict(invoice),
                disputed=disputed and outstanding == 0,
                written_off=written_off,
                already_settled=already_settled,
            )
        )

    billing_window = cfg.mandate_billing_window_minutes * MINUTE_MICROS
    mandate_ids_in_subs = {
        str(s.get("mandate_id") or "") for s in view.subscriptions if s.get("mandate_id")
    }
    for mandate in view.mandates:
        mandate_id = str(mandate.get("mandate_id") or "")
        if not mandate_id:
            continue
        expires_at = int(mandate.get("expires_at_micros") or 0)
        state = str(mandate.get("state") or "")
        near_expiry = 0 < expires_at <= now_micros + billing_window
        if state not in {"EXPIRING", "REVOKED", "EXPIRED"} and not near_expiry:
            continue
        if mandate_id in mandate_ids_in_subs and state not in {"EXPIRING", "REVOKED", "EXPIRED"}:
            continue
        if expires_at > now_micros + billing_window and state not in {"EXPIRING", "REVOKED"}:
            continue
        detected_at = min(expires_at, now_micros) if expires_at else now_micros
        if detected_at > now_micros:
            detected_at = now_micros
        next_charge_token = str(expires_at)
        merge(
            _Draft(
                risk_class=RiskClass.MANDATE_HEALTH,
                natural_key=natural_key_mandate(
                    mandate_id=mandate_id, next_charge_date=next_charge_token
                ),
                merchant_id=_first_merchant(view),
                customer_id=str(mandate.get("customer_id") or "") or None,
                gross_paise=int(mandate.get("max_amount_paise") or 0),
                first_detected_at_micros=detected_at,
                linked_refs={"mandate_id": mandate_id},
                facts={"mandate_state": state, "expires_at_micros": expires_at},
            )
        )

    _attach_signals(drafts, accepted)

    degraded_methods = detect_degraded_cohorts(list(view.transactions), now_micros, cfg)

    opportunities: list[DetectedOpportunity] = []
    for draft in drafts.values():
        value = compute_value_at_risk(
            draft.risk_class,
            gross_paise=draft.gross_paise,
            config=cfg,
            invoice=draft.invoice,
            subscription=draft.subscription,
        )
        window_minutes = cfg.window_minutes(draft.risk_class)
        expires_at = draft.first_detected_at_micros + window_minutes * MINUTE_MICROS
        window_expired = now_micros >= expires_at
        addressable, reason, state = classify_addressability(
            risk_class=draft.risk_class,
            value_at_risk_paise=value,
            customer_id=draft.customer_id,
            window_expired=window_expired,
            disputed=draft.disputed,
            written_off=draft.written_off,
            already_settled=draft.already_settled,
            amount_determinable=draft.amount_determinable,
        )
        ageing = None
        if draft.risk_class == RiskClass.RECEIVABLE_OVERDUE:
            age_days = int((now_micros - draft.first_detected_at_micros) // DAY_MICROS)
            if draft.facts.get("ageing_days") is not None:
                age_days = int(draft.facts["ageing_days"])
            ageing = ageing_bucket_days(age_days)
        degradation_flag = bool(
            draft.method_type and draft.method_type in degraded_methods
        )
        opportunities.append(
            DetectedOpportunity(
                opportunity_id=opportunity_id_for(draft.natural_key),
                merchant_id=draft.merchant_id,
                customer_id=draft.customer_id,
                risk_class=draft.risk_class,
                natural_key=draft.natural_key,
                value_at_risk_paise=value,
                original_value_paise=draft.gross_paise,
                continuation_value_paise=(
                    int(cfg.continuation_factor * (draft.subscription or {}).get("cycle_amount_paise", 0))
                    if draft.subscription
                    else 0
                ),
                addressable=addressable,
                non_addressable_reason=reason,
                state=state,
                first_detected_at_micros=draft.first_detected_at_micros,
                recovery_window_expires_at_micros=expires_at,
                attempt_seq=draft.attempt_seq,
                ageing_bucket=ageing,
                degradation_flag=degradation_flag,
                evidence=EvidenceRecord(
                    signal_ids=tuple(draft.signal_ids),
                    source_refs=dict(draft.linked_refs),
                    facts=dict(draft.facts),
                ),
                detector_version=cfg.detector_version,
                secondary_class=draft.secondary_class,
            )
        )

    opportunities.sort(key=lambda o: o.opportunity_id)
    metrics = compute_metrics(
        opportunities,
        quarantined,
        signals_ingested=len(view.signals),
        dedupe_merges=dedupe_merges,
        detector_version=cfg.detector_version,
    )
    return SentinelResult(
        opportunities=tuple(opportunities),
        quarantined=tuple(quarantined),
        metrics=metrics,
        now_micros=now_micros,
    )


def _attach_signals(drafts: dict[str, _Draft], signals: list[dict[str, Any]]) -> None:
    by_source: dict[str, list[str]] = defaultdict(list)
    for sig in signals:
        source = str(sig.get("source_ref") or "")
        if source:
            by_source[source].append(str(sig.get("signal_id")))
    for draft in drafts.values():
        for ref in draft.linked_refs.values():
            if ref in by_source:
                draft.signal_ids.extend(by_source[ref])
        # Generator signals use opportunity_id as source_ref; ignore that identity.


def _merchant_for_order(view: ObservableWorldView, order_id: str) -> str | None:
    for order in view.orders:
        if order.get("order_id") == order_id:
            return str(order.get("merchant_id") or "") or None
    return None


def _first_merchant(view: ObservableWorldView) -> str:
    if view.merchants:
        return str(view.merchants[0].get("merchant_id") or "mer_unknown")
    return "mer_unknown"
