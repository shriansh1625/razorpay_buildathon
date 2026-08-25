"""Delayed execution scheduler — virtual time only."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from revive.execution.models import AuthorisedAction, ExecutionResult


@dataclass
class ScheduledExecution:
    scheduled_at_micros: int
    authorised: AuthorisedAction
    context: dict[str, Any]


@dataclass
class DelayScheduler:
    """Schedule A02 and other delayed actions at future virtual times."""

    _pending: list[ScheduledExecution] = field(default_factory=list)

    def schedule(
        self,
        authorised: AuthorisedAction,
        scheduled_at_micros: int,
        context: dict[str, Any] | None = None,
    ) -> ScheduledExecution:
        entry = ScheduledExecution(
            scheduled_at_micros=scheduled_at_micros,
            authorised=authorised,
            context=dict(context or {}),
        )
        self._pending.append(entry)
        self._pending.sort(key=lambda s: s.scheduled_at_micros)
        return entry

    def pending_count(self) -> int:
        return len(self._pending)

    def drain_until(
        self,
        now_micros: int,
        executor: Callable[..., ExecutionResult],
        **executor_kwargs: Any,
    ) -> list[ExecutionResult]:
        """Execute all scheduled actions whose time has arrived."""
        results: list[ExecutionResult] = []
        ready: list[ScheduledExecution] = []
        remaining: list[ScheduledExecution] = []
        for entry in self._pending:
            if entry.scheduled_at_micros <= now_micros:
                ready.append(entry)
            else:
                remaining.append(entry)
        self._pending = remaining
        for entry in ready:
            kwargs = dict(executor_kwargs)
            kwargs.update(entry.context)
            results.append(executor(entry.authorised, **kwargs))
        return results

    def cancel_expired(self, now_micros: int, expires_at_micros: int) -> int:
        """Remove pending entries that can no longer execute."""
        before = len(self._pending)
        self._pending = [
            e
            for e in self._pending
            if e.scheduled_at_micros <= expires_at_micros
            and expires_at_micros >= now_micros
        ]
        return before - len(self._pending)
