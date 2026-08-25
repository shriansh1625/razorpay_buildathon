"""Virtual-time timestamps for deterministic simulation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True, order=True)
class VirtualTimestamp:
    """Monotonic virtual clock instant (UTC, microsecond precision)."""

    epoch_micros: int

    def __post_init__(self) -> None:
        if not isinstance(self.epoch_micros, int) or isinstance(self.epoch_micros, bool):
            raise TypeError("epoch_micros must be int")
        if self.epoch_micros < 0:
            raise ValueError("epoch_micros must be non-negative")

    @classmethod
    def from_datetime(cls, dt: datetime) -> VirtualTimestamp:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        micros = int(dt.timestamp() * 1_000_000)
        return cls(micros)

    @classmethod
    def zero(cls) -> VirtualTimestamp:
        return cls(0)

    def to_datetime(self) -> datetime:
        return datetime.fromtimestamp(self.epoch_micros / 1_000_000, tz=timezone.utc)

    def add_minutes(self, minutes: int) -> VirtualTimestamp:
        if minutes < 0:
            raise ValueError("minutes must be non-negative")
        return VirtualTimestamp(self.epoch_micros + minutes * 60 * 1_000_000)

    def add_seconds(self, seconds: int) -> VirtualTimestamp:
        if seconds < 0:
            raise ValueError("seconds must be non-negative")
        return VirtualTimestamp(self.epoch_micros + seconds * 1_000_000)

    def __str__(self) -> str:
        return self.to_datetime().isoformat()
