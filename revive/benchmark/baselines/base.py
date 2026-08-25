"""Baseline policy protocol."""

from __future__ import annotations

from typing import Protocol

from revive.benchmark.config import BaselineEnvironmentConfig
from revive.benchmark.types import (
    BaselineCycleContext,
    BaselineCycleResult,
    BaselinePolicyId,
    ObservableOpportunity,
)


class BaselinePolicy(Protocol):
    policy_id: BaselinePolicyId
    strategy_version: str

    def decide_cycle(
        self,
        opportunities: list[ObservableOpportunity],
        context: BaselineCycleContext,
        env: BaselineEnvironmentConfig,
        epsilon_paise: int,
    ) -> BaselineCycleResult: ...
