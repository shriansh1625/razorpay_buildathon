"""Generic state machine with explicit legal transitions (RR-NFR-043)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, Iterable, TypeVar

from revive.errors.exceptions import IllegalStateTransitionError

S = TypeVar("S", bound=Enum)


@dataclass(frozen=True, slots=True)
class TransitionSpec:
    from_state: Enum
    to_state: Enum
    trigger: str | None = None


def transition(from_state: Enum, to_state: Enum, *, trigger: str | None = None) -> TransitionSpec:
    return TransitionSpec(from_state=from_state, to_state=to_state, trigger=trigger)


@dataclass
class StateMachine(Generic[S]):
    name: str
    transitions: frozenset[tuple[Enum, Enum]]
    initial_states: frozenset[Enum] | None = None
    terminal_states: frozenset[Enum] | None = None
    illegal_pairs: frozenset[tuple[Enum, Enum]] | None = None

    def validate(self, from_state: S | None, to_state: S, *, trigger: str | None = None) -> S:
        if from_state is None:
            if self.initial_states and to_state not in self.initial_states:
                raise IllegalStateTransitionError(
                    self.name,
                    "<none>",
                    to_state.value,
                    trigger=trigger,
                )
            return to_state

        if self.terminal_states and from_state in self.terminal_states:
            raise IllegalStateTransitionError(
                self.name,
                from_state.value,
                to_state.value,
                trigger=trigger,
            )

        if self.illegal_pairs and (from_state, to_state) in self.illegal_pairs:
            raise IllegalStateTransitionError(
                self.name,
                from_state.value,
                to_state.value,
                trigger=trigger,
            )

        if (from_state, to_state) not in self.transitions:
            raise IllegalStateTransitionError(
                self.name,
                from_state.value,
                to_state.value,
                trigger=trigger,
            )
        return to_state

    def legal_targets(self, from_state: S) -> frozenset[S]:
        return frozenset(
            to  # type: ignore[misc]
            for src, to in self.transitions
            if src == from_state
        )

    def is_terminal(self, state: S) -> bool:
        return self.terminal_states is not None and state in self.terminal_states


def build_transition_set(specs: Iterable[TransitionSpec]) -> frozenset[tuple[Enum, Enum]]:
    return frozenset((spec.from_state, spec.to_state) for spec in specs)
