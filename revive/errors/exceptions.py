"""Exception hierarchy — illegal transitions raise, never silently absorb (RR-NFR-043)."""

from __future__ import annotations


class ReviveError(Exception):
    """Base for all REVIVE domain errors."""


class IllegalStateTransitionError(ReviveError):
    """Raised when a state machine receives an illegal transition."""

    def __init__(
        self,
        machine: str,
        from_state: str,
        to_state: str,
        *,
        trigger: str | None = None,
    ) -> None:
        self.machine = machine
        self.from_state = from_state
        self.to_state = to_state
        self.trigger = trigger
        detail = f"{machine}: illegal transition {from_state!r} -> {to_state!r}"
        if trigger:
            detail += f" (trigger={trigger!r})"
        super().__init__(detail)


class InvariantViolationError(ReviveError):
    """Raised when a domain invariant is violated (e.g. DM-*, RR-NFR-041)."""


class ConfigurationError(ReviveError):
    """Raised when configuration or policy pack is invalid or unfrozen where required."""
