"""Canonical opportunity identity bridge — world ↔ sentinel via natural_key."""

from __future__ import annotations

from revive.domain.enums import RiskClass
from revive.recovery.sentinel.identity import (
    natural_key_checkout,
    natural_key_mandate,
    natural_key_payment,
    natural_key_receivable,
    natural_key_subscription,
)
from revive.recovery.sentinel.models import DetectedOpportunity
from revive.recovery.sentinel.detect import SentinelResult
from revive.simulation.observation import ObservableWorldView


class OpportunityIdentityError(ValueError):
    """Deterministic identity invariant violation."""


def canonical_natural_key_from_observable_opportunity(
    opportunity: dict,
    view: ObservableWorldView,
) -> str | None:
    """
    Derive the sentinel canonical natural_key for a world observable opportunity.

    Uses the same identity functions as M4 detect() — no fuzzy matching.
    """
    try:
        risk = RiskClass(str(opportunity.get("risk_class")))
    except ValueError:
        return None

    linked = dict(opportunity.get("linked_refs") or {})
    customer_id = opportunity.get("customer_id")

    if risk == RiskClass.PAYMENT_FAILURE:
        order_id = linked.get("order_id")
        if order_id and customer_id:
            return natural_key_payment(
                customer_id=str(customer_id),
                order_id=str(order_id),
            )
        return None

    if risk == RiskClass.CHECKOUT_ABANDONMENT:
        session_id = linked.get("checkout_session_id")
        if not session_id:
            return None
        identity = str(customer_id) if customer_id else str(session_id)
        return natural_key_checkout(
            identity=identity,
            cart_fingerprint=str(session_id),
        )

    if risk == RiskClass.SUBSCRIPTION_FAILURE:
        subscription_id = linked.get("subscription_id")
        if not subscription_id:
            return None
        for sub in view.subscriptions:
            if str(sub.get("subscription_id") or "") == str(subscription_id):
                cycle_number = int(sub.get("cycle_number") or 0)
                return natural_key_subscription(
                    subscription_id=str(subscription_id),
                    cycle_number=cycle_number,
                )
        return None

    if risk == RiskClass.RECEIVABLE_OVERDUE:
        invoice_id = linked.get("invoice_id")
        if invoice_id:
            return natural_key_receivable(invoice_id=str(invoice_id))
        return None

    if risk == RiskClass.MANDATE_HEALTH:
        mandate_id = linked.get("mandate_id")
        if not mandate_id:
            return None
        for mandate in view.mandates:
            if str(mandate.get("mandate_id") or "") == str(mandate_id):
                expires_at = int(mandate.get("expires_at_micros") or 0)
                return natural_key_mandate(
                    mandate_id=str(mandate_id),
                    next_charge_date=str(expires_at),
                )
        return None

    return None


def observable_opportunity_by_id(
    view: ObservableWorldView,
    opportunity_id: str,
) -> dict | None:
    for opp in view.opportunities:
        if str(opp.get("opportunity_id")) == opportunity_id:
            return opp
    return None


def index_sentinel_by_natural_key(
    sentinel: SentinelResult,
) -> dict[str, DetectedOpportunity]:
    """Index detected opportunities by canonical natural_key."""
    index: dict[str, DetectedOpportunity] = {}
    for opp in sentinel.opportunities:
        existing = index.get(opp.natural_key)
        if existing is not None:
            raise OpportunityIdentityError(
                f"duplicate sentinel natural_key {opp.natural_key!r}: "
                f"{existing.opportunity_id} vs {opp.opportunity_id}"
            )
        index[opp.natural_key] = opp
    return index


def resolve_sentinel_for_world_opportunity_id(
    world_opportunity_id: str,
    view: ObservableWorldView,
    sentinel_index: dict[str, DetectedOpportunity],
    *,
    strict: bool = False,
) -> DetectedOpportunity | None:
    """
    Resolve a baseline/world opportunity_id to exactly one sentinel opportunity.

    When strict=True, raises OpportunityIdentityError on zero or duplicate matches.
    """
    world_opp = observable_opportunity_by_id(view, world_opportunity_id)
    if world_opp is None:
        if strict:
            raise OpportunityIdentityError(
                f"unknown world opportunity_id {world_opportunity_id!r}"
            )
        return None

    natural_key = canonical_natural_key_from_observable_opportunity(world_opp, view)
    if natural_key is None:
        if strict:
            raise OpportunityIdentityError(
                f"cannot derive natural_key for world opportunity {world_opportunity_id!r}"
            )
        return None

    detected = sentinel_index.get(natural_key)
    if detected is None:
        if strict:
            raise OpportunityIdentityError(
                f"no sentinel opportunity for natural_key {natural_key!r} "
                f"(world {world_opportunity_id!r})"
            )
        return None

    return detected


def index_world_opportunities_by_natural_key(
    view: ObservableWorldView,
) -> dict[str, str]:
    """Cycle-local index: canonical natural_key → world opportunity_id."""
    index: dict[str, str] = {}
    for opp in view.opportunities:
        natural_key = canonical_natural_key_from_observable_opportunity(opp, view)
        if natural_key is None:
            continue
        world_id = str(opp.get("opportunity_id"))
        existing = index.get(natural_key)
        if existing is not None and existing != world_id:
            raise OpportunityIdentityError(
                f"duplicate world natural_key {natural_key!r}: "
                f"{existing} vs {world_id}"
            )
        index[natural_key] = world_id
    return index


def resolve_world_opportunity_id_by_natural_key(
    natural_key: str,
    view: ObservableWorldView,
    *,
    world_index: dict[str, str] | None = None,
) -> str | None:
    """Map sentinel canonical natural_key back to generator world opportunity_id."""
    if world_index is not None:
        return world_index.get(natural_key)
    for opp in view.opportunities:
        derived = canonical_natural_key_from_observable_opportunity(opp, view)
        if derived == natural_key:
            return str(opp.get("opportunity_id"))
    return None


def assert_baseline_identity_invariant(
    world_opportunity_id: str,
    view: ObservableWorldView,
    sentinel_index: dict[str, DetectedOpportunity],
) -> DetectedOpportunity:
    """Diagnostic assertion — exactly one sentinel match required."""
    return resolve_sentinel_for_world_opportunity_id(
        world_opportunity_id,
        view,
        sentinel_index,
        strict=True,
    )
