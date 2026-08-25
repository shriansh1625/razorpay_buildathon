"""Action catalogue — resource templates from docs/11 §3."""

from __future__ import annotations

from revive.domain.enums import ActionCode
from revive.recovery.candidates.models import ResourceRequirement

# Resource keys align with docs/11 action catalogue.
_RESOURCE_TEMPLATES: dict[ActionCode, tuple[ResourceRequirement, ...]] = {
    ActionCode.A00: (),
    ActionCode.A01: (ResourceRequirement("retry_slots", 1),),
    ActionCode.A02: (ResourceRequirement("retry_slots", 1),),
    ActionCode.A03: (
        ResourceRequirement("message_capacity", 1),
        ResourceRequirement("contact_allowance", 1),
    ),
    ActionCode.A04: (
        ResourceRequirement("message_capacity", 1),
        ResourceRequirement("contact_allowance", 1),
    ),
    ActionCode.A05: (
        ResourceRequirement("message_capacity", 1),
        ResourceRequirement("contact_allowance", 1),
    ),
    ActionCode.A06: (
        ResourceRequirement("message_capacity", 1),
        ResourceRequirement("contact_allowance", 1),
    ),
    ActionCode.A07: (
        ResourceRequirement("message_capacity", 1),
        ResourceRequirement("contact_allowance", 1),
    ),
    ActionCode.A08: (
        ResourceRequirement("message_capacity", 1),
        ResourceRequirement("contact_allowance", 1),
    ),
    ActionCode.A09: (
        ResourceRequirement("message_capacity", 1),
        ResourceRequirement("contact_allowance", 1),
    ),
    ActionCode.A10: (
        ResourceRequirement("incentive_budget", 1),
        ResourceRequirement("message_capacity", 1),
        ResourceRequirement("contact_allowance", 1),
    ),
    ActionCode.A11: (
        ResourceRequirement("incentive_budget", 1),
        ResourceRequirement("message_capacity", 1),
        ResourceRequirement("contact_allowance", 1),
    ),
    ActionCode.A12: (
        ResourceRequirement("voice_minutes", 5),
        ResourceRequirement("contact_allowance", 1),
    ),
    ActionCode.A13: (ResourceRequirement("human_review_slots", 1),),
    ActionCode.A14: (ResourceRequirement("human_review_slots", 1),),
}

_MESSAGE_ACTIONS = frozenset(
    {
        ActionCode.A03,
        ActionCode.A04,
        ActionCode.A05,
        ActionCode.A06,
        ActionCode.A07,
        ActionCode.A08,
        ActionCode.A09,
        ActionCode.A10,
        ActionCode.A11,
    }
)
_RETRY_ACTIONS = frozenset({ActionCode.A01, ActionCode.A02, ActionCode.A03})
_INCENTIVE_ACTIONS = frozenset({ActionCode.A10, ActionCode.A11})
_HUMAN_ACTIONS = frozenset({ActionCode.A13, ActionCode.A14})


def resources_for(action: ActionCode) -> tuple[ResourceRequirement, ...]:
    return _RESOURCE_TEMPLATES.get(action, ())


def is_message_action(action: ActionCode) -> bool:
    return action in _MESSAGE_ACTIONS


def is_retry_action(action: ActionCode) -> bool:
    return action in _RETRY_ACTIONS


def is_incentive_action(action: ActionCode) -> bool:
    return action in _INCENTIVE_ACTIONS


def is_human_action(action: ActionCode) -> bool:
    return action in _HUMAN_ACTIONS
