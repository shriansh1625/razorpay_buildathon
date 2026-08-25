"""Cycle-scoped observable view indexes — M13.14 semantics-preserving cache."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from revive.recovery.context.config import ContextConfig, default_context_config
from revive.recovery.context.history import payment_history_stats
from revive.recovery.sentinel.config import SentinelConfig
from revive.recovery.sentinel.degradation import detect_degraded_cohorts
from revive.recovery.context.history import (
    merchant_failure_rate,
    method_failure_rate,
)
from revive.simulation.observation import ObservableWorldView

MINUTE_MICROS = 60 * 1_000_000
DAY_MICROS = 24 * 60 * 60 * 1_000_000


@dataclass
class CycleViewCache:
    """
    Immutable per-cycle indexes over an observable world view.

    Scope: one REVIVE cycle (invalidated when ``now_micros`` or world view changes).
    """

    view: ObservableWorldView
    now_micros: int
    config: ContextConfig = field(default_factory=default_context_config)
    _customers_by_id: dict[str, dict[str, Any]] = field(init=False, repr=False)
    _instruments_by_id: dict[str, dict[str, Any]] = field(init=False, repr=False)
    _checkout_by_id: dict[str, dict[str, Any]] = field(init=False, repr=False)
    _subscriptions_by_id: dict[str, dict[str, Any]] = field(init=False, repr=False)
    _mandates_by_id: dict[str, dict[str, Any]] = field(init=False, repr=False)
    _invoices_by_id: dict[str, dict[str, Any]] = field(init=False, repr=False)
    _merchants_by_id: dict[str, dict[str, Any]] = field(init=False, repr=False)
    _transactions_by_customer: dict[str, tuple[dict[str, Any], ...]] = field(init=False, repr=False)
    _contact_stats_by_customer: dict[str, dict[str, int]] = field(init=False, repr=False)
    _checkout_by_customer: dict[str, list[dict[str, Any]]] = field(init=False, repr=False)
    _invoices_by_customer: dict[str, list[dict[str, Any]]] = field(init=False, repr=False)
    _degraded_methods: frozenset[str] = field(init=False, repr=False)
    _merchant_failure_rate: float | None = field(init=False, repr=False)
    _method_failure_rates: dict[str, float | None] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._customers_by_id = {
            str(c.get("customer_id")): c for c in self.view.customers if c.get("customer_id")
        }
        self._instruments_by_id = {
            str(i.get("instrument_id")): i for i in self.view.instruments if i.get("instrument_id")
        }
        self._checkout_by_id = {
            str(s.get("session_id")): s for s in self.view.checkout_sessions if s.get("session_id")
        }
        self._subscriptions_by_id = {
            str(s.get("subscription_id")): s for s in self.view.subscriptions if s.get("subscription_id")
        }
        self._mandates_by_id = {
            str(m.get("mandate_id")): m for m in self.view.mandates if m.get("mandate_id")
        }
        self._invoices_by_id = {
            str(i.get("invoice_id")): i for i in self.view.invoices if i.get("invoice_id")
        }
        self._merchants_by_id = {
            str(m.get("merchant_id")): m for m in self.view.merchants if m.get("merchant_id")
        }
        window_start = self.now_micros - self.config.customer_history_days * DAY_MICROS
        by_customer: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for txn in self.view.transactions:
            customer_id = str(txn.get("customer_id") or "")
            if not customer_id:
                continue
            attempted = int(txn.get("attempted_at_micros") or 0)
            if attempted > self.now_micros or attempted < window_start:
                continue
            by_customer[customer_id].append(txn)
        self._transactions_by_customer = {
            cid: tuple(sorted(rows, key=lambda t: int(t.get("attempted_at_micros") or 0)))
            for cid, rows in by_customer.items()
        }
        self._contact_stats_by_customer = self._build_contact_stats()
        self._checkout_by_customer = self._build_checkout_by_customer()
        self._invoices_by_customer = self._build_invoices_by_customer()
        sentinel_cfg = SentinelConfig(
            degradation_window_minutes=self.config.degradation_window_minutes,
            degradation_min_attempts=self.config.degradation_min_attempts,
            degradation_failure_rate=self.config.degradation_failure_rate,
        )
        self._degraded_methods = frozenset(
            detect_degraded_cohorts(list(self.view.transactions), self.now_micros, sentinel_cfg)
        )
        self._merchant_failure_rate = merchant_failure_rate(
            self.view.transactions,
            self.now_micros,
            self.config.degradation_window_minutes,
        )
        self._method_failure_rates = {}

    @property
    def cache_key(self) -> tuple[int, int]:
        return (id(self.view), self.now_micros)

    def customer_row(self, customer_id: str | None) -> dict[str, Any] | None:
        if not customer_id:
            return None
        return self._customers_by_id.get(customer_id)

    def instrument_row(self, instrument_id: str | None) -> dict[str, Any] | None:
        if not instrument_id:
            return None
        return self._instruments_by_id.get(instrument_id)

    def checkout_row(self, session_id: str | None) -> dict[str, Any] | None:
        if not session_id:
            return None
        return self._checkout_by_id.get(session_id)

    def subscription_row(self, subscription_id: str | None) -> dict[str, Any] | None:
        if not subscription_id:
            return None
        return self._subscriptions_by_id.get(subscription_id)

    def mandate_row(self, mandate_id: str | None) -> dict[str, Any] | None:
        if not mandate_id:
            return None
        return self._mandates_by_id.get(mandate_id)

    def invoice_row(self, invoice_id: str | None) -> dict[str, Any] | None:
        if not invoice_id:
            return None
        return self._invoices_by_id.get(invoice_id)

    def merchant_timezone(self, merchant_id: str) -> str:
        merchant = self._merchants_by_id.get(merchant_id)
        if merchant:
            return str(merchant.get("timezone") or "UTC")
        return "UTC"

    def customer_transactions(self, customer_id: str | None) -> list[dict[str, Any]]:
        if not customer_id:
            return []
        return list(self._transactions_by_customer.get(customer_id, ()))

    def contact_stats(self, customer_id: str | None) -> dict[str, int]:
        if not customer_id:
            return {"contacts_last_7d": 0, "contacts_last_30d": 0, "previous_recovery_count": 0}
        return dict(
            self._contact_stats_by_customer.get(
                customer_id,
                {"contacts_last_7d": 0, "contacts_last_30d": 0, "previous_recovery_count": 0},
            )
        )

    def prior_abandonment_count(
        self,
        customer_id: str | None,
        exclude_session_id: str | None,
    ) -> int:
        if not customer_id:
            return 0
        window_start = self.now_micros - self.config.customer_history_days * DAY_MICROS
        count = 0
        for session in self._checkout_by_customer.get(customer_id, ()):
            sid = str(session.get("session_id") or "")
            if sid and sid == exclude_session_id:
                continue
            abandoned = session.get("abandoned_at_micros")
            if abandoned is None:
                continue
            abandoned_at = int(abandoned)
            if abandoned_at > self.now_micros or abandoned_at < window_start:
                continue
            count += 1
        return count

    def prior_overdue_count(self, customer_id: str | None, exclude_invoice_id: str | None) -> int:
        if not customer_id:
            return 0
        count = 0
        for invoice in self._invoices_by_customer.get(customer_id, ()):
            iid = str(invoice.get("invoice_id") or "")
            if iid and iid == exclude_invoice_id:
                continue
            due_at = int(invoice.get("due_at_micros") or 0)
            if due_at <= self.now_micros and str(invoice.get("state") or "") in {"OVERDUE", "DISPUTED"}:
                count += 1
        return count

    @property
    def degraded_methods(self) -> frozenset[str]:
        return self._degraded_methods

    def merchant_failure_rate_cached(self) -> float | None:
        return self._merchant_failure_rate

    def method_failure_rate_cached(self, method_type: str | None) -> float | None:
        if not method_type:
            return None
        if method_type not in self._method_failure_rates:
            self._method_failure_rates[method_type] = method_failure_rate(
                self.view.transactions,
                method_type,
                self.now_micros,
                self.config.degradation_window_minutes,
            )
        return self._method_failure_rates[method_type]

    def payment_stats(self, customer_id: str | None) -> dict[str, Any]:
        return payment_history_stats(self.customer_transactions(customer_id))

    def _build_contact_stats(self) -> dict[str, dict[str, int]]:
        start_7d = self.now_micros - self.config.fatigue_7d_days * DAY_MICROS
        start_30d = self.now_micros - self.config.fatigue_window_days * DAY_MICROS
        stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"contacts_last_7d": 0, "contacts_last_30d": 0, "previous_recovery_count": 0}
        )
        for opp in self.view.opportunities:
            customer_id = str(opp.get("customer_id") or "")
            if not customer_id:
                continue
            contacts = int(opp.get("contacts_made") or 0)
            detected = int(opp.get("first_detected_at_micros") or 0)
            row = stats[customer_id]
            if detected <= self.now_micros and detected >= start_30d:
                row["contacts_last_30d"] += contacts
            if detected <= self.now_micros and detected >= start_7d:
                row["contacts_last_7d"] += contacts
            state = str(opp.get("state") or "")
            if state in {"RECOVERED", "STOPPED", "CLOSED_UNRECOVERED"}:
                row["previous_recovery_count"] += 1
        return dict(stats)

    def _build_checkout_by_customer(self) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for session in self.view.checkout_sessions:
            customer_id = str(session.get("customer_id") or "")
            if customer_id:
                grouped[customer_id].append(session)
        return dict(grouped)

    def _build_invoices_by_customer(self) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for invoice in self.view.invoices:
            customer_id = str(invoice.get("customer_id") or "")
            if customer_id:
                grouped[customer_id].append(invoice)
        return dict(grouped)
