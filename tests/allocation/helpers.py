"""Shared builders for allocation tests."""

from __future__ import annotations

from revive.domain.enums import ActionCode, CandidateAvailability
from revive.recovery.candidates.models import RecoveryCandidate, ResourceRequirement
from revive.recovery.valuation.models import CandidateValuation
from revive.allocation.models import PortfolioItem, PricedCandidate
from revive.allocation.resources import priced_candidate


def make_valuation(
    candidate_id: str,
    opportunity_id: str,
    action: ActionCode,
    enrv_paise: int,
    cycle_id: str = "cyc_test",
) -> CandidateValuation:
    return CandidateValuation(
        valuation_id=f"val_{candidate_id}",
        candidate_id=candidate_id,
        opportunity_id=opportunity_id,
        cycle_id=cycle_id,
        action_code=action,
        p_action=0.5,
        p_natural=0.3,
        uplift=0.2,
        sigma=0.05,
        predictor_cell_ref="test",
        shrinkage_level=2,
        gross_paise=enrv_paise,
        cost_paise=0,
        expected_incentive_paise=0,
        fatigue_cost_paise=0,
        enrv_paise=enrv_paise,
        enrv_lo_paise=enrv_paise - 100,
        enrv_hi_paise=enrv_paise + 100,
        valuation_version="test",
        strategy_version="test",
        provenance=("test",),
        value_drivers=("test",),
    )


def make_candidate(
    opportunity_id: str,
    action: ActionCode,
    resources: tuple[ResourceRequirement, ...] = (),
    candidate_suffix: str = "",
) -> RecoveryCandidate:
    cid = f"cand_{opportunity_id}_{action.value}{candidate_suffix}"
    return RecoveryCandidate(
        candidate_id=cid,
        opportunity_id=opportunity_id,
        cycle_id="cyc_test",
        action_code=action,
        params={"channel": "SMS", "incentive_tier": "TIER_0"},
        availability_status=CandidateAvailability.AVAILABLE,
        prerequisites_satisfied=(),
        prerequisites_failed=(),
        resource_requirements=resources,
        nominal_cost_paise=0,
        earliest_eligible_at_micros=None,
        approval_required=False,
        reason_codes=(),
        provenance=("test",),
        policy_pack_version="test",
    )


def make_item(
    opportunity_id: str,
    customer_id: str,
    value_at_risk_paise: int,
    priced: tuple[PricedCandidate, ...],
) -> PortfolioItem:
    return PortfolioItem(
        opportunity_id=opportunity_id,
        customer_id=customer_id,
        value_at_risk_paise=value_at_risk_paise,
        candidates=priced,
    )


def priced(
    opportunity_id: str,
    action: ActionCode,
    enrv_paise: int,
    resources: tuple[ResourceRequirement, ...] = (),
    incentive_tier: str = "TIER_0",
) -> PricedCandidate:
    cand = make_candidate(opportunity_id, action, resources)
    cand = RecoveryCandidate(
        candidate_id=cand.candidate_id,
        opportunity_id=cand.opportunity_id,
        cycle_id=cand.cycle_id,
        action_code=cand.action_code,
        params={"channel": "SMS", "incentive_tier": incentive_tier},
        availability_status=cand.availability_status,
        prerequisites_satisfied=cand.prerequisites_satisfied,
        prerequisites_failed=cand.prerequisites_failed,
        resource_requirements=resources,
        nominal_cost_paise=cand.nominal_cost_paise,
        earliest_eligible_at_micros=cand.earliest_eligible_at_micros,
        approval_required=cand.approval_required,
        reason_codes=cand.reason_codes,
        provenance=cand.provenance,
        policy_pack_version=cand.policy_pack_version,
    )
    val = make_valuation(cand.candidate_id, opportunity_id, action, enrv_paise)
    return priced_candidate(cand, val)
