"""Observable world state updates after execution."""

from __future__ import annotations

from revive.domain.enums import InterventionState, OpportunityState
from revive.simulation.types import AdapterResult, OutcomeKind
from revive.state.transitions import intervention_machine, opportunity_machine

from revive.execution.environment import ExecutionEnvironment
from revive.execution.models import RealizedOutcome


def transition_opportunity_state(
    env: ExecutionEnvironment,
    adapter_result: AdapterResult,
    realized: RealizedOutcome | None,
) -> str:
    """Apply legal opportunity state transitions after execution."""
    current = env.opportunity_state
    if current == OpportunityState.AUTHORISED:
        if (current, OpportunityState.ACTING) in opportunity_machine.transitions:
            env.opportunity_state = OpportunityState.ACTING
            current = env.opportunity_state

    if current == OpportunityState.ACTING:
        if adapter_result == AdapterResult.TIMEOUT_UNKNOWN:
            if (current, OpportunityState.RECONCILING) in opportunity_machine.transitions:
                env.opportunity_state = OpportunityState.RECONCILING
        elif (current, OpportunityState.AWAITING_OUTCOME) in opportunity_machine.transitions:
            env.opportunity_state = OpportunityState.AWAITING_OUTCOME
            current = env.opportunity_state

    if current == OpportunityState.AWAITING_OUTCOME and realized is not None:
        if realized.recovered_amount_paise > 0 and realized.observed_within_horizon:
            if (current, OpportunityState.RECOVERED) in opportunity_machine.transitions:
                env.opportunity_state = OpportunityState.RECOVERED
        elif realized.outcome_kind == OutcomeKind.NOT_RECOVERED:
            if (current, OpportunityState.PRICED) in opportunity_machine.transitions:
                env.opportunity_state = OpportunityState.PRICED

    return env.opportunity_state.value


def intervention_state_for(adapter_result: AdapterResult) -> InterventionState:
    if adapter_result == AdapterResult.SUCCESS:
        return InterventionState.COMPLETED_SUCCESS
    if adapter_result == AdapterResult.TIMEOUT_UNKNOWN:
        return InterventionState.UNKNOWN
    if adapter_result == AdapterResult.FAILED_RETRYABLE:
        return InterventionState.COMPLETED_FAILED
    if adapter_result in {
        AdapterResult.FAILED_TERMINAL,
        AdapterResult.REJECTED_BY_PROVIDER,
    }:
        return InterventionState.COMPLETED_FAILED
    return InterventionState.COMPLETED_FAILED


def payment_state_for(
    action_code: str,
    adapter_result: AdapterResult,
    realized: RealizedOutcome | None,
) -> str | None:
    if action_code not in {"A01", "A02", "A03"}:
        return None
    if adapter_result == AdapterResult.SUCCESS:
        if realized and realized.recovered_amount_paise > 0:
            return "payment_success"
        return "payment_pending"
    if adapter_result == AdapterResult.TIMEOUT_UNKNOWN:
        return "payment_unknown"
    return "payment_failed"


def customer_response_for(adapter_result: AdapterResult) -> str | None:
    if adapter_result == AdapterResult.SUCCESS:
        return "delivered"
    if adapter_result == AdapterResult.REJECTED_BY_PROVIDER:
        return "rejected"
    if adapter_result == AdapterResult.TIMEOUT_UNKNOWN:
        return "unknown"
    return "failed"


def apply_intervention_transition(
    current: InterventionState,
    target: InterventionState,
) -> InterventionState:
    if (current, target) in intervention_machine.transitions:
        return target
    return current
