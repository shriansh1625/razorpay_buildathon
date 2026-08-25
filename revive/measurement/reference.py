"""No-action counterfactual reference — evaluator boundary only."""

from __future__ import annotations

from revive.domain.enums import ActionCode
from revive.domain.timestamps import VirtualTimestamp
from revive.recovery.valuation.money import bankers_round_paise
from revive.recovery.valuation.models import CandidateValuation
from revive.simulation.oracle._partition import OraclePartition
from revive.simulation.oracle.resolve import resolve_outcome


def predicted_no_action_reference_paise(
    valuation: CandidateValuation,
    value_at_risk_paise: int,
    *,
    net_retention: float = 1.0,
) -> int:
    """M7 predicted natural recovery: p(i,∅) · V(i) · m."""
    return bankers_round_paise(
        valuation.p_natural * value_at_risk_paise * net_retention
    )


def realized_no_action_reference_paise(
    partition: OraclePartition,
    opportunity_id: str,
    action_time_micros: int,
    value_at_risk_paise: int,
    *,
    horizon_minutes: int,
) -> int:
    """
    Oracle counterfactual for A00 — measurement/evaluator boundary only.

    docs/17 §4.8 oracle_counterfactual_paise — never exposed to decision path.
    """
    result = resolve_outcome(
        partition,
        opportunity_id,
        ActionCode.A00,
        VirtualTimestamp(action_time_micros),
        horizon_minutes=horizon_minutes,
        value_at_risk_paise=value_at_risk_paise,
    )
    return result.recovered_amount_paise
