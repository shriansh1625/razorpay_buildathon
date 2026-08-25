"""Valuation configuration — PROVISIONAL until StrategyVersion sealed."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from revive.config.policy_pack import PolicyPack

VALUATION_VERSION = "0.7.0-m7"
STRATEGY_VERSION = "strat_m7_dev"
BENCHMARK_STRATEGY_VERSION = "strat_m7_benchmark_v1"

# Merchant net retention (ASSUMPTION default 1.0 — docs/11 §5.1).
DEFAULT_NET_RETENTION = 1.0

# Fatigue externality dial (PROPOSED — docs/11 §5.1).
DEFAULT_LAMBDA_FATIGUE = 1.0

# Beta prior pseudo-count (PROPOSED — docs/35 §2.2).
DEFAULT_PRIOR_WEIGHT = 10.0

# Hierarchical shrinkage κ (PROPOSED — docs/11 §4.3).
DEFAULT_SHRINKAGE_KAPPA_PARENT = 5.0
DEFAULT_SHRINKAGE_KAPPA_ROOT = 10.0

# Observable action uplift deltas for development priors (PROVISIONAL — not oracle).
DEFAULT_ACTION_UPLIFT_DELTA: dict[str, float] = {
    "A00": 0.0,
    "A01": 0.06,
    "A02": 0.08,
    "A03": 0.10,
    "A04": 0.05,
    "A05": 0.04,
    "A06": 0.12,
    "A07": 0.03,
    "A08": 0.06,
    "A09": 0.09,
    "A10": 0.02,
    "A11": 0.02,
    "A12": 0.01,
    "A13": 0.01,
    "A14": 0.01,
}

# Incentive amounts by tier (PROVISIONAL paise).
DEFAULT_INCENTIVE_TIER_PAISE: dict[str, int] = {
    "TIER_0": 0,
    "TIER_1": 500,
    "TIER_2": 1500,
    "TIER_3": 3000,
}


@dataclass(frozen=True, slots=True)
class ValuationConfig:
    net_retention_factor: float = DEFAULT_NET_RETENTION
    lambda_fatigue: float = DEFAULT_LAMBDA_FATIGUE
    prior_weight: float = DEFAULT_PRIOR_WEIGHT
    shrinkage_kappa_parent: float = DEFAULT_SHRINKAGE_KAPPA_PARENT
    shrinkage_kappa_root: float = DEFAULT_SHRINKAGE_KAPPA_ROOT
    action_uplift_delta: dict[str, float] | None = None
    incentive_tier_paise: dict[str, int] | None = None
    valuation_version: str = VALUATION_VERSION
    strategy_version: str = STRATEGY_VERSION
    # ADR-011 provisional — centralized, not embedded in formulas.
    epsilon_paise_provisional: int = 0

    def uplift_delta(self, action_code: str) -> float:
        table = self.action_uplift_delta or DEFAULT_ACTION_UPLIFT_DELTA
        return table.get(action_code, 0.0)

    def incentive_paise(self, tier: str) -> int:
        table = self.incentive_tier_paise or DEFAULT_INCENTIVE_TIER_PAISE
        return table.get(tier, 0)


def default_valuation_config() -> ValuationConfig:
    return ValuationConfig(
        action_uplift_delta=dict(DEFAULT_ACTION_UPLIFT_DELTA),
        incentive_tier_paise=dict(DEFAULT_INCENTIVE_TIER_PAISE),
        strategy_version=STRATEGY_VERSION,
    )


def official_valuation_config(epsilon_paise: int) -> ValuationConfig:
    """Frozen benchmark valuation — strategy and ε bound to sealed PolicyPack."""
    return ValuationConfig(
        action_uplift_delta=dict(DEFAULT_ACTION_UPLIFT_DELTA),
        incentive_tier_paise=dict(DEFAULT_INCENTIVE_TIER_PAISE),
        valuation_version=VALUATION_VERSION,
        strategy_version=BENCHMARK_STRATEGY_VERSION,
        epsilon_paise_provisional=epsilon_paise,
    )


def valuation_config_for_policy(policy: "PolicyPack") -> ValuationConfig:
    """Single ε source: PolicyPack.epsilon_paise drives valuation metadata."""
    if policy.is_frozen_for_benchmark:
        return official_valuation_config(policy.epsilon_paise)
    base = default_valuation_config()
    return ValuationConfig(
        net_retention_factor=base.net_retention_factor,
        lambda_fatigue=base.lambda_fatigue,
        prior_weight=base.prior_weight,
        shrinkage_kappa_parent=base.shrinkage_kappa_parent,
        shrinkage_kappa_root=base.shrinkage_kappa_root,
        action_uplift_delta=base.action_uplift_delta,
        incentive_tier_paise=base.incentive_tier_paise,
        valuation_version=base.valuation_version,
        strategy_version=base.strategy_version,
        epsilon_paise_provisional=policy.epsilon_paise,
    )
