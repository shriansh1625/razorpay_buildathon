"""Policy and timing feasibility checks for candidate actions."""

from __future__ import annotations

from revive.domain.enums import ActionCode, CandidateAvailability, RiskClass
from revive.recovery.candidates.catalogue import (
    is_human_action,
    is_incentive_action,
    is_message_action,
    is_retry_action,
    resources_for,
)
from revive.recovery.candidates.config import CandidateConfig
from revive.recovery.candidates.models import CandidateCapacityContext, ResourceRequirement
from revive.recovery.candidates.rules import forbids_immediate_retry, prefers_delayed_retry, primary_cause
from revive.recovery.context.models import ContextObject
from revive.recovery.diagnosis.models import Diagnosis
from revive.recovery.sentinel.models import DetectedOpportunity

MINUTE_MICROS = 60 * 1_000_000

# Immutable risk-class compatibility table (docs/12) — built once, not per candidate.
_CLASS_ACTIONS: dict[RiskClass, frozenset[ActionCode]] = {
    RiskClass.PAYMENT_FAILURE: frozenset(
        {ActionCode.A01, ActionCode.A02, ActionCode.A03, ActionCode.A04}
    ),
    RiskClass.CHECKOUT_ABANDONMENT: frozenset(
        {ActionCode.A07, ActionCode.A06, ActionCode.A05}
    ),
    RiskClass.SUBSCRIPTION_FAILURE: frozenset(
        {ActionCode.A01, ActionCode.A02, ActionCode.A08}
    ),
    RiskClass.RECEIVABLE_OVERDUE: frozenset(
        {ActionCode.A05, ActionCode.A08, ActionCode.A09, ActionCode.A14}
    ),
    RiskClass.MANDATE_HEALTH: frozenset({ActionCode.A08, ActionCode.A11}),
}


def _comm_window_open(context: ContextObject, cfg: CandidateConfig) -> bool:
    hour = context.temporal.merchant_local_hour
    if hour is None:
        return True
    return cfg.comm_window_start_hour <= hour < cfg.comm_window_end_hour


def _contact_cap_ok(context: ContextObject, cfg: CandidateConfig) -> bool:
    return context.fatigue.contacts_last_7d < cfg.contact_cap_7d


def _retry_attempts_ok(opportunity: DetectedOpportunity, cfg: CandidateConfig) -> bool:
    return opportunity.attempt_seq < cfg.max_retry_attempts


def _window_open(opportunity: DetectedOpportunity, now_micros: int) -> bool:
    return now_micros < opportunity.recovery_window_expires_at_micros


