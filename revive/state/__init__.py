"""Explicit state machines with legal-transition tables."""

from revive.state.machine import StateMachine, transition
from revive.state.transitions import (
    APPROVAL_REQUEST_TRANSITIONS,
    CYCLE_TRANSITIONS,
    INTERVENTION_TRANSITIONS,
    OPPORTUNITY_ILLEGAL_TRANSITIONS,
    OPPORTUNITY_TRANSITIONS,
    RESERVATION_HANDLE_TRANSITIONS,
    RUN_TRANSITIONS,
    approval_request_machine,
    cycle_machine,
    intervention_machine,
    opportunity_machine,
    reservation_handle_machine,
    run_machine,
)

__all__ = [
    "StateMachine",
    "transition",
    "OPPORTUNITY_TRANSITIONS",
    "OPPORTUNITY_ILLEGAL_TRANSITIONS",
    "INTERVENTION_TRANSITIONS",
    "APPROVAL_REQUEST_TRANSITIONS",
    "RESERVATION_HANDLE_TRANSITIONS",
    "CYCLE_TRANSITIONS",
    "RUN_TRANSITIONS",
    "opportunity_machine",
    "intervention_machine",
    "approval_request_machine",
    "reservation_handle_machine",
    "cycle_machine",
    "run_machine",
]
