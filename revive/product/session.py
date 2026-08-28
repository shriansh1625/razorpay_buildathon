"""Deterministic demonstration session for the Control Room."""

from __future__ import annotations

from dataclasses import dataclass

from revive.allocation.models import ResourceCapacities
from revive.benchmark.official.world import generate_shared_world
from revive.config.policy_pack import default_draft_policy_pack
from revive.product.project import audit_ledger, control_room, latest_traces, opportunity_detail
from revive.product.trace import (
    ProductRunState,
    new_product_state,
    run_traced_cycle,
    settle_scheduled_executions,
)
from revive.execution.models import ExecutionStage
from revive.simulation.config import GeneratorConfig
from revive.simulation.types import GenerationProfile

DEMO_SEED = 14
DEMO_CYCLES = 4


def fixture_label(seed: int = DEMO_SEED) -> str:
    return (
        f"PAYVANTA Sandbox — synthetic test population, seed={seed}. "
        "Bounded local execution. Not official benchmark evidence."
    )


FIXTURE_LABEL = fixture_label(DEMO_SEED)


def demo_generator_config(seed: int = DEMO_SEED) -> GeneratorConfig:
    return GeneratorConfig(
        seed=seed,
        profile=GenerationProfile.BALANCED,
        customer_count=18,
        opportunity_count=34,
        simulation_window_days=1,
        cycle_interval_minutes=180,
        inject_signal_faults=False,
        inject_adversarial_cases=False,
        privacy_canary_count=0,
        metadata={"product": "PAYVANTA", "fixture": "control-room-demo"},
    )


def demo_capacities() -> ResourceCapacities:
    """Tight enough that allocation contention is visible."""
    return ResourceCapacities(
        retry_slots=4,
        message_capacity=6,
        voice_minutes=3,
        human_review_slots=2,
        incentive_budget_paise=150_000,
        contact_allowance_per_customer=2,
    )


@dataclass
class ProductSession:
    state: ProductRunState

    def snapshot(self) -> dict:
        traces = latest_traces(self.state)
        details = {
            t.opportunity.opportunity_id: opportunity_detail(t) for t in traces
        }
        return {
            "control_room": control_room(self.state),
            "opportunities": details,
            "audit_ledger": audit_ledger(self.state),
            "wow_opportunity_id": _wow_opportunity_id(traces),
        }


def _wow_opportunity_id(traces) -> str | None:
    """Pick the most instructive opportunity for the guided reveal.

    Preference order: authorized → executed → measured with positive incremental
    net (the full recovery story), then any executed intervention, then a blocked
    decision (still a complete guardrail story), then whatever exists.
    """
    if not traces:
        return None

    def is_success(t) -> bool:
        if t.measurement is None or t.assignment is None or t.execution is None:
            return False
        if t.assignment.action_code.value == "A00":
            return False
        return (
            t.execution.execution_stage == ExecutionStage.SUCCEEDED
            and t.measurement.realized_net_value_paise > 0
        )

    success = [t for t in traces if is_success(t)]
    if success:
        best = max(
            success,
            key=lambda t: (
                t.measurement.realized_net_value_paise,
                len(t.candidates),
            ),
        )
        return best.opportunity.opportunity_id

    def executed(t) -> bool:
        return t.measurement is not None and t.assignment is not None and (
            t.assignment.action_code.value != "A00"
        )

    recovered = [
        t for t in traces if executed(t) and t.measurement.gross_recovered_paise > 0
    ]
    if recovered:
        best = max(recovered, key=lambda t: t.measurement.gross_recovered_paise)
        return best.opportunity.opportunity_id
    for t in traces:
        if executed(t):
            return t.opportunity.opportunity_id
    for t in traces:
        if t.authorization is not None:
            return t.opportunity.opportunity_id
    return traces[0].opportunity.opportunity_id


def build_demo_session(
    *,
    seed: int = DEMO_SEED,
    cycles: int = DEMO_CYCLES,
) -> ProductSession:
    bundle = generate_shared_world(demo_generator_config(seed))
    pack = default_draft_policy_pack()
    state = new_product_state(
        bundle,
        pack,
        demo_capacities(),
        fixture_label=fixture_label(seed),
    )
    times = bundle.cycle_times_micros[:cycles]
    if not times:
        times = (bundle.config.cycle_interval_minutes * 60 * 1_000_000,)
    for idx, now in enumerate(times):
        run_traced_cycle(state, f"cyc_{idx:04d}", now)
    # Retries authorized in the final cycle are still pending. Advance virtual
    # time past the last scheduled instant so their outcomes are measured rather
    # than left permanently unobservable.
    if state.pending_scheduled:
        horizon = max(p.scheduled_at_micros for p in state.pending_scheduled)
        settle_scheduled_executions(state, horizon)
    return ProductSession(state=state)
