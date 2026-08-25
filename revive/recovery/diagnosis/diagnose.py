"""Root Cause Analyst — deterministic diagnosis path (C-05, M5)."""

from __future__ import annotations

from revive.domain.enums import CauseCode
from revive.recovery.context.models import ContextObject
from revive.recovery.diagnosis.config import DiagnosisConfig, default_diagnosis_config
from revive.recovery.diagnosis.models import Diagnosis
from revive.recovery.diagnosis.rules import rank_causes
from revive.recovery.sentinel.models import DetectedOpportunity
from revive.simulation.ids import deterministic_id
from revive.simulation.observation import ObservableWorldView


def diagnose(
    opportunity: DetectedOpportunity,
    context: ContextObject,
    view: ObservableWorldView,
    now_micros: int,
    cycle_id: str = "",
    config: DiagnosisConfig | None = None,
) -> Diagnosis:
    """Produce a structured, action-agnostic diagnosis for one opportunity."""
    del view  # reserved for future evidence row lookups; M5 uses assembled context
    cfg = config or default_diagnosis_config()
    if opportunity.opportunity_id != context.opportunity_id:
        raise ValueError("opportunity_id mismatch between opportunity and context")

    ranked = rank_causes(opportunity, context)
    unclassified = (
        len(ranked) == 0
        or (len(ranked) == 1 and ranked[0].cause_code == CauseCode.UNCLASSIFIED)
        or all(rc.cause_code == CauseCode.UNCLASSIFIED for rc in ranked)
    )
    deterministic = any(
        rc.cause_code != CauseCode.UNCLASSIFIED for rc in ranked
    ) or unclassified

    provenance: list[str] = ["payment_history", "temporal_context"]
    if context.payment:
        provenance.append("transaction")
    if context.checkout:
        provenance.append("checkout_state")
    if context.subscription:
        provenance.append("subscription_state")
    if context.receivable:
        provenance.append("invoice_ageing")
    if opportunity.degradation_flag:
        provenance.append("degradation_signal")

    diagnosis_id = deterministic_id(
        "dg",
        f"{opportunity.opportunity_id}:{now_micros}:{cfg.diagnostic_version}",
    )
    return Diagnosis(
        diagnosis_id=str(diagnosis_id),
        opportunity_id=opportunity.opportunity_id,
        cycle_id=cycle_id,
        produced_at_micros=now_micros,
        ranked_causes=ranked,
        unclassified=unclassified,
        observable_context=context,
        deterministic_mapping_applied=deterministic,
        diagnostic_version=cfg.diagnostic_version,
        feature_schema_version=context.feature_schema_version,
        llm_used=False,
        llm_cache_hit=False,
        provenance=tuple(dict.fromkeys(provenance)),
    )


def understand(
    opportunity: DetectedOpportunity,
    view: ObservableWorldView,
    now_micros: int,
    cycle_id: str = "",
    context_config=None,
    diagnosis_config: DiagnosisConfig | None = None,
) -> Diagnosis:
    """M4→M5 pipeline: assemble context then diagnose."""
    from revive.recovery.context.assemble import assemble_context

    context = assemble_context(opportunity, view, now_micros, context_config)
    return diagnose(
        opportunity,
        context,
        view,
        now_micros,
        cycle_id=cycle_id,
        config=diagnosis_config,
    )
