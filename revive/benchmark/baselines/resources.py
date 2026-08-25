"""Resource reservation helpers for baseline action selection."""

from __future__ import annotations

from revive.benchmark.types import BaselineCycleContext
from revive.domain.enums import ActionCode

_RETRY_ACTIONS = frozenset({ActionCode.A01, ActionCode.A02, ActionCode.A03})
_MESSAGE_ACTIONS = frozenset(
    {
        ActionCode.A04,
        ActionCode.A05,
        ActionCode.A06,
        ActionCode.A07,
        ActionCode.A09,
        ActionCode.A11,
    }
)


def can_reserve_action(action: ActionCode, customer_id: str, ctx: BaselineCycleContext) -> bool:
    if action in _RETRY_ACTIONS and not ctx.can_use_retry_slot():
        return False
    if action in _MESSAGE_ACTIONS:
        if not ctx.can_use_message_capacity():
            return False
        if not ctx.can_contact(customer_id):
            return False
    return True


def reserve_action(action: ActionCode, customer_id: str, ctx: BaselineCycleContext) -> bool:
    if action in _RETRY_ACTIONS:
        if not ctx.reserve_retry_slot():
            return False
    if action in _MESSAGE_ACTIONS:
        if not ctx.reserve_message_capacity():
            return False
        if not ctx.reserve_contact(customer_id):
            return False
    return True
