"""Judge-facing recovery simulator. Deterministic engine, labelled fixture."""

from __future__ import annotations

from typing import Any

from revive.allocation.models import ResourceCapacities
from revive.benchmark.official.world import generate_shared_world
from revive.config.policy_pack import default_draft_policy_pack
from revive.product.project import audit_ledger, control_room, latest_traces, opportunity_detail
from revive.product.trace import new_product_state, run_traced_cycle
from revive.simulation.config import GeneratorConfig
from revive.simulation.types import GenerationProfile

RISK_MIX = {
    "PAYMENT_FAILURE": dict(
        failure_mix_payment=1.0,
        failure_mix_checkout=0.0,
        failure_mix_subscription=0.0,
        failure_mix_receivable=0.0,
        failure_mix_mandate=0.0,
    ),
    "CHECKOUT_ABANDONMENT": dict(
        failure_mix_payment=0.0,
        failure_mix_checkout=1.0,
        failure_mix_subscription=0.0,
        failure_mix_receivable=0.0,
        failure_mix_mandate=0.0,
    ),
    "SUBSCRIPTION_FAILURE": dict(
        failure_mix_payment=0.0,
        failure_mix_checkout=0.0,
        failure_mix_subscription=1.0,
        failure_mix_receivable=0.0,
        failure_mix_mandate=0.0,
    ),
    "RECEIVABLE_OVERDUE": dict(
        failure_mix_payment=0.0,
        failure_mix_checkout=0.0,
        failure_mix_subscription=0.0,
        failure_mix_receivable=1.0,
        failure_mix_mandate=0.0,
    ),
}


def run_simulator(
    *,
    failure_type: str = "PAYMENT_FAILURE",
    seed: int = 7,
    opportunity_count: int = 12,
    profile: str = "SCARCE",
    urgency: str = "normal",
) -> dict[str, Any]:
    mix = RISK_MIX.get(failure_type, RISK_MIX["PAYMENT_FAILURE"])
    interval = 60 if urgency == "high" else 180
    config = GeneratorConfig(
        seed=seed,
        profile=GenerationProfile(profile),
        customer_count=max(4, opportunity_count // 2),
        opportunity_count=opportunity_count,
        simulation_window_days=1,
        cycle_interval_minutes=interval,
        inject_signal_faults=False,
        inject_adversarial_cases=False,
        privacy_canary_count=0,
        metadata={"product": "PAYVANTA", "fixture": "recovery-simulator"},
        **mix,
    )
    bundle = generate_shared_world(config)
    caps = ResourceCapacities(
        retry_slots=3,
        message_capacity=4,
        voice_minutes=2,
        human_review_slots=1,
        incentive_budget_paise=80_000,
        contact_allowance_per_customer=1 if urgency == "high" else 2,
    )
    state = new_product_state(
        bundle,
        default_draft_policy_pack(),
        caps,
        fixture_label=(
            "Recovery Simulator — synthetic, deterministic. "
            "Not official benchmark evidence. Diagnosis is a closed taxonomy "
            "(LLM off)."
        ),
    )
    # Payment-only worlds emit signals at the window end; the first cycle is empty.
    times = bundle.cycle_times_micros
    now = times[-1] if times else interval * 60 * 1_000_000
    now = times[-1] if times else interval * 60 * 1_000_000
    run_traced_cycle(state, "cyc_sim_0000", now)
    traces = latest_traces(state)
    details = {t.opportunity.opportunity_id: opportunity_detail(t) for t in traces}
    focus = None
    for t in traces:
        if t.measurement and t.assignment and t.assignment.action_code.value != "A00":
            focus = t.opportunity.opportunity_id
            break
    if focus is None and traces:
        focus = traces[0].opportunity.opportunity_id
    return {
        "inputs": {
            "failure_type": failure_type,
            "seed": seed,
            "opportunity_count": opportunity_count,
            "profile": profile,
            "urgency": urgency,
            "llm_mode": "OFF",
        },
        "control_room": control_room(state),
        "opportunities": details,
        "audit_ledger": audit_ledger(state),
        "focus_opportunity_id": focus,
    }
