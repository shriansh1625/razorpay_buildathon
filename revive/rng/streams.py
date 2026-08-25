"""Seeded, labelled PRNG streams — one stream per subsystem for auditability."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Final

# Closed set of stream labels used across REVIVE (extend in later milestones).
STREAM_LABELS: Final[frozenset[str]] = frozenset(
    {
        "dataset",
        "generator",
        "oracle",
        "predictor",
        "allocator",
        "execution",
        "approval_sim",
        "exploration",
        "approver",
        "customer_generation",
        "transaction_generation",
        "checkout_generation",
        "failure_generation",
        "environment_conditions",
        "response_generation",
    }
)


@dataclass
class PRNGStream:
    """Deterministic random stream derived from master seed + label."""

    label: str
    _rng: random.Random = field(repr=False)

    def __post_init__(self) -> None:
        if self.label not in STREAM_LABELS:
            raise ValueError(f"unknown PRNG stream label: {self.label!r}")

    def random(self) -> float:
        return self._rng.random()

    def randint(self, a: int, b: int) -> int:
        return self._rng.randint(a, b)

    def choice(self, seq):
        return self._rng.choice(seq)

    def getstate(self):
        return self._rng.getstate()

    def setstate(self, state) -> None:
        self._rng.setstate(state)


def _derive_seed(master_seed: int, label: str) -> int:
    digest = hashlib.sha256(f"{master_seed}:{label}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


@dataclass
class PRNGStreamRegistry:
    """Factory for labelled streams sharing a master seed."""

    master_seed: int

    def stream(self, label: str) -> PRNGStream:
        seed = _derive_seed(self.master_seed, label)
        return PRNGStream(label=label, _rng=random.Random(seed))

    def snapshot(self) -> dict[str, object]:
        return {label: self.stream(label).getstate() for label in sorted(STREAM_LABELS)}
