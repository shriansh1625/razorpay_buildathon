"""Decision lifecycle configuration — PROVISIONAL until benchmark freeze."""

from __future__ import annotations

from dataclasses import dataclass

DECISION_LIFECYCLE_VERSION = "0.9.0-m9"

# PROPOSED cycle interval — docs/40 OQ-15 (15 min virtual).
DEFAULT_ALLOCATION_TTL_MICROS = 15 * 60 * 1_000_000


@dataclass(frozen=True, slots=True)
class DecisionLifecycleConfig:
    allocation_ttl_micros: int = DEFAULT_ALLOCATION_TTL_MICROS
    lifecycle_version: str = DECISION_LIFECYCLE_VERSION


def default_lifecycle_config() -> DecisionLifecycleConfig:
    return DecisionLifecycleConfig()
