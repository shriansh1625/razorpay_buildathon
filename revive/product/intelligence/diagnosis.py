"""AI diagnosis orchestration — product sandbox only."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from revive.domain.enums import ActionCode, CauseCode
from revive.product.catalog import action_label
from revive.product.intelligence.config import GROQ_MODEL, AI_SCHEMA_VERSION, ai_configured
from revive.product.intelligence.groq_client import GroqError, complete_structured, system_prompt
from revive.product.intelligence.schemas import (
    CandidateActionProposal,
    DiagnosisProposal,
    DiagnosisResult,
    parse_proposal,
)
from revive.product.project import counterfactual_lab
from revive.product.trace import OpportunityTrace


def _cause_codes() -> list[str]:
    return sorted(c.value for c in CauseCode)


def _action_codes() -> list[str]:
    return sorted(a.value for a in ActionCode)


def build_observation(trace: OpportunityTrace) -> dict[str, Any]:
    opp = trace.opportunity
    ctx = trace.diagnosis.observable_context
    deterministic_causes = [
        rc.cause_code.value for rc in trace.diagnosis.ranked_causes[:5]
    ]
    engine_candidates = [
        {
            "action_id": c.action_code.value,
            "label": action_label(c.action_code.value),
            "availability": c.availability_status.value,
        }
        for c in trace.candidates[:8]
    ]
    return {
        "opportunity_id": opp.opportunity_id,
        "risk_class": opp.risk_class.value,
        "value_at_risk_paise": opp.value_at_risk_paise,
        "addressable": opp.addressable,
        "evidence_facts": dict(opp.evidence.facts),
        "signal_ids": list(opp.evidence.signal_ids),
        "deterministic_ranked_causes": deterministic_causes,
        "engine_candidates": engine_candidates,
        "context": {
            "customer_id": ctx.customer.customer_id if ctx.customer else None,
            "payment": asdict(ctx.payment) if ctx.payment else None,
            "checkout": asdict(ctx.checkout) if ctx.checkout else None,
            "subscription": asdict(ctx.subscription) if ctx.subscription else None,
            "receivable": asdict(ctx.receivable) if ctx.receivable else None,
        },
        "allowed_cause_codes": _cause_codes(),
        "allowed_action_ids": _action_codes(),
    }


def deterministic_fallback(trace: OpportunityTrace) -> DiagnosisProposal:
    opp = trace.opportunity
    ranked = trace.diagnosis.ranked_causes
    primary = ranked[0].cause_code.value if ranked else CauseCode.UNCLASSIFIED.value
    observed = [
        f"{k}={v}" for k, v in list(trace.opportunity.evidence.facts.items())[:8]
    ]
    inference = [
        "Deterministic taxonomy ranking applied (llm_used=false on engine path).",
    ]
    if trace.diagnosis.unclassified:
        inference.append("Cause remains partially unclassified under closed taxonomy.")
    conf = 0.55 if primary != CauseCode.UNCLASSIFIED.value else 0.35
    if ranked:
        band = ranked[0].confidence_band.value
        if band == "HIGH":
            conf = 0.85
        elif band == "MEDIUM":
            conf = 0.65
        elif band == "LOW":
            conf = 0.45
    candidates: list[CandidateActionProposal] = []
    for cand in trace.candidates[:4]:
        if cand.action_code == ActionCode.A00:
            continue
        candidates.append(
            CandidateActionProposal(
                action_id=cand.action_code.value,
                reason=f"Engine candidate catalogue entry ({action_label(cand.action_code.value)}).",
                expected_context_fit="Catalogue candidate ({})".format(cand.availability_status.value),
            )
        )
    missing: list[str] = []
    if not observed:
        missing.append("No discrete evidence facts at detection.")
    return DiagnosisProposal(
        opportunity_id=opp.opportunity_id,
        primary_cause=primary,
        cause_confidence=conf,
        observed_evidence=tuple(observed),
        inference_notes=tuple(inference),
        candidate_actions=tuple(candidates),
        missing_evidence=tuple(missing),
        risk_flags=tuple(),
        uncertainty="Deterministic fallback — no external model call.",
    )


def economic_decision(trace: OpportunityTrace) -> dict[str, Any]:
    lab = counterfactual_lab(trace)
    selected = None
    if trace.assignment:
        selected = action_label(trace.assignment.action_code.value)
    return {
        "authority": "deterministic_engine",
        "selected_action": selected,
        "selection_rationale": lab.get("selection_rationale"),
        "allocator_explanation": lab.get("allocator_explanation"),
        "note": "ENRV and guardrails are authoritative. AI proposals never override economics or safety.",
    }


def diagnose_opportunity(trace: OpportunityTrace) -> DiagnosisResult:
    if not ai_configured():
        proposal = deterministic_fallback(trace)
        return DiagnosisResult(
            proposal=proposal,
            source="deterministic_fallback",
            status="DETERMINISTIC_FALLBACK",
            model=None,
            provider=None,
        )

    observation = build_observation(trace)
    user_msg = (
        "Return a DiagnosisProposal JSON object for this sandbox opportunity.\n"
        "Use primary_cause from allowed_cause_codes and action_id from allowed_action_ids.\n"
        "observed_evidence must cite only facts present in evidence_facts or context.\n"
        "inference_notes must be clearly inferential.\n\n"
        f"OBSERVATION:\n{observation}"
    )
    try:
        raw = complete_structured(
            [
                {"role": "system", "content": system_prompt()},
                {"role": "user", "content": user_msg},
            ]
        )
        proposal = parse_proposal(
            raw,
            expected_opportunity_id=trace.opportunity.opportunity_id,
            evidence_facts=observation.get("evidence_facts"),
            context=observation.get("context"),
        )
        return DiagnosisResult(
            proposal=proposal,
            source="groq",
            status="AI_COMPLETED",
            model=GROQ_MODEL,
            provider="groq",
        )
    except (GroqError, ValueError, RuntimeError) as exc:
        proposal = deterministic_fallback(trace)
        return DiagnosisResult(
            proposal=proposal,
            source="deterministic_fallback",
            status="AI_UNAVAILABLE",
            model=GROQ_MODEL,
            provider="groq",
            error=str(exc)[:240],
        )


def intelligence_event(result: DiagnosisResult) -> dict[str, Any]:
    from datetime import datetime, timezone

    return {
        "event": "AI_DIAGNOSIS_COMPLETED",
        "status": result.status,
        "source": result.source,
        "model": result.model,
        "provider": result.provider,
        "opportunity_id": result.proposal.opportunity_id,
        "primary_cause": result.proposal.primary_cause,
        "schema_version": AI_SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "layer": "product_sandbox_overlay",
        "money_path": False,
        "note": "Overlay diagnosis. Not an engine money-path event.",
    }
