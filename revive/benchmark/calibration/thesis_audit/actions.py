"""Action categorization for thesis audit."""

from __future__ import annotations

from revive.domain.enums import ActionCode

_RETRY = frozenset({ActionCode.A01, ActionCode.A02, ActionCode.A03})
_MESSAGE = frozenset({ActionCode.A04, ActionCode.A05})
_VOICE = frozenset()  # no dedicated voice-only code in v1 catalogue
_INCENTIVE = frozenset({ActionCode.A06})
_HUMAN = frozenset({ActionCode.A07, ActionCode.A14})
_MANDATE = frozenset({ActionCode.A08})
_CHECKOUT = frozenset({ActionCode.A09})
_DEFER = frozenset({ActionCode.A12})
_NO_ACTION = frozenset({ActionCode.A00})


def action_category(code: ActionCode) -> str:
    if code in _NO_ACTION:
        return "no_action"
    if code in _RETRY:
        return "retry"
    if code in _MESSAGE:
        return "message"
    if code in _VOICE:
        return "voice"
    if code in _INCENTIVE:
        return "incentive"
    if code in _HUMAN:
        return "human"
    if code in _MANDATE:
        return "mandate"
    if code in _CHECKOUT:
        return "checkout"
    if code in _DEFER:
        return "defer"
    return "other"
