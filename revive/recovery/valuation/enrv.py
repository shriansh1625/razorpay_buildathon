"""ENRV computation — exact documented component sum (RR-FUNC-029)."""

from __future__ import annotations

from dataclasses import dataclass

from revive.domain.enums import ActionCode
from revive.recovery.candidates.models import RecoveryCandidate
from revive.recovery.context.models import ContextObject
from revive.recovery.sentinel.models import DetectedOpportunity
from revive.recovery.valuation.config import ValuationConfig
from revive.recovery.valuation.costs import (
    direct_cost_paise,
    fatigue_cost_paise,
    incentive_paise,
)
from revive.recovery.valuation.money import bankers_round_paise
from revive.recovery.valuation.predictor import ProbabilityEstimate


@dataclass(frozen=True, slots=True)
class EnrvComponents:
    p_action: float
    p_natural: float
    uplift: float
    sigma: float
    gross_paise: int
    cost_paise: int
    expected_incentive_paise: int
    fatigue_cost_paise: int
    enrv_paise: int
    enrv_lo_paise: int
    enrv_hi_paise: int


def _enrv_interval(
    uplift: float,
    sigma_u: float,
    p_action: float,
    sigma_action: float,
    value_paise: int,
    m: float,
    cost_paise: int,
    incentive_paise: int,
    fatigue_cost: int,
) -> tuple[int, int]:
    """Conservative interval from uplift variance (docs/11 §7.1)."""
    u_lo = uplift - sigma_u
    u_hi = uplift + sigma_u
    p_lo = max(0.0, p_action - sigma_action)
    p_hi = min(1.0, p_action + sigma_action)
    gross_lo = bankers_round_paise(u_lo * value_paise * m)
    gross_hi = bankers_round_paise(u_hi * value_paise * m)
    enrv_lo = gross_lo - cost_paise - bankers_round_paise(p_hi * incentive_paise) - fatigue_cost
    enrv_hi = gross_hi - cost_paise - bankers_round_paise(p_lo * incentive_paise) - fatigue_cost
    return enrv_lo, enrv_hi


def compute_enrv(
    candidate: RecoveryCandidate,
    opportunity: DetectedOpportunity,
    context: ContextObject,
    action_prob: ProbabilityEstimate,
    natural_prob: ProbabilityEstimate,
    cfg: ValuationConfig,
) -> EnrvComponents:
    if candidate.action_code == ActionCode.A00:
        return EnrvComponents(
            p_action=natural_prob.mean,
            p_natural=natural_prob.mean,
            uplift=0.0,
            sigma=0.0,
            gross_paise=0,
            cost_paise=0,
            expected_incentive_paise=0,
            fatigue_cost_paise=0,
            enrv_paise=0,
            enrv_lo_paise=0,
            enrv_hi_paise=0,
        )

    p_action = action_prob.mean
    p_natural = natural_prob.mean
    uplift = p_action - p_natural
    sigma_u = (action_prob.sigma ** 2 + natural_prob.sigma ** 2) ** 0.5

    value_paise = opportunity.value_at_risk_paise
    m = cfg.net_retention_factor
    gross_paise = bankers_round_paise(uplift * value_paise * m)

    cost_paise = direct_cost_paise(candidate)
    incentive = incentive_paise(candidate, cfg)
    expected_incentive_paise = bankers_round_paise(p_action * incentive)
    fatigue_cost = fatigue_cost_paise(candidate, context, opportunity, cfg)

    enrv_paise = gross_paise - cost_paise - expected_incentive_paise - fatigue_cost
    enrv_lo, enrv_hi = _enrv_interval(
        uplift,
        sigma_u,
        p_action,
        action_prob.sigma,
        value_paise,
        m,
        cost_paise,
        incentive,
        fatigue_cost,
    )
    if enrv_lo > enrv_paise:
        enrv_lo = enrv_paise
    if enrv_hi < enrv_paise:
        enrv_hi = enrv_paise

    return EnrvComponents(
        p_action=p_action,
        p_natural=p_natural,
        uplift=uplift,
        sigma=sigma_u,
        gross_paise=gross_paise,
        cost_paise=cost_paise,
        expected_incentive_paise=expected_incentive_paise,
        fatigue_cost_paise=fatigue_cost,
        enrv_paise=enrv_paise,
        enrv_lo_paise=enrv_lo,
        enrv_hi_paise=enrv_hi,
    )
