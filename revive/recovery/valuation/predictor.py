"""Observable-only recovery probability estimation — Beta-Binomial + shrinkage."""

from __future__ import annotations

from dataclasses import dataclass

from revive.domain.enums import ActionCode
from revive.recovery.context.models import ContextObject
from revive.recovery.diagnosis.models import Diagnosis
from revive.recovery.sentinel.models import DetectedOpportunity
from revive.recovery.valuation.cells import (
    BetaEstimate,
    cell_key_for,
    shrinkage_estimate,
)
from revive.recovery.valuation.config import ValuationConfig
from revive.recovery.valuation.features import (
    customer_segment,
    observable_action_prior,
    observable_natural_prior,
    top_cause_code,
)


@dataclass(frozen=True, slots=True)
class ProbabilityEstimate:
    mean: float
    sigma: float
    shrinkage_level: int
    predictor_cell_ref: str


def _root_prior(
    opportunity: DetectedOpportunity,
    action: ActionCode,
    cfg: ValuationConfig,
    natural_prior: float,
) -> float:
    if action == ActionCode.A00:
        return natural_prior
    return observable_action_prior(
        natural_prior,
        action,
        cfg.uplift_delta(action.value),
        opportunity,
    )


def estimate_natural_probability(
    opportunity: DetectedOpportunity,
    context: ContextObject,
    diagnosis: Diagnosis,
    cfg: ValuationConfig,
) -> ProbabilityEstimate:
    segment = customer_segment(context)
    cause = top_cause_code(diagnosis)
    cell = cell_key_for(opportunity, ActionCode.A00, cause, segment)
    cell_prior = observable_natural_prior(opportunity, context, diagnosis)
    shrunk = shrinkage_estimate(cell_prior, cell_prior, cell_prior, 0, cfg)
    return ProbabilityEstimate(
        mean=shrunk.mean,
        sigma=shrunk.sigma,
        shrinkage_level=shrunk.shrinkage_level,
        predictor_cell_ref=cell.cell_ref().replace("A00", "NATURAL"),
    )


def estimate_action_probability(
    opportunity: DetectedOpportunity,
    context: ContextObject,
    diagnosis: Diagnosis,
    action: ActionCode,
    natural_prior_mean: float,
    cfg: ValuationConfig,
) -> ProbabilityEstimate:
    if action == ActionCode.A00:
        natural = estimate_natural_probability(opportunity, context, diagnosis, cfg)
        return ProbabilityEstimate(
            mean=natural.mean,
            sigma=natural.sigma,
            shrinkage_level=natural.shrinkage_level,
            predictor_cell_ref=natural.predictor_cell_ref,
        )
    segment = customer_segment(context)
    cause = top_cause_code(diagnosis)
    cell = cell_key_for(opportunity, action, cause, segment)
    cell_prior = observable_action_prior(
        natural_prior_mean,
        action,
        cfg.uplift_delta(action.value),
        opportunity,
    )
    parent_prior = cell_prior
    root_prior = _root_prior(opportunity, action, cfg, natural_prior_mean)
    shrunk = shrinkage_estimate(cell_prior, parent_prior, root_prior, 0, cfg)
    return ProbabilityEstimate(
        mean=shrunk.mean,
        sigma=shrunk.sigma,
        shrinkage_level=shrunk.shrinkage_level,
        predictor_cell_ref=cell.cell_ref(),
    )
