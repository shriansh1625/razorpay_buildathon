"""Natural keys — one opportunity per distinct economic loss (docs/12 §6)."""

from __future__ import annotations

from revive.domain.enums import RiskClass
from revive.simulation.ids import deterministic_id


def natural_key_payment(*, customer_id: str, order_id: str, billing_period: str = "current") -> str:
    return f"PAYMENT_FAILURE|{customer_id}|{order_id}|{billing_period}"


def natural_key_checkout(*, identity: str, cart_fingerprint: str) -> str:
    return f"CHECKOUT_ABANDONMENT|{identity}|{cart_fingerprint}"


def natural_key_receivable(*, invoice_id: str) -> str:
    return f"RECEIVABLE_OVERDUE|{invoice_id}"


def natural_key_subscription(*, subscription_id: str, cycle_number: int) -> str:
    return f"SUBSCRIPTION_FAILURE|{subscription_id}|{cycle_number}"


def natural_key_mandate(*, mandate_id: str, next_charge_date: str) -> str:
    return f"MANDATE_HEALTH|{mandate_id}|{next_charge_date}"


def opportunity_id_for(natural_key: str) -> str:
    return deterministic_id("opp", natural_key)


def risk_class_from_natural_key(key: str) -> RiskClass:
    prefix = key.split("|", 1)[0]
    return RiskClass(prefix)
