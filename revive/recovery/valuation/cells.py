"""Predictor cell keys and hierarchical shrinkage — docs/11 §4.3, docs/35 §2."""

from __future__ import annotations

from dataclasses import dataclass

from revive.domain.enums import ActionCode
from revive.recovery.sentinel.models import DetectedOpportunity
from revive.recovery.valuation.config import ValuationConfig


@dataclass(frozen=True, slots=True)
class CellKey:
    risk_class: str
    cause_code: str
    action_code: str
    customer_segment: str

    def as_tuple(self) -> tuple[str, str, str, str]:
        return (self.risk_class, self.cause_code, self.action_code, self.customer_segment)

    def cell_ref(self) -> str:
        return "|".join(self.as_tuple())

    def parent(self) -> tuple[str, str, str]:
        return (self.risk_class, self.cause_code, self.action_code)

    def root(self) -> tuple[str, str]:
        return (self.risk_class, self.action_code)


@dataclass(frozen=True, slots=True)
class BetaEstimate:
    mean: float
    sigma: float
    shrinkage_level: int
    cell_ref: str
    alpha: float
    beta: float


def cell_key_for(
    opportunity: DetectedOpportunity,
    action: ActionCode,
    cause_code: str,
    segment: str,
) -> CellKey:
    return CellKey(
        risk_class=opportunity.risk_class.value,
        cause_code=cause_code,
        action_code=action.value if action != ActionCode.A00 else "NATURAL",
        customer_segment=segment,
    )


def beta_from_prior(prior_mean: float, prior_weight: float) -> tuple[float, float]:
    p = min(0.99, max(0.01, prior_mean))
    alpha = p * prior_weight
    beta = (1.0 - p) * prior_weight
    return max(alpha, 0.01), max(beta, 0.01)


def beta_mean_sigma(alpha: float, beta: float) -> tuple[float, float]:
    total = alpha + beta
    mean = alpha / total
    sigma = (alpha * beta / (total ** 2 * (total + 1))) ** 0.5
    return mean, sigma


def shrinkage_estimate(
    cell_prior: float,
    parent_prior: float,
    root_prior: float,
    n_observed: int,
    cfg: ValuationConfig,
) -> BetaEstimate:
    """Three-level shrinkage with n=0 development cells — inflated sigma."""
    if n_observed == 0 and cell_prior == parent_prior == root_prior:
        # Bit-identical to three-level mix when all priors match (n=0 cells).
        alpha, beta = beta_from_prior(cell_prior, cfg.prior_weight)
        p = alpha / (alpha + beta)
        k1 = cfg.shrinkage_kappa_parent
        k2 = cfg.shrinkage_kappa_root
        mean = (k1 * p + k2 * p) / (k1 + k2)
        level = 2
        eff_alpha = mean * cfg.prior_weight
        eff_beta = (1.0 - mean) * cfg.prior_weight
        sigma = min(0.5, beta_mean_sigma(eff_alpha, eff_beta)[1] * 2.0)
    else:
        k1 = cfg.shrinkage_kappa_parent
        k2 = cfg.shrinkage_kappa_root
        alpha, beta = beta_from_prior(cell_prior, cfg.prior_weight)
        parent_alpha, parent_beta = beta_from_prior(parent_prior, cfg.prior_weight)
        root_alpha, root_beta = beta_from_prior(root_prior, cfg.prior_weight)
        parent_mean = parent_alpha / (parent_alpha + parent_beta)
        root_mean = root_alpha / (root_alpha + root_beta)
        mean = (n_observed * (alpha / (alpha + beta)) + k1 * parent_mean + k2 * root_mean) / (
            n_observed + k1 + k2
        )
        level = 2 if n_observed == 0 else 0
        eff_alpha = mean * cfg.prior_weight
        eff_beta = (1.0 - mean) * cfg.prior_weight
        sigma = beta_mean_sigma(eff_alpha, eff_beta)[1]
        if n_observed == 0:
            sigma = min(0.5, sigma * 2.0)
    return BetaEstimate(
        mean=mean,
        sigma=sigma,
        shrinkage_level=level,
        cell_ref=f"shrunk:{mean:.6f}",
        alpha=eff_alpha,
        beta=eff_beta,
    )
