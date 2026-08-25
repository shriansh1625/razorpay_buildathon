"""State machine tests — RR-NFR-043."""

import pytest

from revive.domain.enums import OpportunityState
from revive.errors import IllegalStateTransitionError
from revive.state import opportunity_machine


def test_opportunity_has_fifteen_states():
    assert len(OpportunityState) == 15


def test_legal_detected_to_diagnosed():
    opportunity_machine.validate(
        OpportunityState.DETECTED,
        OpportunityState.DIAGNOSED,
    )


@pytest.mark.parametrize(
    ("src", "dst"),
    [
        (OpportunityState.PRICED, OpportunityState.ACTING),
        (OpportunityState.AUTHORISED, OpportunityState.AUTHORISED),
        (OpportunityState.RECOVERED, OpportunityState.PRICED),
        (OpportunityState.AWAITING_APPROVAL, OpportunityState.ACTING),
    ],
)
def test_illegal_opportunity_transitions_raise(src, dst):
    with pytest.raises(IllegalStateTransitionError):
        opportunity_machine.validate(src, dst)


def test_terminal_reconciliation_failed_blocks_exit():
    with pytest.raises(IllegalStateTransitionError):
        opportunity_machine.validate(
            OpportunityState.RECONCILIATION_FAILED,
            OpportunityState.PRICED,
        )
