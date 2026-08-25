"""
Observable-only ENRV heuristic for baseline B3.

NOT the REVIVE counterfactual engine (M7+). Uses only observable proxies.
"""

from __future__ import annotations

from revive.benchmark.config import BaselineEnvironmentConfig
from revive.benchmark.types import ObservableOpportunity
from revive.domain.enums import ActionCode

# Fixed observable heuristics — not oracle-derived.
_ACTION_UPLIFT_DELTA: dict[ActionCode, float] = {
    ActionCode.A00: 0.0,
    ActionCode.A01: 0.08,
    ActionCode.A02: 0.10,
    ActionCode.A03: 0.12,
    ActionCode.A04: 0.06,
    ActionCode.A05: 0.05,
    ActionCode.A06: 0.15,
    ActionCode.A07: 0.04,
    ActionCode.A08: 0.07,
    ActionCode.A09: 0.11,
    ActionCode.A10: 0.03,
    ActionCode.A11: 0.02,
    ActionCode.A12: 0.0,
    ActionCode.A13: 0.01,
    ActionCode.A14: 0.01,
}


def estimate_enrv(
    opportunity: ObservableOpportunity,
    action: ActionCode,
    env: BaselineEnvironmentConfig,
) -> int:
    """Heuristic ENRV from observable features only."""
    if action == ActionCode.A00:
        return 0

    base = opportunity.prior_self_recovery_rate
    uplift = _ACTION_UPLIFT_DELTA.get(action, 0.0)
    if opportunity.in_degradation_window and action == ActionCode.A01:
        uplift *= 0.5

    success_prob = min(1.0, max(0.0, base + uplift))
    gross = int(opportunity.value_at_risk_paise * success_prob)
    cost = env.cost_for(action)
    fatigue = opportunity.contacts_made * 200
    return gross - cost - fatigue


def best_action_for_opportunity(
    opportunity: ObservableOpportunity,
    candidates: tuple[ActionCode, ...],
    env: BaselineEnvironmentConfig,
    epsilon_paise: int,
) -> tuple[ActionCode, int]:
    best_action = ActionCode.A00
    best_enrv = 0
    for action in candidates:
        enrv = estimate_enrv(opportunity, action, env)
        if enrv > best_enrv:
            best_enrv = enrv
            best_action = action
    if best_enrv <= epsilon_paise:
        return ActionCode.A00, 0
    return best_action, best_enrv
