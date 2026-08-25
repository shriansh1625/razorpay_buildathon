"""Historical pattern features from observable transaction history."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

MINUTE_MICROS = 60 * 1_000_000
DAY_MICROS = 24 * 60 * 60 * 1_000_000


def customer_transactions(
    transactions: tuple[dict[str, Any], ...],
    customer_id: str | None,
    now_micros: int,
    history_days: int,
) -> list[dict[str, Any]]:
    if not customer_id:
        return []
    window_start = now_micros - history_days * DAY_MICROS
    rows: list[dict[str, Any]] = []
    for txn in transactions:
        if str(txn.get("customer_id") or "") != customer_id:
            continue
        attempted = int(txn.get("attempted_at_micros") or 0)
        if attempted > now_micros or attempted < window_start:
            continue
        rows.append(txn)
    rows.sort(key=lambda t: int(t.get("attempted_at_micros") or 0))
    return rows


def payment_history_stats(
    transactions: list[dict[str, Any]],
) -> dict[str, Any]:
    successes = [t for t in transactions if str(t.get("status") or "").upper() == "SUCCESS"]
    failures = [t for t in transactions if str(t.get("status") or "").upper() == "FAILED"]
    total = len(successes) + len(failures)
    success_rate = (len(successes) / total) if total else None
    amounts = [int(t.get("amount_paise") or 0) for t in successes + failures if t.get("amount_paise")]
    avg_amount = int(sum(amounts) / len(amounts)) if amounts else None
    return {
        "successful_payment_count": len(successes),
        "failed_payment_count": len(failures),
        "success_rate": success_rate,
        "average_transaction_value_paise": avg_amount,
        "recent_failure_count": len(failures),
        "last_success_micros": max((int(t["attempted_at_micros"]) for t in successes), default=None),
        "last_failure_micros": max((int(t["attempted_at_micros"]) for t in failures), default=None),
    }


def instrument_history_stats(
    transactions: list[dict[str, Any]],
    instrument_id: str | None,
) -> dict[str, Any]:
    if not instrument_id:
        return {
            "instrument_success_count": 0,
            "instrument_failure_count": 0,
            "instrument_success_rate": None,
        }
    scoped = [t for t in transactions if str(t.get("instrument_id") or "") == instrument_id]
    successes = sum(1 for t in scoped if str(t.get("status") or "").upper() == "SUCCESS")
    failures = sum(1 for t in scoped if str(t.get("status") or "").upper() == "FAILED")
    total = successes + failures
    return {
        "instrument_success_count": successes,
        "instrument_failure_count": failures,
        "instrument_success_rate": (successes / total) if total else None,
    }


def failure_cluster_size(
    transactions: list[dict[str, Any]],
    *,
    anchor_micros: int,
    window_minutes: int,
) -> int:
    window = window_minutes * MINUTE_MICROS
    start = anchor_micros - window
    failures = [
        t
        for t in transactions
        if str(t.get("status") or "").upper() == "FAILED"
        and start <= int(t.get("attempted_at_micros") or 0) <= anchor_micros
    ]
    return len(failures)


def merchant_failure_rate(
    transactions: tuple[dict[str, Any], ...],
    now_micros: int,
    window_minutes: int,
) -> float | None:
    window = window_minutes * MINUTE_MICROS
    window_start = now_micros - window
    attempts = [
        t
        for t in transactions
        if window_start <= int(t.get("attempted_at_micros") or 0) <= now_micros
    ]
    if not attempts:
        return None
    failures = sum(1 for t in attempts if str(t.get("status") or "").upper() == "FAILED")
    return failures / len(attempts)


def method_failure_rate(
    transactions: tuple[dict[str, Any], ...],
    method_type: str | None,
    now_micros: int,
    window_minutes: int,
) -> float | None:
    if not method_type:
        return None
    window = window_minutes * MINUTE_MICROS
    window_start = now_micros - window
    attempts = [
        t
        for t in transactions
        if str(t.get("method_type") or "") == method_type
        and window_start <= int(t.get("attempted_at_micros") or 0) <= now_micros
    ]
    if not attempts:
        return None
    failures = sum(1 for t in attempts if str(t.get("status") or "").upper() == "FAILED")
    return failures / len(attempts)


def prior_abandonment_count(
    checkout_sessions: tuple[dict[str, Any], ...],
    customer_id: str | None,
    exclude_session_id: str | None,
    now_micros: int,
    history_days: int,
) -> int:
    if not customer_id:
        return 0
    window_start = now_micros - history_days * DAY_MICROS
    count = 0
    for session in checkout_sessions:
        sid = str(session.get("session_id") or "")
        if sid and sid == exclude_session_id:
            continue
        if str(session.get("customer_id") or "") != customer_id:
            continue
        abandoned = session.get("abandoned_at_micros")
        if abandoned is None:
            continue
        if int(abandoned) > now_micros or int(abandoned) < window_start:
            continue
        count += 1
    return count


def prior_overdue_count(
    invoices: tuple[dict[str, Any], ...],
    customer_id: str | None,
    exclude_invoice_id: str | None,
    now_micros: int,
) -> int:
    if not customer_id:
        return 0
    count = 0
    for invoice in invoices:
        iid = str(invoice.get("invoice_id") or "")
        if iid and iid == exclude_invoice_id:
            continue
        if str(invoice.get("customer_id") or "") != customer_id:
            continue
        due_at = int(invoice.get("due_at_micros") or 0)
        if due_at <= now_micros and str(invoice.get("state") or "") in {"OVERDUE", "DISPUTED"}:
            count += 1
    return count


def subscription_debit_stats(
    transactions: list[dict[str, Any]],
    subscription_id: str | None,
) -> dict[str, int]:
    if not subscription_id:
        return {"successful_debit_count": 0, "failed_debit_count": 0}
    # Link via order/subscription refs when present on transactions.
    successes = failures = 0
    for txn in transactions:
        order_id = str(txn.get("order_id") or "")
        if subscription_id not in order_id:
            continue
        if str(txn.get("status") or "").upper() == "SUCCESS":
            successes += 1
        elif str(txn.get("status") or "").upper() == "FAILED":
            failures += 1
    return {"successful_debit_count": successes, "failed_debit_count": failures}


def contact_counts_from_opportunities(
    opportunities: tuple[dict[str, Any], ...],
    customer_id: str | None,
    now_micros: int,
    window_7d_days: int,
    window_30d_days: int,
) -> dict[str, int]:
    if not customer_id:
        return {"contacts_last_7d": 0, "contacts_last_30d": 0, "previous_recovery_count": 0}
    day_micros = 24 * 60 * 60 * 1_000_000
    start_7d = now_micros - window_7d_days * day_micros
    start_30d = now_micros - window_30d_days * day_micros
    contacts_7d = contacts_30d = recovery_count = 0
    for opp in opportunities:
        if str(opp.get("customer_id") or "") != customer_id:
            continue
        contacts = int(opp.get("contacts_made") or 0)
        detected = int(opp.get("first_detected_at_micros") or 0)
        if detected <= now_micros and detected >= start_30d:
            contacts_30d += contacts
        if detected <= now_micros and detected >= start_7d:
            contacts_7d += contacts
        state = str(opp.get("state") or "")
        if state in {"RECOVERED", "STOPPED", "CLOSED_UNRECOVERED"}:
            recovery_count += 1
    return {
        "contacts_last_7d": contacts_7d,
        "contacts_last_30d": contacts_30d,
        "previous_recovery_count": recovery_count,
    }


def fatigue_band(contacts_last_7d: int, contacts_last_30d: int) -> str:
    if contacts_last_7d >= 3 or contacts_last_30d >= 8:
        return "HIGH"
    if contacts_last_7d >= 1 or contacts_last_30d >= 3:
        return "MED"
    return "LOW"
