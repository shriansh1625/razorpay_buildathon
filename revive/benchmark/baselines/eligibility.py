"""Opportunity eligibility for baseline cycles — docs/09 §2.1 (simplified for M3)."""

from __future__ import annotations

from revive.benchmark.types import ObservableOpportunity

_ELIGIBLE_STATES = frozenset(
    {
        "DETECTED",
        "DIAGNOSED",
        "PRICED",
        "DEFERRED",
        "NO_ACTION_CYCLE",
        "AWAITING_OUTCOME",
    }
)


def is_eligible(opportunity: ObservableOpportunity, now_micros: int) -> bool:
    if not opportunity.addressable:
        return False
    if opportunity.state not in _ELIGIBLE_STATES:
        return False
    if now_micros >= opportunity.recovery_window_expires_at_micros:
        return False
    if opportunity.next_eligible_at_micros is not None and now_micros < opportunity.next_eligible_at_micros:
        return False
    return True


def eligible_opportunities(
    opportunities: list[ObservableOpportunity],
    now_micros: int,
) -> list[ObservableOpportunity]:
    return [o for o in opportunities if is_eligible(o, now_micros)]
