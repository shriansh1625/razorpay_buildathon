"""B1 — FIXED_RETRY: class-based retry schedule, no targeting (docs/20 §2)."""

from __future__ import annotations

from revive.benchmark.baselines.base import BaselinePolicy
from revive.benchmark.baselines.eligibility import eligible_opportunities
from revive.benchmark.baselines.resources import can_reserve_action, reserve_action
from revive.benchmark.config import B1_RETRY_SCHEDULE, BaselineEnvironmentConfig
from revive.benchmark.types import (
    BASELINE_NAMES,
    BaselineCycleContext,
    BaselineCycleResult,
    BaselineDecision,
    BaselinePolicyId,
    ObservableOpportunity,
)
from revive.domain.enums import ActionCode, DecisionOutcome, RiskClass

MINUTE_MICROS = 60 * 1_000_000


class FixedRetryBaseline:
    """Fixed retry schedule per risk class — PROVISIONAL schedule in benchmark/config.py."""

    policy_id = BaselinePolicyId.B1
    strategy_version = "b1_adr-013_v1"

    def decide_cycle(
        self,
        opportunities: list[ObservableOpportunity],
        context: BaselineCycleContext,
        env: BaselineEnvironmentConfig,
        epsilon_paise: int,
    ) -> BaselineCycleResult:
        eligible = eligible_opportunities(opportunities, context.now_micros)
        decisions: list[BaselineDecision] = []

        for opp in sorted(eligible, key=lambda o: o.opportunity_id):
            action, reason = self._scheduled_action(opp, context)
            outcome = DecisionOutcome.NO_ACTION
            if action != ActionCode.A00:
                if can_reserve_action(action, opp.customer_id, context):
                    if reserve_action(action, opp.customer_id, context):
                        outcome = DecisionOutcome.SELECTED
                        reason = "B1_SCHEDULED_RETRY"
                    else:
                        outcome = DecisionOutcome.DEFERRED
                        reason = "B1_CAPACITY_DEFERRED"
                        action = ActionCode.A00
                else:
                    outcome = DecisionOutcome.DEFERRED
                    reason = "B1_CAPACITY_DEFERRED"
                    action = ActionCode.A00

            decisions.append(
                BaselineDecision(
                    policy_id=self.policy_id,
                    policy_name=BASELINE_NAMES[self.policy_id],
                    strategy_version=self.strategy_version,
                    cycle_id=context.cycle_id,
                    opportunity_id=opp.opportunity_id,
                    action_code=action,
                    outcome=outcome,
                    reason_code=reason,
                    decision_at_micros=context.now_micros,
                    observable_features={
                        "attempt_seq": opp.attempt_seq,
                        "risk_class": opp.risk_class,
                        "elapsed_minutes": (context.now_micros - opp.first_detected_at_micros)
                        // MINUTE_MICROS,
                    },
                )
            )
        return BaselineCycleResult(
            policy_id=self.policy_id,
            cycle_id=context.cycle_id,
            decisions=tuple(decisions),
        )

    def _scheduled_action(
        self,
        opp: ObservableOpportunity,
        context: BaselineCycleContext,
    ) -> tuple[ActionCode, str]:
        try:
            risk = RiskClass(opp.risk_class)
        except ValueError:
            return ActionCode.A00, "B1_UNKNOWN_CLASS"

        schedule = B1_RETRY_SCHEDULE.get(risk, ())
        if not schedule:
            return ActionCode.A00, "B1_NO_SCHEDULE"

        elapsed_minutes = (context.now_micros - opp.first_detected_at_micros) // MINUTE_MICROS
        step_index = min(opp.attempt_seq, len(schedule) - 1)
        delay, action = schedule[step_index]

        if elapsed_minutes < delay:
            return ActionCode.A00, "B1_WAITING_FOR_SCHEDULE"

        return action, "B1_SCHEDULED_RETRY"
