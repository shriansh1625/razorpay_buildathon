"""Intervention cost, incentive, and fatigue — docs/11 §5.1."""

from __future__ import annotations

from revive.benchmark.config import DEFAULT_ACTION_COSTS_PAISE
from revive.domain.enums import ActionCode
from revive.recovery.candidates.models import RecoveryCandidate
from revive.recovery.context.models import ContextObject
from revive.recovery.sentinel.models import DetectedOpportunity
from revive.recovery.valuation.money import bankers_round_paise

_CHANNEL_INTRUSIVENESS: dict[str, float] = {
    "NONE": 0.0,
    "EMAIL": 0.4,
    "SMS": 0.8,
    "PUSH": 0.3,
    "VOICE": 2.0,
    "WHATSAPP": 0.7,
}


def direct_cost_paise(candidate: RecoveryCandidate) -> int:
    if candidate.action_code == ActionCode.A00:
        return 0
    return candidate.nominal_cost_paise


def incentive_paise(candidate: RecoveryCandidate, cfg: ValuationConfig) -> int:
    if candidate.action_code == ActionCode.A00:
        return 0
    tier = candidate.params.get("incentive_tier", "TIER_0")
    return cfg.incentive_paise(str(tier))


def fatigue_units(
    candidate: RecoveryCandidate,
    context: ContextObject,
    opportunity: DetectedOpportunity,
) -> float:
    if candidate.action_code == ActionCode.A00:
        return 0.0
    contacts_7d = context.fatigue.contacts_last_7d
    contacts_30d = context.fatigue.contacts_last_30d
    units = contacts_7d * 0.5 + contacts_30d * 0.1
    channel = str(candidate.params.get("channel", "NONE"))
    units += _CHANNEL_INTRUSIVENESS.get(channel, 0.5)
    if opportunity.value_at_risk_paise >= 100_000:
        units *= 1.15
    return max(0.0, units)


def fatigue_cost_paise(
    candidate: RecoveryCandidate,
    context: ContextObject,
    opportunity: DetectedOpportunity,
    cfg: ValuationConfig,
) -> int:
    units = fatigue_units(candidate, context, opportunity)
    return bankers_round_paise(cfg.lambda_fatigue * units)
