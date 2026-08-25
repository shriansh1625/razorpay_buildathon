"""Resource usage vectors and reservation — docs/10 §3."""

from __future__ import annotations

from revive.domain.enums import ActionCode, CandidateAvailability
from revive.recovery.candidates.models import RecoveryCandidate
from revive.recovery.valuation.config import DEFAULT_INCENTIVE_TIER_PAISE
from revive.recovery.valuation.models import CandidateValuation
from revive.allocation.models import PricedCandidate, PortfolioItem, ResourceState

_USAGE_CACHE: dict[int, dict[str, int]] = {}


def clear_usage_cache() -> None:
    _USAGE_CACHE.clear()


def usage_dict(pc: PricedCandidate) -> dict[str, int]:
    key = id(pc)
    cached = _USAGE_CACHE.get(key)
    if cached is not None:
        return cached
    usage = dict(pc.usage)
    _USAGE_CACHE[key] = usage
    return usage


def incentive_paise_for(candidate: RecoveryCandidate) -> int:
    if candidate.action_code == ActionCode.A00:
        return 0
    tier = str(candidate.params.get("incentive_tier", "TIER_0"))
    return DEFAULT_INCENTIVE_TIER_PAISE.get(tier, 0)


def usage_for_candidate(candidate: RecoveryCandidate) -> dict[str, int]:
    """Resource consumption per docs/10 §3 — incentive reserved at full d(i,a)."""
    usage: dict[str, int] = {}
    for req in candidate.resource_requirements:
        if req.resource_key == "incentive_budget":
            usage["incentive_budget"] = incentive_paise_for(candidate)
        elif req.resource_key == "contact_allowance":
            usage["contact_allowance"] = req.quantity
        elif req.resource_key == "retry_slots":
            usage["retry_slots"] = req.quantity
        elif req.resource_key == "message_capacity":
            usage["message_capacity"] = req.quantity
        elif req.resource_key == "voice_minutes":
            usage["voice_minutes"] = req.quantity
        elif req.resource_key == "human_review_slots":
            usage["human_review_slots"] = req.quantity
    return usage


def priced_candidate(
    candidate: RecoveryCandidate,
    valuation: CandidateValuation,
) -> PricedCandidate:
    usage = usage_for_candidate(candidate)
    return PricedCandidate(
        candidate=candidate,
        valuation=valuation,
        usage=tuple(sorted(usage.items())),
    )


def portfolio_item_from_valuation(
    opportunity_id: str,
    customer_id: str | None,
    value_at_risk_paise: int,
    candidates: tuple[RecoveryCandidate, ...],
    valuations: tuple[CandidateValuation, ...],
) -> PortfolioItem:
    by_id = {v.candidate_id: v for v in valuations}
    priced: list[PricedCandidate] = []
    for cand in candidates:
        if cand.availability_status != CandidateAvailability.AVAILABLE:
            continue
        val = by_id.get(cand.candidate_id)
        if val is None:
            continue
        priced.append(priced_candidate(cand, val))
    return PortfolioItem(
        opportunity_id=opportunity_id,
        customer_id=customer_id,
        value_at_risk_paise=value_at_risk_paise,
        candidates=tuple(priced),
    )


def normalized_resource_cost(usage: dict[str, int]) -> float:
    """Density denominator — incentive paise scaled to comparable units."""
    total = 0.0
    for resource, qty in usage.items():
        if resource == "incentive_budget":
            total += qty / 1000.0
        else:
            total += float(qty)
    return max(1.0, total)


def can_reserve(state: ResourceState, usage: dict[str, int], customer_id: str | None) -> bool:
    if usage.get("retry_slots", 0) > state.remaining_retry_slots():
        return False
    if usage.get("message_capacity", 0) > state.remaining_message_capacity():
        return False
    if usage.get("voice_minutes", 0) > state.remaining_voice_minutes():
        return False
    if usage.get("human_review_slots", 0) > state.remaining_human_review_slots():
        return False
    incentive = usage.get("incentive_budget", 0)
    if incentive > state.remaining_incentive_budget_paise():
        return False
    contact = usage.get("contact_allowance", 0)
    if contact > 0:
        if customer_id is None:
            return False
        if contact > state.remaining_contacts(customer_id):
            return False
    return True


def reserve(state: ResourceState, usage: dict[str, int], customer_id: str | None) -> bool:
    if not can_reserve(state, usage, customer_id):
        return False
    state.retry_slots_used += usage.get("retry_slots", 0)
    state.message_capacity_used += usage.get("message_capacity", 0)
    state.voice_minutes_used += usage.get("voice_minutes", 0)
    state.human_review_slots_used += usage.get("human_review_slots", 0)
    state.incentive_budget_used_paise += usage.get("incentive_budget", 0)
    contact = usage.get("contact_allowance", 0)
    if contact > 0 and customer_id is not None:
        state.customer_contacts[customer_id] = state.contacts_for(customer_id) + contact
    return True


def resource_usage_summary(state: ResourceState) -> dict[str, int]:
    return {
        "retry_slots": state.retry_slots_used,
        "message_capacity": state.message_capacity_used,
        "voice_minutes": state.voice_minutes_used,
        "human_review_slots": state.human_review_slots_used,
        "incentive_budget": state.incentive_budget_used_paise,
    }
