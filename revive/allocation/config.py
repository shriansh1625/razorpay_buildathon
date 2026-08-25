"""Allocator configuration — PROVISIONAL until benchmark freeze."""

from __future__ import annotations

from dataclasses import dataclass

ALLOCATOR_VERSION = "0.8.0-m8"

# Subgradient iterations (deterministic in k — docs/10 §5.1).
DEFAULT_K_MAX = 40
DEFAULT_STEP_SCALE = 50.0
DEFAULT_DUALITY_TOLERANCE = 0.05

# Benchmark mode uses iteration cap, not wall clock (RR-NFR-020).
DEFAULT_ITERATION_BUDGET = 40


@dataclass(frozen=True, slots=True)
class AllocatorConfig:
    k_max: int = DEFAULT_K_MAX
    step_scale: float = DEFAULT_STEP_SCALE
    duality_tolerance: float = DEFAULT_DUALITY_TOLERANCE
    iteration_budget: int = DEFAULT_ITERATION_BUDGET
    allocator_version: str = ALLOCATOR_VERSION
    force_fallback: bool = False

    def step(self, k: int) -> float:
        return self.step_scale / (k + 1) ** 0.5


def default_allocator_config() -> AllocatorConfig:
    return AllocatorConfig()
