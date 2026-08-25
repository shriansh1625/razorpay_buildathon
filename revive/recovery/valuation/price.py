"""Counterfactual recovery valuation entry — no ranking or allocation."""

from __future__ import annotations

import hashlib

from revive.config.policy_pack import PolicyPack
from revive.domain.enums import ActionCode
from revive.recovery.candidates.models import CandidateSetResult, RecoveryCandidate
from revive.recovery.context.models import ContextObject
from revive.recovery.diagnosis.models import Diagnosis
from revive.recovery.sentinel.models import DetectedOpportunity
from revive.recovery.valuation.config import ValuationConfig, default_valuation_config, valuation_config_for_policy
from revive.recovery.valuation.enrv import compute_enrv
from revive.recovery.valuation.models import CandidateValuation, ValuationResult
from revive.recovery.valuation.predictor import (
    estimate_action_probability,
    estimate_natural_probability,
)


def _valuation_id(candidate_id: str, strategy_version: str) -> str:
    digest = hashlib.sha256(f"{candidate_id}:{strategy_version}".encode()).hexdigest()[:16]
    return f"val_{digest}"


def _value_drivers(
    candidate: RecoveryCandidate,
    uplift: float,
    p_action: float,
    p_natural: float,
) -> tuple[str, ...]:
    drivers: list[str] = []
    if candidate.action_code == ActionCode.A00:
        drivers.append("no_action_reference")
        return tuple(drivers)
    if uplift > 0:
        drivers.append("positive_uplift")
    elif uplift < 0:
        drivers.append("negative_uplift")
    else:
        drivers.append("zero_uplift")
    if p_natural > 0.5:
        drivers.append("high_natural_recovery_baseline")
    if p_action > p_natural:
        drivers.append("action_improves_recovery_estimate")
    if candidate.nominal_cost_paise > 0:
        drivers.append("direct_cost")
    tier = candidate.params.get("incentive_tier", "TIER_0")
    if tier != "TIER_0":
        drivers.append("incentive_tier")
    return tuple(drivers)


def _price_one(
    candidate: RecoveryCandidate,
    opportunity: DetectedOpportunity,
    context: ContextObject,
    diagnosis: Diagnosis,
    natural_prob,
    cfg: ValuationConfig,
) -> CandidateValuation:
    if candidate.action_code == ActionCode.A00:
        action_prob = natural_prob
    else:
        action_prob = estimate_action_probability(
            opportunity,
            context,
            diagnosis,
            candidate.action_code,
            natural_prob.mean,
            cfg,
        )
    components = compute_enrv(
        candidate,
        opportunity,
        context,
        action_prob,
        natural_prob,
        cfg,
    )
    provenance = (
        f"valuation_version={cfg.valuation_version}",
        f"strategy_version={cfg.strategy_version}",
        f"predictor_cell={action_prob.predictor_cell_ref}",
        f"shrinkage_level={action_prob.shrinkage_level}",
    )
    return CandidateValuation(
        valuation_id=_valuation_id(candidate.candidate_id, cfg.strategy_version),
        candidate_id=candidate.candidate_id,
        opportunity_id=candidate.opportunity_id,
        cycle_id=candidate.cycle_id,
        action_code=candidate.action_code,
        p_action=components.p_action,
        p_natural=components.p_natural,
        uplift=components.uplift,
        sigma=components.sigma,
        predictor_cell_ref=action_prob.predictor_cell_ref,
        shrinkage_level=action_prob.shrinkage_level,
        gross_paise=components.gross_paise,
        cost_paise=components.cost_paise,
        expected_incentive_paise=components.expected_incentive_paise,
        fatigue_cost_paise=components.fatigue_cost_paise,
        enrv_paise=components.enrv_paise,
        enrv_lo_paise=components.enrv_lo_paise,
        enrv_hi_paise=components.enrv_hi_paise,
        valuation_version=cfg.valuation_version,
        strategy_version=cfg.strategy_version,
        provenance=provenance,
        value_drivers=_value_drivers(
            candidate,
            components.uplift,
            components.p_action,
            components.p_natural,
        ),
    )


def price_candidates(
    opportunity: DetectedOpportunity,
    context: ContextObject,
    diagnosis: Diagnosis,
    candidate_set: CandidateSetResult,
    now_micros: int,
    policy: PolicyPack | None = None,
    config: ValuationConfig | None = None,
) -> ValuationResult:
    """Value every candidate independently — enumeration, not selection."""
    if config is not None:
        cfg = config
    elif policy is not None:
        cfg = valuation_config_for_policy(policy)
        if policy.metadata.get("lambda_fatigue") is not None:
            cfg = ValuationConfig(
                net_retention_factor=cfg.net_retention_factor,
                lambda_fatigue=float(policy.metadata["lambda_fatigue"]),
                prior_weight=cfg.prior_weight,
                shrinkage_kappa_parent=cfg.shrinkage_kappa_parent,
                shrinkage_kappa_root=cfg.shrinkage_kappa_root,
                action_uplift_delta=cfg.action_uplift_delta,
                incentive_tier_paise=cfg.incentive_tier_paise,
                valuation_version=cfg.valuation_version,
                strategy_version=cfg.strategy_version,
                epsilon_paise_provisional=policy.epsilon_paise,
            )
    else:
        cfg = default_valuation_config()

    natural_prob = estimate_natural_probability(opportunity, context, diagnosis, cfg)
    valuations: list[CandidateValuation] = []
    for candidate in sorted(candidate_set.candidates, key=lambda c: c.action_code.value):
        valuations.append(
            _price_one(candidate, opportunity, context, diagnosis, natural_prob, cfg)
        )

    return ValuationResult(
        opportunity_id=opportunity.opportunity_id,
        cycle_id=candidate_set.cycle_id,
        produced_at_micros=now_micros,
        valuations=tuple(valuations),
        valuation_version=cfg.valuation_version,
        strategy_version=cfg.strategy_version,
        p_natural=natural_prob.mean,
    )


def simulate(
    opportunity: DetectedOpportunity,
    context: ContextObject,
    diagnosis: Diagnosis,
    candidate_set: CandidateSetResult,
    now_micros: int,
    policy: PolicyPack | None = None,
    config: ValuationConfig | None = None,
) -> ValuationResult:
    """Alias for valuation simulation without execution."""
    return price_candidates(
        opportunity,
        context,
        diagnosis,
        candidate_set,
        now_micros,
        policy=policy,
        config=config,
    )
