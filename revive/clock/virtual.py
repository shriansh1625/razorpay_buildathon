"""Virtual clock — advances only on explicit calls (RR-NFR-045 tolerance for late signals)."""

from __future__ import annotations

from dataclasses import dataclass, field

from revive.domain.timestamps import VirtualTimestamp


@dataclass
class VirtualClock:
    """Monotonic virtual-time source."""

    _now: VirtualTimestamp = field(default_factory=VirtualTimestamp.zero)

    @property
    def now(self) -> VirtualTimestamp:
        return self._now

    def set(self, timestamp: VirtualTimestamp) -> None:
        if timestamp < self._now:
            raise ValueError(
                f"virtual clock cannot move backwards: {timestamp} < {self._now}"
            )
        self._now = timestamp

    def advance_minutes(self, minutes: int) -> VirtualTimestamp:
        if minutes < 0:
            raise ValueError("minutes must be non-negative")
        self._now = self._now.add_minutes(minutes)
        return self._now

    def advance_seconds(self, seconds: int) -> VirtualTimestamp:
        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        self._now = self._now.add_seconds(seconds)
        return self._now

    def snapshot(self) -> VirtualTimestamp:
        return self._now
