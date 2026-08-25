"""Structured error taxonomy for REVIVE."""

from revive.errors.exceptions import (
    ConfigurationError,
    IllegalStateTransitionError,
    InvariantViolationError,
    ReviveError,
)

__all__ = [
    "ReviveError",
    "IllegalStateTransitionError",
    "InvariantViolationError",
    "ConfigurationError",
]
