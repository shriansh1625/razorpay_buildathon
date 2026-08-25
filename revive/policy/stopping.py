"""Stopping rules SR-01…SR-11 — docs/14 §2."""

from __future__ import annotations

from revive.domain.enums import ActionCode, CauseCode
from revive.policy.config import PolicyRules
from revive.policy.context import AuthorizeContext
from revive.policy.models import StoppingRuleResult


def evaluate_stopping_rules(
    action: ActionCode,
    ctx: AuthorizeContext,
    rules: PolicyRules,
) -> tuple[StoppingRuleResult, ...]:
    results: list[StoppingRuleResult] = []

    results.append(_sr01(ctx))
    results.append(_sr02(ctx))
    results.append(_sr03(ctx, rules))
    results.append(_sr04(ctx, rules))
    results.append(_sr05(ctx))
    results.append(_sr06(ctx))
    results.append(_sr07(ctx, rules))
    results.append(_sr08(ctx))
    results.append(_sr09(ctx))
    results.append(_sr10(ctx))
    results.append(_sr11(ctx))

    return tuple(results)


def any_blocking_stopping(results: tuple[StoppingRuleResult, ...]) -> StoppingRuleResult | None:
    for r in results:
        if r.fired and r.blocking:
            return r
    return None


def _sr01(ctx: AuthorizeContext) -> StoppingRuleResult:
    fired = ctx.now_micros >= ctx.recovery_window_expires_at_micros
    return StoppingRuleResult(
        rule_id="SR-01",
        fired=fired,
        blocking=fired,
        reason_code="RECOVERY_WINDOW_EXPIRED",
        observed_value=ctx.now_micros,
        threshold=ctx.recovery_window_expires_at_micros,
    )


def _sr02(ctx: AuthorizeContext) -> StoppingRuleResult:
    fired = ctx.payment_succeeded or ctx.opportunity_state == "RECOVERED"
    return StoppingRuleResult(
        rule_id="SR-02",
        fired=fired,
        blocking=fired,
        reason_code="RECOVERED",
        observed_value=ctx.opportunity_state,
    )


def _sr03(ctx: AuthorizeContext, rules: PolicyRules) -> StoppingRuleResult:
    fired = ctx.retries_on_opportunity >= rules.max_retries_per_opportunity
    return StoppingRuleResult(
        rule_id="SR-03",
        fired=fired,
        blocking=fired,
        reason_code="ATTEMPT_CAP_REACHED",
        observed_value=ctx.retries_on_opportunity,
        threshold=rules.max_retries_per_opportunity,
    )


def _sr04(ctx: AuthorizeContext, rules: PolicyRules) -> StoppingRuleResult:
    fired = ctx.contacts_on_opportunity >= rules.opportunity_contact_cap
    return StoppingRuleResult(
        rule_id="SR-04",
        fired=fired,
        blocking=fired,
        reason_code="OPPORTUNITY_CONTACT_CAP_REACHED",
        observed_value=ctx.contacts_on_opportunity,
        threshold=rules.opportunity_contact_cap,
    )


def _sr05(ctx: AuthorizeContext) -> StoppingRuleResult:
    terminal_causes = {
        CauseCode.CUSTOMER_DECLINED_TO_PAY,
        CauseCode.ORDER_NO_LONGER_WANTED,
    }
    fired = (
        ctx.top_cause_code in terminal_causes
        and ctx.cause_confidence_band in ("MED", "HIGH")
    )
    return StoppingRuleResult(
        rule_id="SR-05",
        fired=fired,
        blocking=fired,
        reason_code="TERMINAL_CAUSE",
        observed_value=ctx.top_cause_code.value if ctx.top_cause_code else None,
    )


def _sr06(ctx: AuthorizeContext) -> StoppingRuleResult:
    fired = ctx.approval_expired
    return StoppingRuleResult(
        rule_id="SR-06",
        fired=fired,
        blocking=fired,
        reason_code="APPROVAL_EXPIRED",
    )


def _sr07(ctx: AuthorizeContext, rules: PolicyRules) -> StoppingRuleResult:
    fired = ctx.consecutive_no_action_cycles >= rules.sr07_consecutive_cycles
    return StoppingRuleResult(
        rule_id="SR-07",
        fired=fired,
        blocking=fired,
        reason_code="ECONOMIC_EXHAUSTION",
        observed_value=ctx.consecutive_no_action_cycles,
        threshold=rules.sr07_consecutive_cycles,
    )


def _sr08(ctx: AuthorizeContext) -> StoppingRuleResult:
    fired = ctx.opted_out
    return StoppingRuleResult(
        rule_id="SR-08",
        fired=fired,
        blocking=fired,
        reason_code="CUSTOMER_OPT_OUT",
    )


def _sr09(ctx: AuthorizeContext) -> StoppingRuleResult:
    fired = len(ctx.risk_flags) > 0
    return StoppingRuleResult(
        rule_id="SR-09",
        fired=fired,
        blocking=fired,
        reason_code="RISK_OR_LEGAL_HOLD",
        observed_value=list(ctx.risk_flags),
    )


def _sr10(ctx: AuthorizeContext) -> StoppingRuleResult:
    fired = ctx.value_written_off or ctx.value_at_risk_paise <= 0
    return StoppingRuleResult(
        rule_id="SR-10",
        fired=fired,
        blocking=fired,
        reason_code="VALUE_NOT_RECOVERABLE",
        observed_value=ctx.value_at_risk_paise,
    )


def _sr11(ctx: AuthorizeContext) -> StoppingRuleResult:
    fired = ctx.merchant_halt or ctx.opportunity_suppressed
    return StoppingRuleResult(
        rule_id="SR-11",
        fired=fired,
        blocking=fired,
        reason_code="MERCHANT_STOP",
    )
