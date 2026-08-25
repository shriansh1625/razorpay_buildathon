"""B2 — CONTACT_ALL: act on eligible opportunities until capacity exhausted (docs/20 §2)."""

from __future__ import annotations

from revive.benchmark.baselines.base import BaselinePolicy
from revive.benchmark.baselines.eligibility import eligible_opportunities
from revive.benchmark.baselines.resources import can_reserve_action, reserve_action
from revive.benchmark.config import CONTACT_ALL_DEFAULT_ACTION, BaselineEnvironmentConfig
from revive.benchmark.types import (
    BASELINE_NAMES,
    BaselineCycleContext,
    BaselineCycleResult,
    BaselineDecision,
    BaselinePolicyId,
    ObservableOpportunity,
)
from revive.domain.enums import ActionCode, DecisionOutcome, RiskClass


class ContactAllBaseline:
    """Effort without prioritisation — arbitrary deterministic order by opportunity_id."""

    policy_id = BaselinePolicyId.B2
    strategy_version = "b2_v1"

    def decide_cycle(
        self,
        opportunities: list[ObservableOpportunity],
        context: BaselineCycleContext,
        env: BaselineEnvironmentConfig,
        epsilon_paise: int,
    ) -> BaselineCycleResult:
        eligible = sorted(
            eligible_opportunities(opportunities, context.now_micros),
            key=lambda o: o.opportunity_id,
        )
        decisions: list[BaselineDecision] = []

        for opp in eligible:
            try:
                risk = RiskClass(opp.risk_class)
                action = CONTACT_ALL_DEFAULT_ACTION.get(risk, ActionCode.A05)
            except ValueError:
                action = ActionCode.A05

            outcome = DecisionOutcome.NO_ACTION
            reason = "B2_NOT_SELECTED"
            if can_reserve_action(action, opp.customer_id, context):
                if reserve_action(action, opp.customer_id, context):
                    outcome = DecisionOutcome.SELECTED
                    reason = "B2_CONTACT_ALL"
                else:
                    outcome = DecisionOutcome.DEFERRED
                    reason = "B2_CAPACITY_DEFERRED"
                    action = ActionCode.A00
            else:
                outcome = DecisionOutcome.DEFERRED
                reason = "B2_CAPACITY_DEFERRED"
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
                    observable_features={"risk_class": opp.risk_class},
                )
            )
        return BaselineCycleResult(
            policy_id=self.policy_id,
            cycle_id=context.cycle_id,
            decisions=tuple(decisions),
        )
