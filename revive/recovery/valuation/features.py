"""Observable feature extraction for predictor cells — docs/11 §4.4."""

from __future__ import annotations

from revive.domain.enums import ActionCode, RiskClass
from revive.recovery.candidates.models import RecoveryCandidate
from revive.recovery.context.models import ContextObject
from revive.recovery.diagnosis.models import Diagnosis
from revive.recovery.sentinel.models import DetectedOpportunity


def customer_segment(context: ContextObject) -> str:
    return context.customer.segment or "UNKNOWN"


def top_cause_code(diagnosis: Diagnosis) -> str:
    if diagnosis.ranked_causes:
        return diagnosis.ranked_causes[0].cause_code.value
    return "UNCLASSIFIED"


def observable_natural_prior(
    opportunity: DetectedOpportunity,
    context: ContextObject,
    diagnosis: Diagnosis,
) -> float:
    """Development prior for p(i,∅) from observable proxies only."""
    base = context.customer.prior_self_recovery_rate or 0.15
    if context.customer.success_rate is not None:
        base = 0.4 * base + 0.6 * context.customer.success_rate
    if opportunity.degradation_flag:
        base *= 0.65
    if context.temporal.time_to_window_close_micros is not None:
        days_left = context.temporal.time_to_window_close_micros / (24 * 60 * 60 * 1_000_000)
        if days_left < 2:
            base *= 0.85
    if context.receivable and context.receivable.ageing_days:
        if context.receivable.ageing_days > 30:
            base *= 0.5
        elif context.receivable.ageing_days > 15:
            base *= 0.75
    if diagnosis.unclassified:
        base *= 0.9
    return min(0.95, max(0.02, base))


def observable_action_prior(
    natural_prior: float,
    action: ActionCode,
    uplift_delta: float,
    opportunity: DetectedOpportunity,
) -> float:
    """Development prior for p(i,a) — never oracle-derived."""
    delta = uplift_delta
    if opportunity.degradation_flag and action == ActionCode.A01:
        delta *= 0.5
    if action == ActionCode.A00:
        return natural_prior
    return min(0.98, max(0.01, natural_prior + delta))
