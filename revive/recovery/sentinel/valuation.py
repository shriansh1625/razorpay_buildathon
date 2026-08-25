"""V(i) — recoverable amount in paise (docs/12 §4, RR-FUNC-002)."""

from __future__ import annotations

from revive.domain.enums import RiskClass
from revive.recovery.sentinel.config import SentinelConfig


def checkout_value_paise(session: dict) -> int | None:
    value = session.get("cart_value_paise")
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    if value <= 0:
        return None
    return value


def receivable_outstanding_paise(invoice: dict) -> int:
    issued = int(invoice.get("issued_amount_paise") or 0)
    paid = int(invoice.get("paid_amount_paise") or 0)
    credited = int(invoice.get("credited_amount_paise") or 0)
    written_off = int(invoice.get("written_off_amount_paise") or 0)
    disputed = int(invoice.get("disputed_amount_paise") or 0)
    outstanding = issued - paid - credited - written_off - disputed
    return max(0, outstanding)


def subscription_value_paise(subscription: dict, config: SentinelConfig) -> int:
    cycle = int(subscription.get("cycle_amount_paise") or 0)
    continuation = int(config.continuation_factor * cycle)
    return cycle + continuation


def compute_value_at_risk(
    risk_class: RiskClass,
    *,
    gross_paise: int,
    config: SentinelConfig,
    invoice: dict | None = None,
    subscription: dict | None = None,
) -> int:
    if risk_class == RiskClass.RECEIVABLE_OVERDUE and invoice is not None:
        return receivable_outstanding_paise(invoice)
    if risk_class == RiskClass.SUBSCRIPTION_FAILURE and subscription is not None:
        return subscription_value_paise(subscription, config)
    return max(0, int(gross_paise))
