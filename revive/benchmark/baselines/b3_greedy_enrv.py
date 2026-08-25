"""B3 — GREEDY_ENRV: rank by raw ENRV, ignore resource density (docs/20 §2, 10 §5.2)."""

from __future__ import annotations

from revive.benchmark.baselines.base import BaselinePolicy
from revive.benchmark.baselines.eligibility import eligible_opportunities
from revive.benchmark.baselines.resources import can_reserve_action, reserve_action
from revive.benchmark.config import BaselineEnvironmentConfig
from revive.benchmark.pricing import best_action_for_opportunity
from revive.benchmark.types import (
    BASELINE_NAMES,
    BaselineCycleContext,
    BaselineCycleResult,
    BaselineDecision,
    BaselinePolicyId,
    ObservableOpportunity,
)
from revive.domain.enums import ActionCode, DecisionOutcome

_GREEDY_CANDIDATES = (
    ActionCode.A01,
    ActionCode.A02,
    ActionCode.A03,
    ActionCode.A04,
    ActionCode.A05,
    ActionCode.A06,
    ActionCode.A09,
    ActionCode.A08,
)


class GreedyEnrvBaseline:
    """Greedy by raw heuristic ENRV — simpler than REVIVE constrained allocator."""

    policy_id = BaselinePolicyId.B3
    strategy_version = "b3_v1_observable_heuristic"

    def decide_cycle(
        self,
        opportunities: list[ObservableOpportunity],
        context: BaselineCycleContext,
        env: BaselineEnvironmentConfig,
        epsilon_paise: int,
    ) -> BaselineCycleResult:
        eligible = eligible_opportunities(opportunities, context.now_micros)

        ranked: list[tuple[int, ObservableOpportunity, ActionCode, int]] = []
        for opp in eligible:
            action, enrv = best_action_for_opportunity(opp, _GREEDY_CANDIDATES, env, epsilon_paise)
            ranked.append((enrv, opp, action, enrv))

        ranked.sort(key=lambda item: (-item[0], item[1].opportunity_id))

        decisions_by_id: dict[str, BaselineDecision] = {}
        for rank, (_, opp, action, enrv) in enumerate(ranked, start=1):
            if action == ActionCode.A00:
                decisions_by_id[opp.opportunity_id] = BaselineDecision(
                    policy_id=self.policy_id,
                    policy_name=BASELINE_NAMES[self.policy_id],
                    strategy_version=self.strategy_version,
                    cycle_id=context.cycle_id,
                    opportunity_id=opp.opportunity_id,
                    action_code=ActionCode.A00,
                    outcome=DecisionOutcome.NO_ACTION,
                    reason_code="B3_BELOW_EPSILON",
                    decision_at_micros=context.now_micros,
                    enrv_estimate_paise=0,
                    rank=rank,
                )
                continue

            outcome = DecisionOutcome.DEFERRED
            reason = "B3_CAPACITY_DEFERRED"
            selected_action = ActionCode.A00
            if can_reserve_action(action, opp.customer_id, context):
                if reserve_action(action, opp.customer_id, context):
                    outcome = DecisionOutcome.SELECTED
                    reason = "B3_GREEDY_ENRV"
                    selected_action = action

            decisions_by_id[opp.opportunity_id] = BaselineDecision(
                policy_id=self.policy_id,
                policy_name=BASELINE_NAMES[self.policy_id],
                strategy_version=self.strategy_version,
                cycle_id=context.cycle_id,
                opportunity_id=opp.opportunity_id,
                action_code=selected_action,
                outcome=outcome,
                reason_code=reason,
                decision_at_micros=context.now_micros,
                enrv_estimate_paise=enrv,
                rank=rank,
                observable_features={
                    "prior_self_recovery_rate": opp.prior_self_recovery_rate,
                    "value_at_risk_paise": opp.value_at_risk_paise,
                },
            )

        for opp in eligible:
            if opp.opportunity_id not in decisions_by_id:
                decisions_by_id[opp.opportunity_id] = BaselineDecision(
                    policy_id=self.policy_id,
                    policy_name=BASELINE_NAMES[self.policy_id],
                    strategy_version=self.strategy_version,
                    cycle_id=context.cycle_id,
                    opportunity_id=opp.opportunity_id,
                    action_code=ActionCode.A00,
                    outcome=DecisionOutcome.NO_ACTION,
                    reason_code="B3_BELOW_EPSILON",
                    decision_at_micros=context.now_micros,
                )

        ordered = tuple(
            decisions_by_id[o.opportunity_id]
            for o in sorted(eligible, key=lambda x: x.opportunity_id)
        )
        return BaselineCycleResult(
            policy_id=self.policy_id,
            cycle_id=context.cycle_id,
            decisions=ordered,
        )
