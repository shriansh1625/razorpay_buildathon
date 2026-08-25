"""Legal transition tables from docs/34-state-machine.md."""

from __future__ import annotations

from revive.domain.enums import (
    ApprovalRequestState,
    CycleState,
    InterventionState,
    OpportunityState,
    ReservationHandleState,
    RunState,
)
from revive.state.machine import StateMachine, build_transition_set, transition

# --- Opportunity (15 states) ---

_OPPORTUNITY_SPECS = [
    transition(None, OpportunityState.DETECTED, trigger="signal_creates_opportunity"),  # type: ignore[arg-type]
    transition(OpportunityState.DETECTED, OpportunityState.NOT_ADDRESSABLE),
    transition(OpportunityState.DETECTED, OpportunityState.DIAGNOSED),
    transition(OpportunityState.DETECTED, OpportunityState.STOPPED),
    transition(OpportunityState.DETECTED, OpportunityState.RECOVERED),
    transition(OpportunityState.NOT_ADDRESSABLE, OpportunityState.DETECTED),
    transition(OpportunityState.NOT_ADDRESSABLE, OpportunityState.CLOSED_UNRECOVERED),
    transition(OpportunityState.NOT_ADDRESSABLE, OpportunityState.RECOVERED),
    transition(OpportunityState.DIAGNOSED, OpportunityState.PRICED),
    transition(OpportunityState.DIAGNOSED, OpportunityState.STOPPED),
    transition(OpportunityState.PRICED, OpportunityState.AUTHORISED),
    transition(OpportunityState.PRICED, OpportunityState.AWAITING_APPROVAL),
    transition(OpportunityState.PRICED, OpportunityState.DEFERRED),
    transition(OpportunityState.PRICED, OpportunityState.NO_ACTION_CYCLE),
    transition(OpportunityState.PRICED, OpportunityState.STOPPED),
    transition(OpportunityState.AWAITING_APPROVAL, OpportunityState.AUTHORISED),
    transition(OpportunityState.AWAITING_APPROVAL, OpportunityState.PRICED),
    transition(OpportunityState.AWAITING_APPROVAL, OpportunityState.DEFERRED),
    transition(OpportunityState.AWAITING_APPROVAL, OpportunityState.STOPPED),
    transition(OpportunityState.AUTHORISED, OpportunityState.ACTING),
    transition(OpportunityState.AUTHORISED, OpportunityState.DEFERRED),
    transition(OpportunityState.ACTING, OpportunityState.AWAITING_OUTCOME),
    transition(OpportunityState.ACTING, OpportunityState.RECONCILING),
    transition(OpportunityState.AWAITING_OUTCOME, OpportunityState.RECOVERED),
    transition(OpportunityState.AWAITING_OUTCOME, OpportunityState.PRICED),
    transition(OpportunityState.AWAITING_OUTCOME, OpportunityState.STOPPED),
    transition(OpportunityState.AWAITING_OUTCOME, OpportunityState.CLOSED_UNRECOVERED),
    transition(OpportunityState.RECONCILING, OpportunityState.AWAITING_OUTCOME),
    transition(OpportunityState.RECONCILING, OpportunityState.RECONCILIATION_FAILED),
    transition(OpportunityState.RECONCILING, OpportunityState.RECOVERED),
    transition(OpportunityState.DEFERRED, OpportunityState.PRICED),
    transition(OpportunityState.DEFERRED, OpportunityState.STOPPED),
    transition(OpportunityState.DEFERRED, OpportunityState.CLOSED_UNRECOVERED),
    transition(OpportunityState.DEFERRED, OpportunityState.RECOVERED),
    transition(OpportunityState.NO_ACTION_CYCLE, OpportunityState.PRICED),
    transition(OpportunityState.NO_ACTION_CYCLE, OpportunityState.STOPPED),
    transition(OpportunityState.NO_ACTION_CYCLE, OpportunityState.RECOVERED),
    transition(OpportunityState.NO_ACTION_CYCLE, OpportunityState.CLOSED_UNRECOVERED),
    transition(OpportunityState.STOPPED, OpportunityState.PRICED, trigger="external_reopen"),
]

