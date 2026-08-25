"""B0 — NO_ACTION: never acts (docs/20 §2)."""

from __future__ import annotations

from revive.benchmark.baselines.base import BaselinePolicy
from revive.benchmark.baselines.eligibility import eligible_opportunities
from revive.benchmark.config import BaselineEnvironmentConfig
from revive.benchmark.types import (
    BASELINE_NAMES,
    BaselineCycleContext,
    BaselineCycleResult,
    BaselineDecision,
    BaselinePolicyId,
    ObservableOpportunity,
)
from revive.domain.enums import ActionCode, DecisionOutcome


class NoActionBaseline:
    """Natural recovery floor — never selects a real action."""

    policy_id = BaselinePolicyId.B0
    strategy_version = "b0_v1"

    def decide_cycle(
        self,
        opportunities: list[ObservableOpportunity],
        context: BaselineCycleContext,
        env: BaselineEnvironmentConfig,
        epsilon_paise: int,
    ) -> BaselineCycleResult:
        eligible = eligible_opportunities(opportunities, context.now_micros)
        decisions: list[BaselineDecision] = []
        for opp in eligible:
            decisions.append(
                BaselineDecision(
                    policy_id=self.policy_id,
                    policy_name=BASELINE_NAMES[self.policy_id],
                    strategy_version=self.strategy_version,
                    cycle_id=context.cycle_id,
                    opportunity_id=opp.opportunity_id,
                    action_code=ActionCode.A00,
                    outcome=DecisionOutcome.NO_ACTION,
                    reason_code="NO_ACTION_CONTROL",
                    decision_at_micros=context.now_micros,
                    enrv_estimate_paise=0,
                    observable_features={
                        "value_at_risk_paise": opp.value_at_risk_paise,
                        "risk_class": opp.risk_class,
                    },
                )
            )
        return BaselineCycleResult(
            policy_id=self.policy_id,
            cycle_id=context.cycle_id,
            decisions=tuple(decisions),
        )
