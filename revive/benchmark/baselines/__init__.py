"""Baseline policy registry."""

from __future__ import annotations

from revive.benchmark.baselines.b0_no_action import NoActionBaseline
from revive.benchmark.baselines.b1_fixed_retry import FixedRetryBaseline
from revive.benchmark.baselines.b2_contact_all import ContactAllBaseline
from revive.benchmark.baselines.b3_greedy_enrv import GreedyEnrvBaseline
from revive.benchmark.baselines.base import BaselinePolicy
from revive.benchmark.types import BaselinePolicyId

_REGISTRY: dict[BaselinePolicyId, BaselinePolicy] = {
    BaselinePolicyId.B0: NoActionBaseline(),
    BaselinePolicyId.B1: FixedRetryBaseline(),
    BaselinePolicyId.B2: ContactAllBaseline(),
    BaselinePolicyId.B3: GreedyEnrvBaseline(),
}


def get_baseline(policy_id: BaselinePolicyId) -> BaselinePolicy:
    return _REGISTRY[policy_id]


def all_baselines() -> tuple[BaselinePolicy, ...]:
    return tuple(_REGISTRY[policy_id] for policy_id in BaselinePolicyId)