OPPORTUNITY_TRANSITIONS = build_transition_set(_OPPORTUNITY_SPECS)

OPPORTUNITY_ILLEGAL_TRANSITIONS: frozenset[tuple[OpportunityState, OpportunityState]] = frozenset(
    {
        (OpportunityState.PRICED, OpportunityState.ACTING),
        (OpportunityState.AUTHORISED, OpportunityState.AUTHORISED),
        (OpportunityState.ACTING, OpportunityState.ACTING),
        (OpportunityState.RECONCILING, OpportunityState.AUTHORISED),
        (OpportunityState.RECONCILING, OpportunityState.ACTING),
        (OpportunityState.RECONCILIATION_FAILED, OpportunityState.PRICED),
        (OpportunityState.RECOVERED, OpportunityState.PRICED),
        (OpportunityState.CLOSED_UNRECOVERED, OpportunityState.PRICED),
        (OpportunityState.DEFERRED, OpportunityState.ACTING),
        (OpportunityState.AWAITING_APPROVAL, OpportunityState.ACTING),
    }
)

opportunity_machine = StateMachine(
    name="Opportunity",
    transitions=OPPORTUNITY_TRANSITIONS,
    initial_states=frozenset({OpportunityState.DETECTED}),
    terminal_states=frozenset(
        {
            OpportunityState.RECONCILIATION_FAILED,
            OpportunityState.RECOVERED,
            OpportunityState.STOPPED,
            OpportunityState.CLOSED_UNRECOVERED,
        }
    ),
    illegal_pairs=OPPORTUNITY_ILLEGAL_TRANSITIONS,
)

# --- Intervention ---

_INTERVENTION_SPECS = [
    transition(None, InterventionState.INTENDED),  # type: ignore[arg-type]
    transition(InterventionState.INTENDED, InterventionState.IN_FLIGHT),
    transition(InterventionState.IN_FLIGHT, InterventionState.COMPLETED_SUCCESS),
    transition(InterventionState.IN_FLIGHT, InterventionState.COMPLETED_FAILED),
    transition(InterventionState.IN_FLIGHT, InterventionState.UNKNOWN),
    transition(InterventionState.UNKNOWN, InterventionState.RESOLVED_BY_RECONCILIATION),
    transition(InterventionState.UNKNOWN, InterventionState.UNRESOLVED),
]

INTERVENTION_TRANSITIONS = build_transition_set(_INTERVENTION_SPECS)

intervention_machine = StateMachine(
    name="Intervention",
    transitions=INTERVENTION_TRANSITIONS,
    initial_states=frozenset({InterventionState.INTENDED}),
    terminal_states=frozenset(
        {
            InterventionState.COMPLETED_SUCCESS,
            InterventionState.COMPLETED_FAILED,
            InterventionState.RESOLVED_BY_RECONCILIATION,
            InterventionState.UNRESOLVED,
        }
    ),
    illegal_pairs=frozenset(
        {
            (InterventionState.INTENDED, InterventionState.COMPLETED_SUCCESS),
            (InterventionState.INTENDED, InterventionState.COMPLETED_FAILED),
            (InterventionState.UNKNOWN, InterventionState.IN_FLIGHT),
        }
    ),
)

# --- ApprovalRequest ---

_APPROVAL_SPECS = [
    transition(None, ApprovalRequestState.QUEUED),  # type: ignore[arg-type]
    transition(ApprovalRequestState.QUEUED, ApprovalRequestState.APPROVED),
    transition(ApprovalRequestState.QUEUED, ApprovalRequestState.APPROVED_MODIFIED),
    transition(ApprovalRequestState.QUEUED, ApprovalRequestState.REJECTED),
    transition(ApprovalRequestState.QUEUED, ApprovalRequestState.EXPIRED),
    transition(ApprovalRequestState.QUEUED, ApprovalRequestState.VOIDED),
]