def evaluate_feasibility(
    opportunity: DetectedOpportunity,
    context: ContextObject,
    diagnosis: Diagnosis,
    action: ActionCode,
    params: dict,
    now_micros: int,
    cfg: CandidateConfig,
    capacity: CandidateCapacityContext | None,
) -> tuple[
    CandidateAvailability,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    int | None,
    bool,
]:
    """Return availability, prerequisites, reason_codes, provenance, earliest_at, approval."""
    satisfied: list[str] = []
    failed: list[str] = []
    reasons: list[str] = []
    provenance: list[str] = ["action_catalogue"]
    cause = primary_cause(diagnosis)
    earliest: int | None = None
    approval = False

    if not opportunity.addressable:
        if action == ActionCode.A00:
            satisfied.append("NO_ACTION_ALWAYS_FEASIBLE")
            reasons.append("NOT_ADDRESSABLE")
            return (
                CandidateAvailability.AVAILABLE,
                tuple(satisfied),
                tuple(failed),
                tuple(reasons),
                None,
                False,
            )
        failed.append("ADDRESSABLE")
        reasons.append("NOT_ADDRESSABLE")
        return (
            CandidateAvailability.IMPOSSIBLE,
            tuple(satisfied),
            tuple(failed),
            tuple(reasons),
            None,
            False,
        )

    if not _window_open(opportunity, now_micros):
        if action == ActionCode.A00:
            satisfied.append("WINDOW_EXPIRED_NO_ACTION")
            reasons.append("WINDOW_EXPIRED")
            return (
                CandidateAvailability.AVAILABLE,
                tuple(satisfied),
                tuple(failed),
                tuple(reasons),
                None,
                False,
            )
        failed.append("RECOVERY_WINDOW")
        reasons.append("WINDOW_EXPIRED")
        return (
            CandidateAvailability.IMPOSSIBLE,
            tuple(satisfied),
            tuple(failed),
            tuple(reasons),
            None,
            False,
        )

    if action != ActionCode.A00 and action not in _CLASS_ACTIONS.get(
        opportunity.risk_class, frozenset()
    ):
        # Allow cross-family comms/human/incentive if enumerated by rules.
        if not (
            is_message_action(action)
            or is_human_action(action)
            or is_incentive_action(action)
            or action == ActionCode.A13
        ):
            failed.append("RISK_CLASS_COMPATIBILITY")
            reasons.append("ACTION_NOT_COMPATIBLE")
            provenance.append("risk_class_rules")
            return (
                CandidateAvailability.IMPOSSIBLE,
                tuple(satisfied),
                tuple(failed),
                tuple(reasons),
                None,
                False,
            )

    requirements = resources_for(action)

    if action == ActionCode.A00:
        satisfied.append("NO_ACTION")
        reasons.append("POLICY_ALLOWED")
        return (
            CandidateAvailability.AVAILABLE,
            tuple(satisfied),
            tuple(failed),
            tuple(reasons),
            None,
            False,
        )

    if is_retry_action(action) or action in {ActionCode.A01, ActionCode.A02}:
        if not _retry_attempts_ok(opportunity, cfg):
            failed.append("RETRY_ATTEMPTS_REMAINING")
            reasons.append("MAX_RETRIES_REACHED")
            provenance.append("retry_policy")
            return (
                CandidateAvailability.INELIGIBLE,
                tuple(satisfied),
                tuple(failed),
                tuple(reasons),
                None,
                False,
            )
        satisfied.append("RETRY_ATTEMPTS_REMAINING")
        if action == ActionCode.A01 and forbids_immediate_retry(cause):
            failed.append("IMMEDIATE_RETRY_ALLOWED")
            reasons.append("ISSUER_DOWNTIME_DELAY_REQUIRED")
            provenance.append("cause_actionability")
            delay = cfg.issuer_downtime_delay_minutes
            earliest = now_micros + delay * MINUTE_MICROS
            return (
                CandidateAvailability.INELIGIBLE,
                tuple(satisfied),
                tuple(failed),
                tuple(reasons),
                earliest,
                False,
            )
        if action == ActionCode.A02:
            delay = params.get("delay_minutes", cfg.scheduled_retry_delay_minutes)
            if prefers_delayed_retry(cause):
                delay = max(delay, cfg.issuer_downtime_delay_minutes)
            earliest = now_micros + int(delay) * MINUTE_MICROS
            if earliest >= opportunity.recovery_window_expires_at_micros:
                failed.append("RETRY_WINDOW")
                reasons.append("WINDOW_TOO_SHORT_FOR_DELAY")
                return (
                    CandidateAvailability.IMPOSSIBLE,
                    tuple(satisfied),
                    tuple(failed),
                    tuple(reasons),
                    earliest,
                    False,
                )
        satisfied.append("PAYMENT_STATE_RETRYABLE")

    if action == ActionCode.A03 and context.instrument:
        if context.instrument.expiry_state == "EXPIRED":
            satisfied.append("INSTRUMENT_UPDATE_NEEDED")
        elif context.instrument.block_state == "BLOCKED":
            failed.append("INSTRUMENT_STATE")
            reasons.append("INSTRUMENT_BLOCKED")
            return (
                CandidateAvailability.IMPOSSIBLE,
                tuple(satisfied),
                tuple(failed),
                tuple(reasons),
                None,
                False,
            )

    if is_message_action(action):
        provenance.append("communication_policy")
        if not _comm_window_open(context, cfg):
            failed.append("COMMUNICATION_WINDOW")
            reasons.append("CONTACT_WINDOW_CLOSED")
            return (
                CandidateAvailability.INELIGIBLE,
                tuple(satisfied),
                tuple(failed),
                tuple(reasons),
                None,
                False,
            )
        satisfied.append("COMMUNICATION_WINDOW_OPEN")
        if not _contact_cap_ok(context, cfg):
            failed.append("CONTACT_FREQUENCY")
            reasons.append("MAX_CONTACTS_REACHED")
            return (
                CandidateAvailability.INELIGIBLE,
                tuple(satisfied),
                tuple(failed),
                tuple(reasons),
                None,
                False,
            )
        if context.fatigue.contacts_last_30d >= cfg.contact_cap_per_customer:
            failed.append("CONTACT_FREQUENCY")
            reasons.append("MAX_CONTACTS_REACHED")
            return (
                CandidateAvailability.INELIGIBLE,
                tuple(satisfied),
                tuple(failed),
                tuple(reasons),
                None,
                False,
            )
        satisfied.append("CONTACT_LIMIT_OK")

    if is_incentive_action(action):
        provenance.append("incentive_policy")
        max_incentive = min(
            cfg.incentive_max_paise,
            int(opportunity.value_at_risk_paise * cfg.incentive_max_pct_of_v),
        )
        if max_incentive <= 0:
            failed.append("INCENTIVE_POLICY")
            reasons.append("POLICY_MAX_DISCOUNT")
            return (
                CandidateAvailability.INELIGIBLE,
                tuple(satisfied),
                tuple(failed),
                tuple(reasons),
                None,
                False,
            )
        satisfied.append("INCENTIVE_WITHIN_POLICY")
        params.setdefault("max_incentive_paise", max_incentive)

    if is_human_action(action) or action == ActionCode.A13:
        provenance.append("escalation_policy")
        if opportunity.value_at_risk_paise >= cfg.approval_value_threshold_paise:
            approval = True
            reasons.append("APPROVAL_REQUIRED_HIGH_VALUE")

    if capacity is not None and requirements:
        if not capacity.can_reserve(requirements):
            failed.append("CYCLE_CAPACITY")
            for req in requirements:
                if req.resource_key == "retry_slots" and capacity.retry_slots_remaining < req.quantity:
                    reasons.append("RETRY_CAPACITY_EXHAUSTED")
                elif req.resource_key == "message_capacity" and capacity.message_capacity_remaining < req.quantity:
                    reasons.append("MESSAGE_CAPACITY_EXHAUSTED")
                elif req.resource_key == "voice_minutes" and capacity.voice_minutes_remaining < req.quantity:
                    reasons.append("VOICE_CAPACITY_EXHAUSTED")
                elif req.resource_key == "human_review_slots" and capacity.human_review_slots_remaining < req.quantity:
                    reasons.append("HUMAN_CAPACITY_EXHAUSTED")
                elif req.resource_key == "incentive_budget" and capacity.incentive_budget_remaining_paise < req.quantity:
                    reasons.append("INCENTIVE_BUDGET_EXHAUSTED")
            provenance.append("capacity_snapshot")
            return (
                CandidateAvailability.TEMPORARILY_UNAVAILABLE,
                tuple(satisfied),
                tuple(failed),
                tuple(reasons),
                earliest,
                approval,
            )

    satisfied.append("POLICY_ALLOWED")
    reasons.append("POLICY_ALLOWED")
    return (
        CandidateAvailability.AVAILABLE,
        tuple(satisfied),
        tuple(failed),
        tuple(reasons),
        earliest,
        approval,
    )
