"""Baseline cycle runner — development validation only, not official benchmark."""

from __future__ import annotations

from revive.benchmark.baselines import get_baseline
from revive.benchmark.config import BaselineEnvironmentConfig, default_baseline_environment_config
from revive.benchmark.types import (
    BaselineCycleContext,
    BaselineCycleResult,
    BaselinePolicyId,
    ObservableOpportunity,
)
from revive.config.policy_pack import PolicyPack
from revive.simulation.observation import ObservableWorldView


def opportunities_from_observable(view: ObservableWorldView) -> list[ObservableOpportunity]:
    customer_lookup = {c["customer_id"]: c for c in view.customers}
    return [
        ObservableOpportunity.from_dict(o, customer_lookup) for o in view.opportunities
    ]


def run_baseline_cycle(
    policy_id: BaselinePolicyId,
    view: ObservableWorldView,
    *,
    cycle_id: str,
    now_micros: int,
    policy_pack: PolicyPack | None = None,
    env: BaselineEnvironmentConfig | None = None,
    persist_context: BaselineCycleContext | None = None,
) -> BaselineCycleResult:
    """Run one baseline decision cycle on observable state only."""
    from revive.config import default_draft_policy_pack

    pack = policy_pack or default_draft_policy_pack()
    environment = env or default_baseline_environment_config()
    policy = get_baseline(policy_id)

    if persist_context is not None:
        context = persist_context
        context.cycle_id = cycle_id
        context.now_micros = now_micros
        context.retry_slots_used = 0
        context.message_capacity_used = 0
    else:
        context = BaselineCycleContext(
            cycle_id=cycle_id,
            now_micros=now_micros,
            epsilon_paise=pack.epsilon_paise,
            contact_allowance_per_customer=environment.contact_allowance_per_customer,
            retry_slots_per_cycle=environment.retry_slots_per_cycle,
            message_capacity_per_cycle=environment.message_capacity_per_cycle,
        )

    opportunities = opportunities_from_observable(view)
    return policy.decide_cycle(opportunities, context, environment, pack.epsilon_paise)