APPROVAL_REQUEST_TRANSITIONS = build_transition_set(_APPROVAL_SPECS)

approval_request_machine = StateMachine(
    name="ApprovalRequest",
    transitions=APPROVAL_REQUEST_TRANSITIONS,
    initial_states=frozenset({ApprovalRequestState.QUEUED}),
    terminal_states=frozenset(
        {
            ApprovalRequestState.APPROVED,
            ApprovalRequestState.APPROVED_MODIFIED,
            ApprovalRequestState.REJECTED,
            ApprovalRequestState.EXPIRED,
            ApprovalRequestState.VOIDED,
        }
    ),
    illegal_pairs=frozenset(
        {(ApprovalRequestState.EXPIRED, ApprovalRequestState.APPROVED)}
    ),
)

# --- ReservationHandle ---

_RESERVATION_SPECS = [
    transition(None, ReservationHandleState.HELD),  # type: ignore[arg-type]
    transition(ReservationHandleState.HELD, ReservationHandleState.COMMITTED),
    transition(ReservationHandleState.HELD, ReservationHandleState.RELEASED),
    transition(ReservationHandleState.HELD, ReservationHandleState.RECLAIMED),
]

RESERVATION_HANDLE_TRANSITIONS = build_transition_set(_RESERVATION_SPECS)

reservation_handle_machine = StateMachine(
    name="ReservationHandle",
    transitions=RESERVATION_HANDLE_TRANSITIONS,
    initial_states=frozenset({ReservationHandleState.HELD}),
    terminal_states=frozenset(
        {
            ReservationHandleState.COMMITTED,
            ReservationHandleState.RELEASED,
            ReservationHandleState.RECLAIMED,
        }
    ),
    illegal_pairs=frozenset(
        {
            (ReservationHandleState.COMMITTED, ReservationHandleState.RELEASED),
            (ReservationHandleState.RELEASED, ReservationHandleState.COMMITTED),
            (ReservationHandleState.RELEASED, ReservationHandleState.RELEASED),
        }
    ),
)

# --- Cycle ---

_CYCLE_SPECS = [
    transition(None, CycleState.OPEN),  # type: ignore[arg-type]
    transition(CycleState.OPEN, CycleState.DECIDING),
    transition(CycleState.DECIDING, CycleState.EXECUTING),
    transition(CycleState.EXECUTING, CycleState.VERIFYING),
    transition(CycleState.VERIFYING, CycleState.CLOSED),
    transition(CycleState.OPEN, CycleState.ABORTED),
    transition(CycleState.DECIDING, CycleState.ABORTED),
    transition(CycleState.EXECUTING, CycleState.ABORTED),
    transition(CycleState.VERIFYING, CycleState.ABORTED),
]

CYCLE_TRANSITIONS = build_transition_set(_CYCLE_SPECS)

cycle_machine = StateMachine(
    name="Cycle",
    transitions=CYCLE_TRANSITIONS,
    initial_states=frozenset({CycleState.OPEN}),
    terminal_states=frozenset({CycleState.CLOSED, CycleState.ABORTED}),
)

# --- Run ---

_RUN_SPECS = [
    transition(None, RunState.INITIALISED),  # type: ignore[arg-type]
    transition(RunState.INITIALISED, RunState.RUNNING),
    transition(RunState.RUNNING, RunState.COMPLETED),
    transition(RunState.RUNNING, RunState.INVALIDATED),
    transition(RunState.RUNNING, RunState.ABORTED),
    transition(RunState.INITIALISED, RunState.ABORTED),
]

RUN_TRANSITIONS = build_transition_set(_RUN_SPECS)

run_machine = StateMachine(
    name="Run",
    transitions=RUN_TRANSITIONS,
    initial_states=frozenset({RunState.INITIALISED}),
    terminal_states=frozenset(
        {RunState.COMPLETED, RunState.INVALIDATED, RunState.ABORTED}
    ),
)
