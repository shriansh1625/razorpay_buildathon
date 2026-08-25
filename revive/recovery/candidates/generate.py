"""Candidate Generator — C-06 feasibility enumeration (M6)."""

from __future__ import annotations

import json

from revive.benchmark.config import DEFAULT_ACTION_COSTS_PAISE
from revive.config.policy_pack import PolicyPack, default_draft_policy_pack
from revive.domain.enums import ActionCode
from revive.recovery.candidates.config import CandidateConfig, config_from_policy_pack
from revive.recovery.candidates.catalogue import resources_for
from revive.recovery.candidates.feasibility import evaluate_feasibility
from revive.recovery.candidates.models import CandidateCapacityContext, CandidateSetResult, RecoveryCandidate
from revive.recovery.candidates.rules import (
    default_params_for,
    enumerate_action_codes,
    prefers_delayed_retry,
    primary_cause,
)
from revive.recovery.context.models import ContextObject
from revive.recovery.diagnosis.models import Diagnosis
from revive.recovery.sentinel.models import DetectedOpportunity
from revive.simulation.ids import deterministic_id


def _params_key(params: dict) -> str:
    if not params:
        return "{}"
    return json.dumps(params, sort_keys=True, separators=(",", ":"))


def _candidate_id(opportunity_id: str, action: ActionCode, params: dict, version: str) -> str:
    return str(
        deterministic_id(
            "cand",
            f"{opportunity_id}:{action.value}:{_params_key(params)}:{version}",
        )
    )


def generate_candidates(
    opportunity: DetectedOpportunity,
    context: ContextObject,
    diagnosis: Diagnosis,
    now_micros: int,
    cycle_id: str = "",
    policy: PolicyPack | None = None,
    capacity: CandidateCapacityContext | None = None,
    config: CandidateConfig | None = None,
) -> CandidateSetResult:
    """Enumerate feasible recovery candidates — no ranking or ENRV."""
    pack = policy or default_draft_policy_pack()
    cfg = config or config_from_policy_pack(pack.metadata)
    pack_version = pack.version
    cause = primary_cause(diagnosis)

    delay = cfg.issuer_downtime_delay_minutes if prefers_delayed_retry(cause) else cfg.scheduled_retry_delay_minutes

    action_codes = enumerate_action_codes(opportunity.risk_class, diagnosis)
    seen: set[tuple[str, str]] = set()
    candidates: list[RecoveryCandidate] = []

    for action in sorted(action_codes, key=lambda a: a.value):
        params = default_params_for(
            action,
            delay_minutes=delay,
            incentive_tier="TIER_1" if action in {ActionCode.A10, ActionCode.A11} else "TIER_0",
        )
        key = (action.value, _params_key(params))
        if key in seen:
            continue
        seen.add(key)

        availability, satisfied, failed, reasons, earliest, approval = evaluate_feasibility(
            opportunity,
            context,
            diagnosis,
            action,
            params,
            now_micros,
            cfg,
            capacity,
        )

        provenance = ["cause_actionability", "risk_class_rules", "policy_pack"]
        if opportunity.degradation_flag:
            provenance.append("degradation_context")

        candidates.append(
            RecoveryCandidate(
                candidate_id=_candidate_id(
                    opportunity.opportunity_id, action, params, cfg.generator_version
                ),
                opportunity_id=opportunity.opportunity_id,
                cycle_id=cycle_id,
                action_code=action,
                params=params,
                availability_status=availability,
                prerequisites_satisfied=satisfied,
                prerequisites_failed=failed,
                resource_requirements=resources_for(action),
                nominal_cost_paise=DEFAULT_ACTION_COSTS_PAISE.get(action, 0),
                earliest_eligible_at_micros=earliest,
                approval_required=approval,
                reason_codes=tuple(dict.fromkeys(reasons)),
                provenance=tuple(dict.fromkeys(provenance)),
                policy_pack_version=pack_version,
            )
        )

    candidates.sort(key=lambda c: (c.action_code.value, _params_key(c.params)))

    return CandidateSetResult(
        opportunity_id=opportunity.opportunity_id,
        cycle_id=cycle_id,
        produced_at_micros=now_micros,
        candidates=tuple(candidates),
        generator_version=cfg.generator_version,
        policy_pack_version=pack_version,
    )


def simulate(
    opportunity: DetectedOpportunity,
    context: ContextObject,
    diagnosis: Diagnosis,
    now_micros: int,
    cycle_id: str = "",
    policy: PolicyPack | None = None,
    capacity: CandidateCapacityContext | None = None,
    config: CandidateConfig | None = None,
) -> CandidateSetResult:
    """M5→M6 pipeline alias."""
    return generate_candidates(
        opportunity,
        context,
        diagnosis,
        now_micros,
        cycle_id=cycle_id,
        policy=policy,
        capacity=capacity,
        config=config,
    )
