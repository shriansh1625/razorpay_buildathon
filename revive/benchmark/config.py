"""Baseline configuration — shared constraints and provisional B1 schedule."""

from __future__ import annotations

from dataclasses import dataclass

from revive.domain.enums import ActionCode, RiskClass

# PROVISIONAL — publish before benchmark freeze (docs/20 BF-9, ADR-013 draft).
B1_RETRY_SCHEDULE: dict[RiskClass, tuple[tuple[int, ActionCode], ...]] = {
    RiskClass.PAYMENT_FAILURE: (
        (0, ActionCode.A01),
        (30, ActionCode.A02),
        (120, ActionCode.A02),
        (360, ActionCode.A03),
    ),
    RiskClass.CHECKOUT_ABANDONMENT: (
        (60, ActionCode.A09),
        (180, ActionCode.A05),
        (360, ActionCode.A04),
    ),
    RiskClass.SUBSCRIPTION_FAILURE: (
        (0, ActionCode.A01),
        (60, ActionCode.A08),
        (240, ActionCode.A02),
    ),
    RiskClass.RECEIVABLE_OVERDUE: (
        (0, ActionCode.A05),
        (1440, ActionCode.A05),
        (4320, ActionCode.A08),
    ),
    RiskClass.MANDATE_HEALTH: (
        (0, ActionCode.A08),
        (1440, ActionCode.A11),
    ),
}

# Provisional action costs (paise) — centralized, not hard-coded in policies.
DEFAULT_ACTION_COSTS_PAISE: dict[ActionCode, int] = {
    ActionCode.A00: 0,
    ActionCode.A01: 100,
    ActionCode.A02: 100,
    ActionCode.A03: 500,
    ActionCode.A04: 300,
    ActionCode.A05: 300,
    ActionCode.A06: 1000,
    ActionCode.A07: 5000,
    ActionCode.A08: 400,
    ActionCode.A09: 300,
    ActionCode.A10: 0,
    ActionCode.A11: 200,
    ActionCode.A12: 0,
    ActionCode.A13: 800,
    ActionCode.A14: 5000,
}

# Default contact action per risk class for B2 CONTACT_ALL.
CONTACT_ALL_DEFAULT_ACTION: dict[RiskClass, ActionCode] = {
    RiskClass.PAYMENT_FAILURE: ActionCode.A01,
    RiskClass.CHECKOUT_ABANDONMENT: ActionCode.A09,
    RiskClass.SUBSCRIPTION_FAILURE: ActionCode.A01,
    RiskClass.RECEIVABLE_OVERDUE: ActionCode.A05,
    RiskClass.MANDATE_HEALTH: ActionCode.A08,
}


@dataclass(frozen=True, slots=True)
class BaselineEnvironmentConfig:
    """Shared environment constraints — identical for all baselines (BF-4)."""

    contact_allowance_per_customer: int = 2
    retry_slots_per_cycle: int = 50
    message_capacity_per_cycle: int = 100
    action_costs_paise: dict[ActionCode, int] | None = None

    def cost_for(self, action: ActionCode) -> int:
        costs = self.action_costs_paise or DEFAULT_ACTION_COSTS_PAISE
        return costs.get(action, 0)


def default_baseline_environment_config() -> BaselineEnvironmentConfig:
    return BaselineEnvironmentConfig(action_costs_paise=dict(DEFAULT_ACTION_COSTS_PAISE))
