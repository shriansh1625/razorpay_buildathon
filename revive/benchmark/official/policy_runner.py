"""Run one policy on a cloned shared world."""

from __future__ import annotations

from revive.allocation import ResourceCapacities
from revive.benchmark.capacities import benchmark_resource_capacities, profile_from_string
from revive.config.policy_pack import PolicyPack

from revive.benchmark.official.baseline_pipeline import (
    BaselineRunState,
    new_baseline_state,
    run_baseline_cycle_full,
)
from revive.benchmark.official.metrics import PolicyRunMetrics, compute_policy_metrics
from revive.benchmark.official.policies import BenchmarkPolicyId, to_baseline_id
from revive.benchmark.official.revive_pipeline import (
    ReviveRunState,
    new_revive_state,
    run_revive_cycle,
)
from revive.benchmark.official.world import clone_shared_world, SharedWorldBundle


def run_policy_on_world(
    bundle: SharedWorldBundle,
    policy_id: BenchmarkPolicyId,
    policy_pack: PolicyPack,
    *,
    capacities: ResourceCapacities | None = None,
) -> PolicyRunMetrics:
    """Execute full pipeline for one policy on an independent world clone."""
    cloned = clone_shared_world(bundle)
    profile = profile_from_string(cloned.profile)
    caps = capacities or benchmark_resource_capacities(profile)

    try:
        if policy_id == BenchmarkPolicyId.REVIVE:
            state = new_revive_state(cloned, policy_pack, caps)
            for idx, now_micros in enumerate(cloned.cycle_times_micros):
                run_revive_cycle(state, f"cyc_{idx:04d}", now_micros)
            return compute_policy_metrics(
                policy_id.value,
                cloned.seed,
                cloned.profile,
                tuple(state.measurements),
                tuple(state.executions),
                tuple(state.authorizations),
                incentive_budget_capacity_paise=caps.incentive_budget_paise,
                retry_capacity=caps.retry_slots,
                message_capacity=caps.message_capacity,
            )

        baseline_id = to_baseline_id(policy_id)
        if baseline_id is None:
            raise ValueError(f"Unknown policy {policy_id}")

        state = new_baseline_state(cloned, baseline_id, policy_pack)
        for idx, now_micros in enumerate(cloned.cycle_times_micros):
            run_baseline_cycle_full(state, f"cyc_{idx:04d}", now_micros)

        return compute_policy_metrics(
            policy_id.value,
            cloned.seed,
            cloned.profile,
            tuple(state.measurements),
            tuple(state.executions),
            tuple(state.authorizations),
            incentive_budget_capacity_paise=caps.incentive_budget_paise,
            retry_capacity=caps.retry_slots,
            message_capacity=caps.message_capacity,
        )
    finally:
        del cloned
