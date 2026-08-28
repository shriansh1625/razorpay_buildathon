"""Project engine traces into product JSON. No fabricated fields."""

from __future__ import annotations

from typing import Any

from revive.domain.enums import ActionCode, DecisionOutcome
from revive.policy.models import AuthorizationState
from revive.product.catalog import (
    PIPELINE_STAGES,
    action_label,
    block_label,
    risk_label,
)
from revive.product.money import (
    format_compact_inr,
    format_display_inr,
    format_inr,
    paise_to_inr,
)
from revive.product.trace import CycleTrace, OpportunityTrace, ProductRunState


def _money(paise: int | None) -> dict[str, Any] | None:
    """Every amount travels in four forms so no surface has to reformat one.

    `paise` is the truth, `display` is the exact rupees-and-paise evidence form,
    `read` drops paise once they cannot change a decision, and `compact` is the
    lakh/crore headline form. A surface picks the form its context needs instead
    of rounding a string it was handed.
    """
    if paise is None:
        return None
    return {
        "paise": paise,
        "inr": paise_to_inr(paise),
        "display": format_inr(paise),
        "read": format_display_inr(paise),
        "compact": format_compact_inr(paise),
    }


# The allocator states its reason as a code and, sometimes, one argument:
# ("capacity_binding", "retry_slots"). Those codes are the engine's own vocabulary
# and stay in the payload verbatim, because an auditor should be able to read what
# the allocator actually emitted. But a code is not a reason a reviewer can read,
# so each one is also carried as a sentence. Anything unmapped falls back to the
# code itself rather than to a guess — a new allocator reason should look
# unfamiliar in the UI, not be silently narrated as something it is not.
_ALLOCATOR_REASON: dict[str, str] = {
    "enrv_per_resource_density": (
        "The greedy allocator ranked this action highest on expected incremental "
        "net recovery per unit of scarce resource, and capacity was available."
    ),
    "fallback_capacity_exhausted": (
        "A positive-value action existed, but resource capacity was already "
        "committed to opportunities with a higher recovery-per-resource ratio."
    ),
    "no_action_reference": (
        "No candidate cleared the minimum expected-value threshold, so the "
        "do-nothing reference stands as the decision."
    ),
    "portfolio_adjusted_enrv": (
        "Selected on portfolio-adjusted value: expected incremental net recovery "
        "less the shadow price of the resources this action consumes."
    ),
    "feasible_alternative": (
        "The highest-value action did not fit the capacity still remaining this "
        "cycle, so the best-valued action that did fit was selected instead."
    ),
    "capacity_binding": (
        "Deferred because a resource this action needs was fully reserved by the "
        "time the allocator reached this opportunity."
    ),
    "positive_enrv_no_capacity": (
        "Candidates with positive expected value existed, but no capacity was "
        "left in this cycle to run any of them."
    ),
    "no_feasible_positive_enrv": (
        "No candidate was both eligible under policy and positive on expected "
        "incremental net recovery."
    ),
}

# How each code's argument reads once it is spelled out, and whether the value is a
# paise amount. `rv` is reduced_value_paise, so it is formatted as money — a bare
# 30518 next to ₹-denominated figures elsewhere reads as thirty thousand rupees.
# `density` is paise of expected recovery per normalized resource unit: a ratio, not
# an amount, so it stays as the allocator computed it. Keys absent here keep the raw
# `k=v` token, which is still evidence.
_ALLOCATOR_ARG: dict[str, tuple[str, bool]] = {
    "density": ("recovery per resource unit", False),
    "rv": ("portfolio-adjusted value", True),
}


def _allocator_explanation(explanation: tuple[str, ...] | list[str]) -> dict[str, Any] | None:
    """Split an allocator explanation into its code, its arguments, and a sentence."""
    codes = [str(c) for c in explanation if str(c)]
    if not codes:
        return None
    head = codes[0]
    args: list[dict[str, str]] = []
    for token in codes[1:]:
        key, _, value = token.partition("=")
        if not value:
            # A bare argument is the binding resource name (`capacity_binding`).
            args.append({"label": "binding resource", "value": token})
            continue
        label, is_money = _ALLOCATOR_ARG.get(key, (key, False))
        if is_money:
            try:
                value = format_inr(int(value))
            except ValueError:
                pass
        args.append({"label": label, "value": value})
    return {
        "code": head,
        "codes": codes,
        "sentence": _ALLOCATOR_REASON.get(head),
        "args": args,
    }


def _pipeline(trace: OpportunityTrace) -> list[dict[str, Any]]:
    selected = (
        trace.assignment is not None
        and trace.assignment.outcome == DecisionOutcome.SELECTED
        and trace.assignment.action_code != ActionCode.A00
    )
    guarded = trace.authorization is not None
    authorized = (
        trace.authorization is not None
        and trace.authorization.authorization_state == AuthorizationState.AUTHORIZED
    )
    blocked = (
        trace.authorization is not None
        and trace.authorization.authorization_state != AuthorizationState.AUTHORIZED
    )
    flags = {
        "DETECTED": True,
        "DIAGNOSED": True,
        "OPTIMIZED": True,
        "GUARDED": guarded or (trace.assignment is not None and not selected),
        "AUTHORIZED": authorized,
        "EXECUTED": trace.execution is not None,
        "MEASURED": trace.measurement is not None,
    }
    notes = {
        "DETECTED": trace.opportunity.risk_class.value,
        "DIAGNOSED": (
            trace.diagnosis.primary_category.value
            if trace.diagnosis.primary_category
            else "UNCLASSIFIED"
        ),
        "OPTIMIZED": (
            action_label(trace.assignment.action_code.value)
            if trace.assignment
            else "No assignment"
        ),
        "GUARDED": (
            block_label(trace.authorization.blocking_reason_code)
            if blocked
            else ("Allocator held" if not selected else "Gates evaluated")
        ),
        "AUTHORIZED": (
            trace.authorization.authorization_state.value
            if trace.authorization
            else "Not submitted"
        ),
        "EXECUTED": (
            trace.execution.execution_stage.value if trace.execution else "Not executed"
        ),
        "MEASURED": (
            format_inr(trace.measurement.realized_net_value_paise)
            if trace.measurement
            else "No measurement"
        ),
    }
    # Phase 12 timeline vocabulary: the allocator stage reads as SELECTED to a
    # product audience, while the internal stage name stays OPTIMIZED.
    labels = {"OPTIMIZED": "SELECTED"}
    return [
        {
            "stage": stage,
            "label": labels.get(stage, stage),
            "complete": flags[stage],
            "note": notes[stage],
            "blocked": stage == "GUARDED" and blocked,
        }
        for stage in PIPELINE_STAGES
    ]


def counterfactual_lab(trace: OpportunityTrace) -> dict[str, Any]:
    selected_id = trace.assignment.candidate_id if trace.assignment else None
    options = []
    for val in sorted(trace.valuations, key=lambda v: v.enrv_paise, reverse=True):
        cand = next((c for c in trace.candidates if c.candidate_id == val.candidate_id), None)
        is_noop = val.action_code == ActionCode.A00
        status = "AVAILABLE"
        if cand is not None:
            status = cand.availability_status.value
        chosen = selected_id == val.candidate_id
        why_lost = []
        if not chosen:
            if cand is not None and cand.availability_status.value != "AVAILABLE" and not is_noop:
                why_lost.extend(cand.reason_codes)
            elif trace.assignment is not None:
                if val.enrv_paise < trace.assignment.enrv_paise:
                    why_lost.append("Lower expected incremental net recovery")
                if trace.assignment.binding_resource and not is_noop:
                    why_lost.append(
                        f"Constrained by {trace.assignment.binding_resource}"
                    )
        options.append(
            {
                "candidate_id": val.candidate_id,
                "action_code": val.action_code.value,
                "action_label": action_label(val.action_code.value),
                "is_do_nothing": is_noop,
                "chosen": chosen,
                "availability": status,
                "expected_recovery": _money(val.gross_paise),
                "intervention_cost": _money(val.cost_paise + val.expected_incentive_paise),
                "fatigue_cost": _money(val.fatigue_cost_paise),
                "expected_incremental_net": _money(val.enrv_paise),
                "enrv_band": {
                    "lo": _money(val.enrv_lo_paise),
                    "hi": _money(val.enrv_hi_paise),
                },
                "p_action": val.p_action,
                "p_natural": val.p_natural,
                "uplift": val.uplift,
                "approval_required": cand.approval_required if cand else False,
                "why_lost": why_lost,
                "value_drivers": list(val.value_drivers),
            }
        )
    chosen = next((o for o in options if o["chosen"]), None)
    # The allocator's own reason, when it has one in words, IS the rationale — it is
    # more specific than the generic rule, and the generic rule can actively
    # contradict it (claiming maximization when the allocator took a fallback that
    # fit capacity). The generic sentence is the fallback, for a reason code that
    # has no sentence yet. Either way the raw code travels alongside as evidence,
    # so the projection never silently paraphrases the engine away.
    allocator = (
        _allocator_explanation(trace.assignment.explanation) if trace.assignment else None
    )
    rationale = (allocator or {}).get("sentence") or (
        "Chosen because it maximized expected incremental net recovery "
        "subject to policy, resource, risk and authorization constraints."
        if chosen and not chosen["is_do_nothing"]
        else "No intervention cleared the economic and policy bar this cycle. Do nothing is scored."
    )
    return {
        "opportunity_id": trace.opportunity.opportunity_id,
        "p_natural": trace.p_natural,
        "allocator_mode": trace.allocator_mode,
        "constraint_summary": list(trace.constraint_summary),
        "shadow_prices": dict(trace.shadow_prices),
        "options": options,
        "selection_rationale": rationale,
        "allocator_explanation": allocator,
    }


def opportunity_graph(trace: OpportunityTrace) -> dict[str, Any]:
    ctx = trace.diagnosis.observable_context
    ctxd = ctx.to_dict()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    oid = trace.opportunity.opportunity_id

    def add(node_id: str, kind: str, label: str, detail: Any) -> None:
        nodes.append({"id": node_id, "kind": kind, "label": label, "detail": detail})

    add(oid, "opportunity", "Recovery opportunity", {
        "risk_class": risk_label(trace.opportunity.risk_class.value),
        "value_at_risk": _money(trace.opportunity.value_at_risk_paise),
        "addressable": trace.opportunity.addressable,
    })
    if ctx.customer.customer_id:
        add(
            f"cust:{ctx.customer.customer_id}",
            "customer",
            "Customer",
            {
                "segment": ctx.customer.segment,
                "prior_contacts": ctx.customer.previous_contact_count,
                "failed_payments": ctx.customer.failed_payment_count,
            },
        )
        edges.append({"from": f"cust:{ctx.customer.customer_id}", "to": oid, "rel": "owns"})
    if ctx.payment and ctx.payment.transaction_id:
        add("payment", "payment", "Payment", {
            "transaction_id": ctx.payment.transaction_id,
            "reason": ctx.payment.reason_code,
            "method": ctx.payment.method_type,
            "amount": _money(ctx.payment.amount_paise) if ctx.payment.amount_paise else None,
        })
        edges.append({"from": oid, "to": "payment", "rel": "failed_as"})
    if ctx.checkout and ctx.checkout.session_id:
        add("checkout", "checkout", "Checkout", {
            "session_id": ctx.checkout.session_id,
            "stage": ctx.checkout.stage_reached,
            "cart": _money(ctx.checkout.cart_value_paise) if ctx.checkout.cart_value_paise else None,
        })
        edges.append({"from": oid, "to": "checkout", "rel": "abandoned_at"})
    if ctx.subscription and ctx.subscription.subscription_id:
        add("subscription", "subscription", "Subscription", {
            "subscription_id": ctx.subscription.subscription_id,
            "state": ctx.subscription.state,
            "mandate_state": ctx.subscription.mandate_state,
        })
        edges.append({"from": oid, "to": "subscription", "rel": "renewal_of"})
    if ctx.receivable and ctx.receivable.invoice_id:
        add("invoice", "invoice", "Invoice", {
            "invoice_id": ctx.receivable.invoice_id,
            "outstanding": _money(ctx.receivable.outstanding_paise) if ctx.receivable.outstanding_paise else None,
            "ageing": ctx.receivable.ageing_bucket,
        })
        edges.append({"from": oid, "to": "invoice", "rel": "overdue_on"})

    causes = []
    for i, rc in enumerate(trace.diagnosis.ranked_causes):
        cid = f"cause:{rc.cause_code.value}"
        add(cid, "cause", rc.cause_code.value.replace("_", " ").title(), {
            "confidence": rc.confidence_band.value,
            "supporting": list(rc.supporting_features),
            "contradicting": list(rc.contradicting_features),
            "evidence_refs": list(rc.evidence_refs),
        })
        edges.append({"from": oid, "to": cid, "rel": "diagnosed_as" if i == 0 else "also_consistent_with"})
        causes.append(rc.cause_code.value)

    for val in trace.valuations:
        nid = f"action:{val.candidate_id}"
        add(nid, "intervention", action_label(val.action_code.value), {
            "enrv": _money(val.enrv_paise),
            "cost": _money(val.cost_paise),
            "uplift": val.uplift,
        })
        edges.append({"from": oid, "to": nid, "rel": "candidate"})
        if trace.assignment and trace.assignment.candidate_id == val.candidate_id:
            edges.append({"from": nid, "to": "selected", "rel": "selected"})

    if trace.assignment:
        add("selected", "decision", "Selected action", {
            "action": action_label(trace.assignment.action_code.value),
            "outcome": trace.assignment.outcome.value,
            "reason": trace.assignment.reason_code,
        })

    # Guardrail and execution are part of the causal chain, not metadata:
    # the spine is customer → failing object → failure → cause → options →
    # selection → guardrails → execution → outcome.
    auth = trace.authorization
    if auth is not None:
        gate_rows = _gate_rows([g.to_dict() for g in auth.gate_trace])
        blocked_families = [r["family"] for r in gate_rows if r["status"] == "blocked"]
        add("guardrails", "guardrail", "Guardrails", {
            "authorization_state": auth.authorization_state.value,
            "gates_evaluated": len(auth.gate_trace),
            "blocking_gate": auth.blocking_gate_id,
            "blocking_reason": block_label(auth.blocking_reason_code),
            "blocked_families": blocked_families,
        })
        if trace.assignment:
            edges.append({"from": "selected", "to": "guardrails", "rel": "gated_by"})
    if trace.execution is not None:
        add("execution", "execution", "Execution", {
            "stage": trace.execution.execution_stage.value,
            "failure_reason": trace.execution.failure_reason,
            "idempotency_key": trace.execution.idempotency_key,
        })
        if auth is not None:
            edges.append({
                "from": "guardrails",
                "to": "execution",
                "rel": (
                    "authorized"
                    if auth.authorization_state == AuthorizationState.AUTHORIZED
                    else "blocked"
                ),
            })
    if trace.measurement:
        add("outcome", "outcome", "Realized outcome", {
            "incremental_net": _money(trace.measurement.realized_net_value_paise),
            "gross": _money(trace.measurement.gross_recovered_paise),
            "natural": _money(trace.measurement.natural_recovered_paise),
            "observability": trace.measurement.observability.value,
            "attribution": (
                trace.measurement.attribution_class.value
                if trace.measurement.attribution_class
                else None
            ),
        })
        upstream = (
            "execution"
            if trace.execution is not None
            else ("guardrails" if auth is not None else "selected")
        )
        edges.append({"from": upstream, "to": "outcome", "rel": "realized"})

    present = {n["id"] for n in nodes}
    failing_object = next(
        (i for i in ("payment", "checkout", "subscription", "invoice") if i in present),
        None,
    )
    spine_ids = [
        f"cust:{ctx.customer.customer_id}" if ctx.customer.customer_id else None,
        failing_object,
        oid,
        f"cause:{causes[0]}" if causes else None,
        "OPTIONS",
        "selected",
        "guardrails",
        "execution",
        "outcome",
    ]
    chain = [
        s for s in spine_ids if s == "OPTIONS" or (s is not None and s in present)
    ]

    return {
        "opportunity_id": oid,
        "nodes": nodes,
        "edges": edges,
        "chain": chain,
        "causes": causes,
        "context": {
            "customer": ctxd.get("customer"),
            "fatigue": ctxd.get("fatigue"),
            "instrument": ctxd.get("instrument"),
            "payment": ctxd.get("payment"),
            "checkout": ctxd.get("checkout"),
            "subscription": ctxd.get("subscription"),
            "receivable": ctxd.get("receivable"),
        },
        "evidence_facts": dict(trace.opportunity.evidence.facts),
        "signal_ids": list(trace.opportunity.evidence.signal_ids),
        "llm_used": trace.diagnosis.llm_used,
    }


def decision_receipt(trace: OpportunityTrace) -> dict[str, Any]:
    selected_val = None
    if trace.assignment and trace.assignment.candidate_id:
        selected_val = next(
            (v for v in trace.valuations if v.candidate_id == trace.assignment.candidate_id),
            None,
        )
    auth = trace.authorization
    meas = trace.measurement
    # One projection of the lab, read twice below: the selection sentence and the
    # allocator's own reason belong on the receipt too, since the receipt is the
    # record a reviewer reads without the workspace around it.
    _lab = counterfactual_lab(trace)
    rejected = []
    for val in trace.valuations:
        if trace.assignment and val.candidate_id == trace.assignment.candidate_id:
            continue
        rejected.append(
            {
                "action": action_label(val.action_code.value),
                "enrv": _money(val.enrv_paise),
                "reason": "Lower ENRV" if selected_val and val.enrv_paise < selected_val.enrv_paise else "Not selected",
            }
        )
    cause = (
        trace.diagnosis.primary_category.value
        if trace.diagnosis.primary_category
        else "UNCLASSIFIED"
    )
    auth_state = auth.authorization_state.value if auth else "NOT_SUBMITTED"
    return {
        "title": "Recovery Decision Receipt",
        "opportunity_id": trace.opportunity.opportunity_id,
        "cycle_id": trace.cycle_id,
        "observed_failure": {
            "risk_class": risk_label(trace.opportunity.risk_class.value),
            "cause": cause,
            "confidence": trace.diagnosis.uncertainty,
        },
        "evidence": {
            "signals": list(trace.opportunity.evidence.signal_ids),
            "facts": dict(trace.opportunity.evidence.facts),
            "supporting_features": list(
                trace.diagnosis.ranked_causes[0].supporting_features
            )
            if trace.diagnosis.ranked_causes
            else [],
        },
        "available_actions": [
            action_label(c.action_code.value) for c in trace.candidates
        ],
        "selected_action": (
            action_label(trace.assignment.action_code.value)
            if trace.assignment
            else None
        ),
        "expected_incremental_value": _money(selected_val.enrv_paise) if selected_val else _money(0),
        "estimated_intervention_cost": _money(
            (selected_val.cost_paise + selected_val.expected_incentive_paise) if selected_val else 0
        ),
        "policy_constraints": list(trace.constraint_summary),
        "authorization": {
            "state": auth_state,
            "authorized": auth_state == AuthorizationState.AUTHORIZED.value,
            "blocked": auth is not None and auth_state != AuthorizationState.AUTHORIZED.value,
            "blocking_reason": block_label(auth.blocking_reason_code) if auth else None,
            "blocking_gate": auth.blocking_gate_id if auth else None,
        },
        "why_alternatives_lost": rejected[:8],
        "execution": {
            "stage": trace.execution.execution_stage.value if trace.execution else None,
            "failure_reason": trace.execution.failure_reason if trace.execution else None,
            "idempotency_key": trace.execution.idempotency_key if trace.execution else None,
        },
        "realized_recovery": _money(meas.gross_recovered_paise) if meas else None,
        "realized_cost": _money(meas.realized_cost_paise) if meas else None,
        "incremental_net_recovery": _money(meas.realized_net_value_paise) if meas else None,
        "natural_recovery": _money(meas.natural_recovered_paise) if meas else None,
        "attribution": meas.attribution_class.value if meas and meas.attribution_class else None,
        "audit_reference": (
            auth.audit_reference
            if auth
            else (trace.execution.audit_intent_ref if trace.execution else trace.allocation_hash)
        ),
        "pipeline": _pipeline(trace),
        "selection_rationale": _lab["selection_rationale"],
        "allocator_explanation": _lab["allocator_explanation"],
    }


# Phase 11 guardrail families. Gate identities and semantics come from
# revive/policy/gates.py (G1–G12, fixed order); only the presentation grouping
# and the human-readable "what it checks" text live here.
GATE_META: dict[str, tuple[str, str, str]] = {
    "G1": ("POLICY", "Consent", "Customer has consented to this channel and has not opted out"),
    "G2": ("COOLDOWN", "Contact window", "Action falls inside the permitted contact window for this customer"),
    "G3": ("RESOURCE", "Contact cap", "Customer has remaining contact allowance this period"),
    "G4": ("RESOURCE", "Retry cap", "Payment has not exhausted its retry attempts"),
    "G5": ("BUDGET", "Incentive limit", "Incentive amount is within the per-action ceiling"),
    "G6": ("BUDGET", "Budget capacity", "Remaining campaign budget can fund this action"),
    "G7": ("AUTHORIZATION", "Human approval", "Approval obtained where the policy requires a human decision"),
    "G8": ("POLICY", "Risk block", "Account carries no active risk hold"),
    "G9": ("DUPLICATE", "Duplicate suppression", "No equivalent action is already in flight for this payment"),
    "G10": ("POLICY", "Stopping rules", "Stopping rules SR-01…SR-05 evaluated and recorded separately"),
    "G11": ("RESOURCE", "Channel availability", "Selected channel is reachable and enabled"),
    "G12": ("POLICY", "Amount sanity", "Expected net recovery value is positive and within bounds"),
}

GATE_FAMILIES: tuple[str, ...] = (
    "POLICY",
    "RESOURCE",
    "BUDGET",
    "DUPLICATE",
    "COOLDOWN",
    "AUTHORIZATION",
)


def _gate_rows(gates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group the raw gate trace into the six guardrail families.

    Each row carries the actual observed value and the constraint it was tested
    against, so a block can be read without opening the raw trace.
    """
    by_family: dict[str, list[dict[str, Any]]] = {f: [] for f in GATE_FAMILIES}
    for g in gates:
        family, name, checks = GATE_META.get(
            g["gate_id"], ("POLICY", g["gate_id"], "Gate evaluation")
        )
        observed = g.get("observed_value")
        limit = g.get("limit_value")
        reason = g.get("reason_code") or ""
        applicable = "NOT_APPLICABLE" not in reason
        by_family.setdefault(family, []).append(
            {
                "gate_id": g["gate_id"],
                "sequence": g.get("sequence"),
                "name": name,
                "checks": checks,
                "verdict": g.get("verdict"),
                "reason_code": g.get("reason_code"),
                "reason_label": block_label(g.get("reason_code")),
                "blocking": bool(g.get("blocking")),
                "applicable": applicable,
                "observed": _fmt_gate_value(observed),
                "constraint": _fmt_gate_value(limit),
                "has_values": observed is not None or limit is not None,
                "detail": g.get("detail") or {},
            }
        )
    rows = []
    for family in GATE_FAMILIES:
        members = sorted(by_family.get(family, []), key=lambda r: r["sequence"] or 0)
        blocking = [m for m in members if m["blocking"]]
        denied = [m for m in members if m["verdict"] != "ALLOW"]
        applicable = [m for m in members if m["applicable"]]
        if blocking:
            status = "blocked"
        elif denied:
            status = "attention"
        elif applicable:
            status = "pass"
        elif members:
            status = "not_applicable"
        else:
            status = "not_evaluated"
        if blocking:
            result = f"BLOCKED — {blocking[0]['reason_label']}"
        elif applicable:
            result = f"PASS — {len(applicable)} of {len(members)} gates applied"
        elif members:
            result = "NOT APPLICABLE to this action"
        else:
            result = "NOT EVALUATED"
        rows.append(
            {
                "family": family,
                "status": status,
                "gates": members,
                "gate_count": len(members),
                "applicable_count": len(applicable),
                "blocking_gate": blocking[0]["gate_id"] if blocking else None,
                "result": result,
            }
        )
    return rows


def _fmt_gate_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value) if value else "none"
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in value.items()) if value else "none"
    return str(value)


def guardrail_proof(trace: OpportunityTrace) -> dict[str, Any]:
    auth = trace.authorization
    gates = [g.to_dict() for g in auth.gate_trace] if auth else []
    stops = [s.to_dict() for s in auth.stopping_results] if auth else []
    return {
        "opportunity_id": trace.opportunity.opportunity_id,
        "pipeline": _pipeline(trace),
        "authorization_state": auth.authorization_state.value if auth else "NOT_SUBMITTED",
        "blocking_reason": block_label(auth.blocking_reason_code) if auth else None,
        "blocking_gate": auth.blocking_gate_id if auth else None,
        "gate_trace": gates,
        "gate_groups": _gate_rows(gates),
        "gates_evaluated": len(gates),
        "gates_passed": sum(1 for g in gates if g.get("verdict") == "ALLOW"),
        "stopping_results": stops,
        "stopping_fired": sum(1 for s in stops if s.get("fired")),
        "approval_required": auth.approval_requirement if auth else False,
        "allocator_outcome": trace.assignment.outcome.value if trace.assignment else None,
        "allocator_reason": trace.assignment.reason_code if trace.assignment else None,
        "autonomy_bound": "Execution requires AUTHORIZED. Blocked actions never reach adapters.",
    }


def _best_valuation(trace: OpportunityTrace):
    actionable = [v for v in trace.valuations if v.action_code != ActionCode.A00]
    if not actionable:
        return None
    return max(actionable, key=lambda v: v.enrv_paise)


def opportunity_card(trace: OpportunityTrace) -> dict[str, Any]:
    meas = trace.measurement
    best = _best_valuation(trace)
    selected_val = None
    if trace.assignment and trace.assignment.candidate_id:
        selected_val = next(
            (v for v in trace.valuations if v.candidate_id == trace.assignment.candidate_id),
            None,
        )
    auth = trace.authorization
    blocked = auth is not None and auth.authorization_state != AuthorizationState.AUTHORIZED
    policy_state = auth.authorization_state.value if auth else (
        trace.assignment.outcome.value if trace.assignment else "OPEN"
    )
    execution_state = (
        trace.execution.execution_stage.value if trace.execution else "NOT_EXECUTED"
    )
    natural_est = int(round(trace.p_natural * trace.opportunity.value_at_risk_paise))
    observability = meas.observability.value if meas else None
    # Phase 6 NEEDS REVIEW: opportunities a recovery operator cannot close out
    # cleanly. Deliberately excludes ordinary allocator deferral and ordinary
    # unobservable outcomes — those are expected engine states, not exceptions.
    review_reason = None
    if blocked and auth is not None:
        review_reason = f"Blocked at {auth.blocking_gate_id or 'policy'} — {block_label(auth.blocking_reason_code)}"
    elif execution_state == "SCHEDULED":
        review_reason = "Execution scheduled for a future settlement window"
    elif execution_state in {"FAILED", "CANCELLED", "REJECTED"}:
        review_reason = f"Execution {execution_state.lower()}"
    elif meas is not None and meas.realized_net_value_paise < 0:
        review_reason = "Cost incurred with no incremental recovery"
    elif (
        meas is not None
        and observability != "OBSERVED"
        and meas.realized_cost_paise > 0
    ):
        review_reason = "Cost incurred but outcome not observable"
    return {
        "opportunity_id": trace.opportunity.opportunity_id,
        "cycle_id": trace.cycle_id,
        "risk_class": trace.opportunity.risk_class.value,
        "risk_label": risk_label(trace.opportunity.risk_class.value),
        "value_at_risk": _money(trace.opportunity.value_at_risk_paise),
        "addressable": trace.opportunity.addressable,
        "cause": (
            trace.diagnosis.primary_category.value
            if trace.diagnosis.primary_category
            else None
        ),
        "selected_action": (
            action_label(trace.assignment.action_code.value) if trace.assignment else None
        ),
        "best_action": action_label(best.action_code.value) if best else None,
        "action_code": trace.assignment.action_code.value if trace.assignment else None,
        "outcome": trace.assignment.outcome.value if trace.assignment else None,
        "expected_enrv": _money(trace.assignment.enrv_paise) if trace.assignment else None,
        "expected_incremental": _money(selected_val.enrv_paise) if selected_val else (
            _money(best.enrv_paise) if best else None
        ),
        "expected_recovery": _money(best.gross_paise) if best else None,
        "natural_recovery_est": _money(natural_est),
        "candidate_count": len(trace.candidates),
        "authorization_state": auth.authorization_state.value if auth else None,
        "policy_state": policy_state,
        "blocking_reason": block_label(auth.blocking_reason_code) if blocked and auth else None,
        "blocked": blocked,
        "execution_state": execution_state,
        "incremental_net": _money(meas.realized_net_value_paise) if meas else None,
        "realized_recovery": _money(meas.gross_recovered_paise) if meas else None,
        "realized_cost": _money(meas.realized_cost_paise) if meas else None,
        "observability": observability,
        "measured": meas is not None,
        "needs_review": review_reason is not None,
        "review_reason": review_reason,
        "pipeline": _pipeline(trace),
    }


def opportunity_summary(traces: list[OpportunityTrace]) -> dict[str, Any]:
    at_risk = sum(t.opportunity.value_at_risk_paise for t in traces)
    recoverable = sum(
        t.opportunity.value_at_risk_paise for t in traces if t.opportunity.addressable
    )
    blocked = sum(
        1
        for t in traces
        if t.authorization is not None
        and t.authorization.authorization_state != AuthorizationState.AUTHORIZED
    )
    authorized = sum(
        1
        for t in traces
        if t.authorization is not None
        and t.authorization.authorization_state == AuthorizationState.AUTHORIZED
    )
    executed = sum(1 for t in traces if t.execution is not None)
    return {
        "count": len(traces),
        "at_risk": _money(at_risk),
        "recoverable": _money(recoverable),
        "blocked": blocked,
        "authorized": authorized,
        "executed": executed,
    }


def system_pulse(state: ProductRunState) -> dict[str, Any]:
    last = state.cycles[-1] if state.cycles else None
    traces = last.opportunities if last else ()
    evaluated = sum(len(t.candidates) for t in traces)
    return {
        "detected": last.detected_count if last else 0,
        "diagnosed": last.diagnosed_count if last else 0,
        "evaluated": evaluated,
        "authorized": last.authorized_count if last else 0,
        "blocked": last.blocked_count if last else 0,
        "executed": last.executed_count if last else 0,
        "measured": last.measured_count if last else 0,
    }


def _pipeline_panel(stage: str, traces: tuple[OpportunityTrace, ...]) -> dict[str, Any]:
    """Stage previews, as (label, value) pairs rather than pre-joined strings.

    The pipeline cell is ~160px wide, so a preview like "Retry payment
    (scheduled) · ₹187.60 ENRV" has to lose something. Joining the two halves in
    Python takes that decision away from the surface, and the surface then
    truncates from the right — which drops the rupee figure, the one part a
    reader cannot infer. Keeping them separate lets the cell ellipsis the action
    name and anchor the number, and lets the expanded stage panel show both in
    full. `value` is None for the stages whose previews are a single short token.
    """
    samples: list[tuple[str, str | None]] = []
    if stage == "DETECT":
        samples = [(risk_label(t.opportunity.risk_class.value), None) for t in traces[:4]]
    elif stage == "DIAGNOSE":
        samples = [
            (
                t.diagnosis.primary_category.value
                if t.diagnosis.primary_category
                else "UNCLASSIFIED",
                None,
            )
            for t in traces[:4]
        ]
    elif stage == "CANDIDATES":
        for t in traces[:3]:
            for c in t.candidates[:2]:
                samples.append((action_label(c.action_code.value), None))
    elif stage == "OPTIMIZE":
        for t in traces[:4]:
            if t.assignment:
                samples.append(
                    (
                        action_label(t.assignment.action_code.value),
                        f"{format_inr(t.assignment.enrv_paise)} ENRV",
                    )
                )
    elif stage == "GUARD":
        for t in traces[:3]:
            if t.authorization and t.authorization.blocking_reason_code:
                samples.append(
                    (block_label(t.authorization.blocking_reason_code) or "", None)
                )
            elif t.constraint_summary:
                samples.extend((c, None) for c in list(t.constraint_summary)[:2])
    elif stage == "AUTHORIZE":
        samples = [
            (t.authorization.authorization_state.value, None)
            for t in traces
            if t.authorization
        ][:4]
    elif stage == "EXECUTE":
        samples = [
            (t.execution.execution_stage.value, None)
            for t in traces
            if t.execution
        ][:4]
    elif stage == "MEASURE":
        samples = [
            ("Realized net", format_inr(t.measurement.realized_net_value_paise))
            for t in traces
            if t.measurement
        ][:4]
    return {
        "samples": [
            {"label": label, "value": value} for label, value in samples if label
        ][:6]
    }


def interactive_pipeline(state: ProductRunState) -> list[dict[str, Any]]:
    last = state.cycles[-1] if state.cycles else None
    traces = last.opportunities if last else ()
    counts = system_pulse(state)
    stage_map = [
        ("DETECT", "detected"),
        ("DIAGNOSE", "diagnosed"),
        ("CANDIDATES", "evaluated"),
        ("OPTIMIZE", "diagnosed"),
        ("GUARD", "blocked"),
        ("AUTHORIZE", "authorized"),
        ("EXECUTE", "executed"),
        ("MEASURE", "measured"),
    ]
    rows: list[dict[str, Any]] = []
    for stage_id, count_key in stage_map:
        count = counts[count_key]
        if stage_id == "GUARD":
            count = last.guarded_count if last else 0
        elif stage_id == "OPTIMIZE":
            count = last.optimized_count if last else 0
        panel = _pipeline_panel(stage_id, traces)
        status = "active" if count > 0 else "idle"
        if stage_id == "GUARD" and last and last.blocked_count:
            status = "warn"
        rows.append(
            {
                "id": stage_id,
                "label": stage_id,
                "count": count,
                "status": status,
                "samples": panel["samples"],
            }
        )
    return rows


def audit_ledger(state: ProductRunState) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    category_map = {
        "DETECTED": "decisions",
        "DIAGNOSED": "decisions",
        "OPTIMIZED": "decisions",
        "GUARDED": "guardrails",
        "AUTHORIZED": "guardrails",
        "EXECUTED": "executions",
        "MEASURED": "measurements",
    }
    for cycle in state.cycles:
        for tr in cycle.opportunities:
            rec = decision_receipt(tr)
            for idx, step in enumerate(rec["pipeline"]):
                result = "pending"
                if step.get("blocked"):
                    result = "blocked"
                elif step["complete"]:
                    result = "complete"
                events.append(
                    {
                        "timestamp": f"{cycle.cycle_id}+{idx:02d}",
                        "category": category_map.get(step["stage"], "decisions"),
                        "event": step["note"],
                        "stage": step["stage"],
                        "label": step.get("label", step["stage"]),
                        "object": tr.opportunity.opportunity_id,
                        "decision": rec.get("selected_action") or "Do nothing",
                        "result": result,
                        # Phase 14 BLOCKS filter: a cross-cut over categories,
                        # not a category of its own.
                        "blocked": result == "blocked",
                        "audit_reference": rec["audit_reference"],
                    }
                )
    return events


def latest_traces(state: ProductRunState) -> list[OpportunityTrace]:
    """Latest cycle appearance per opportunity_id."""
    by_id: dict[str, OpportunityTrace] = {}
    for cycle in state.cycles:
        for tr in cycle.opportunities:
            by_id[tr.opportunity.opportunity_id] = tr
    ranked = sorted(
        by_id.values(),
        key=lambda t: t.opportunity.value_at_risk_paise,
        reverse=True,
    )
    return ranked


def waterfall(state: ProductRunState) -> dict[str, Any]:
    """Revenue accounting in two internally coherent tracks.

    PLANNED is what the engine expected before acting; REALIZED is what
    measurement observed. Mixing the two in one sequence produces a waterfall
    that does not reconcile, so they are kept separate and each is closed.
    """
    traces = latest_traces(state)
    at_risk = sum(t.opportunity.value_at_risk_paise for t in traces)
    addressable = sum(
        t.opportunity.value_at_risk_paise for t in traces if t.opportunity.addressable
    )
    natural_pred = 0
    incremental_pred = 0
    cost_pred = 0
    for t in traces:
        natural_pred += int(round(t.p_natural * t.opportunity.value_at_risk_paise))
        if t.assignment:
            incremental_pred += max(0, t.assignment.enrv_paise)
            val = next(
                (v for v in t.valuations if v.candidate_id == t.assignment.candidate_id),
                None,
            )
            if val is not None:
                cost_pred += val.cost_paise + val.expected_incentive_paise
    measurements = [
        t.measurement for c in state.cycles for t in c.opportunities if t.measurement
    ]
    gross_real = sum(m.gross_recovered_paise for m in measurements)
    natural_real = sum(m.natural_recovered_paise for m in measurements)
    incremental_real = sum(m.incremental_recovered_paise for m in measurements)
    cost_real = sum(m.realized_cost_paise for m in measurements)
    net_real = sum(m.realized_net_value_paise for m in measurements)
    observed = sum(1 for m in measurements if m.observability.value == "OBSERVED")

    planned = [
        {
            "id": "at_risk",
            "label": "Revenue at risk",
            "kind": "base",
            "value": _money(at_risk),
        },
        {
            "id": "recoverable",
            "label": "Addressable",
            "kind": "base",
            "value": _money(addressable),
            "delta": _money(addressable - at_risk),
        },
        {
            "id": "natural",
            "label": "Expected without action",
            "kind": "natural",
            "value": _money(natural_pred),
            "note": "Baseline the engine expects to recover on its own.",
        },
        {
            "id": "incremental",
            "label": "Expected from intervention",
            "kind": "incremental",
            "value": _money(incremental_pred),
            "note": "Allocated ENRV — value above the do-nothing baseline.",
        },
        {
            "id": "cost",
            "label": "Expected cost",
            "kind": "cost",
            "value": _money(cost_pred),
        },
    ]
    realized_steps = [
        {
            "id": "gross",
            "label": "Gross recovered",
            "kind": "base",
            "value": _money(gross_real),
        },
        {
            "id": "natural",
            "label": "Attributed to natural recovery",
            "kind": "natural",
            "value": _money(natural_real),
            "note": (
                "Observed natural recovery is 0 by construction in this path: "
                "only intervened opportunities are measured, so there is no "
                "un-intervened control group to attribute recovery to."
            ),
        },
        {
            "id": "incremental",
            "label": "Attributed to intervention",
            "kind": "incremental",
            "value": _money(incremental_real),
        },
        {
            "id": "cost",
            "label": "Realized cost",
            "kind": "cost",
            "value": _money(cost_real),
        },
        {
            "id": "net",
            "label": "Incremental net recovery",
            "kind": "net",
            "value": _money(net_real),
        },
    ]
    return {
        # Retained for compatibility with existing consumers.
        "steps": [
            {"id": "at_risk", "label": "Revenue at risk", "value": _money(at_risk)},
            {"id": "recoverable", "label": "Potentially recoverable", "value": _money(addressable)},
            {"id": "natural", "label": "Naturally recoverable (predicted)", "value": _money(natural_pred)},
            {"id": "incremental", "label": "Incrementally recoverable (allocated ENRV)", "value": _money(incremental_pred)},
            {"id": "cost", "label": "Realized intervention cost", "value": _money(cost_real)},
            {"id": "net", "label": "Incremental net recovery (realized)", "value": _money(net_real)},
        ],
        "planned": planned,
        "realized_steps": realized_steps,
        "realized": {
            "gross": _money(gross_real),
            "natural": _money(natural_real),
            "incremental": _money(incremental_real),
            "cost": _money(cost_real),
            "net": _money(net_real),
        },
        "measurement_coverage": {
            "measured": len(measurements),
            "observed": observed,
            "unobservable": len(measurements) - observed,
        },
        "natural_observability": (
            "NOT_SEPARATELY_OBSERVED"
            if natural_real == 0 and measurements
            else "OBSERVED"
        ),
        "note": (
            "PLANNED uses engine valuations before acting. REALIZED uses "
            "measurements only. The two tracks are reported separately because "
            "they answer different questions."
        ),
    }


def _calculations(
    state: ProductRunState, traces: list[OpportunityTrace], wf: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Phase 20 provenance: how each headline figure was derived.

    Every input below is read back out of the same projection the metric was
    computed from, so VIEW CALCULATION cannot drift from the displayed value.
    """
    measurements = [
        t.measurement for c in state.cycles for t in c.opportunities if t.measurement
    ]
    n_meas = len(measurements)
    addressable_n = sum(1 for t in traces if t.opportunity.addressable)
    real = wf["realized"]
    at_risk = wf["planned"][0]["value"]
    recoverable = wf["planned"][1]["value"]
    rate = (
        (real["incremental"]["paise"] / at_risk["paise"]) if at_risk["paise"] else 0.0
    )

    def entry(
        mid: str,
        label: str,
        definition: str,
        formula: str,
        inputs: list[dict[str, Any]],
        result: str,
        source: str,
    ) -> dict[str, Any]:
        return {
            "id": mid,
            "label": label,
            "definition": definition,
            "formula": formula,
            "inputs": inputs,
            "result": result,
            "source": source,
        }

    return {
        "at_risk": entry(
            "at_risk",
            "Revenue at risk",
            "Face value of every open recovery opportunity in the latest view of each account.",
            "Σ opportunity.value_at_risk",
            [
                {"label": "Opportunities counted", "value": str(len(traces))},
                {"label": "Cycles run", "value": str(len(state.cycles))},
            ],
            at_risk["display"],
            "Detection — opportunity ledger",
        ),
        "recoverable": entry(
            "recoverable",
            "Addressable",
            "The at-risk subset the engine holds a legally and operationally available action for.",
            "Σ value_at_risk where opportunity.addressable",
            [
                {"label": "Addressable opportunities", "value": str(addressable_n)},
                {"label": "Of total", "value": str(len(traces))},
                {"label": "Excluded", "value": str(len(traces) - addressable_n)},
            ],
            recoverable["display"],
            "Detection — addressability screen",
        ),
        "natural": entry(
            "natural",
            "Natural recovery",
            "Recovery that would have happened with no intervention. Predicted per opportunity, and separately attributed at measurement.",
            "predicted: Σ p_natural × value_at_risk   ·   realized: Σ measurement.natural_recovered",
            [
                {"label": "Predicted", "value": wf["planned"][2]["value"]["display"]},
                {"label": "Realized (attributed)", "value": real["natural"]["display"]},
                {"label": "Observability", "value": wf["natural_observability"]},
            ],
            real["natural"]["display"],
            "Counterfactual baseline + measurement attribution",
        ),
        "incremental": entry(
            "incremental",
            "Incremental recovery",
            "Recovery attributable to the intervention above the do-nothing baseline. This is the only figure PAYVANTA claims credit for.",
            "Σ measurement.incremental_recovered  =  gross − natural",
            [
                {"label": "Gross recovered", "value": real["gross"]["display"]},
                {"label": "less natural", "value": real["natural"]["display"]},
                {"label": "Measured opportunities", "value": str(n_meas)},
            ],
            real["incremental"]["display"],
            "Measurement — incremental attribution",
        ),
        "cost": entry(
            "cost",
            "Realized cost",
            "Money and incentive actually consumed by executed interventions, after settlement of reservations.",
            "Σ measurement.realized_cost",
            [
                {"label": "Expected at decision time", "value": wf["planned"][4]["value"]["display"]},
                {"label": "Realized after settlement", "value": real["cost"]["display"]},
                {"label": "Executions measured", "value": str(n_meas)},
            ],
            real["cost"]["display"],
            "Execution settlement + measurement",
        ),
        "net": entry(
            "net",
            "Incremental net recovery",
            "The bottom line: incremental recovery net of the cost of achieving it.",
            "incremental recovery − realized cost",
            [
                {"label": "Incremental recovery", "value": real["incremental"]["display"]},
                {"label": "less realized cost", "value": real["cost"]["display"]},
            ],
            real["net"]["display"],
            "Measurement — realized net value",
        ),
        "recovery_rate": entry(
            "recovery_rate",
            "Recovery rate",
            "Share of at-risk revenue converted into incremental recovery.",
            "incremental recovery ÷ revenue at risk",
            [
                {"label": "Incremental recovery", "value": real["incremental"]["display"]},
                {"label": "Revenue at risk", "value": at_risk["display"]},
            ],
            f"{rate * 100:.2f}%",
            "Derived from measurement and detection",
        ),
    }


def control_room(state: ProductRunState) -> dict[str, Any]:
    traces = latest_traces(state)
    measurements = [
        t.measurement for c in state.cycles for t in c.opportunities if t.measurement
    ]
    auths = [
        t.authorization for c in state.cycles for t in c.opportunities if t.authorization
    ]
    authorized = sum(
        1 for a in auths if a.authorization_state == AuthorizationState.AUTHORIZED
    )
    blocked = sum(
        1 for a in auths if a.authorization_state != AuthorizationState.AUTHORIZED
    )
    net = sum(m.realized_net_value_paise for m in measurements)
    cost = sum(m.realized_cost_paise for m in measurements)
    at_risk = sum(t.opportunity.value_at_risk_paise for t in traces)
    incremental = sum(m.incremental_recovered_paise for m in measurements)
    recovery_rate = (incremental / at_risk) if at_risk else 0.0
    wf = waterfall(state)
    last = state.cycles[-1] if state.cycles else None
    pipeline = {
        "DETECTED": last.detected_count if last else 0,
        "DIAGNOSED": last.diagnosed_count if last else 0,
        "OPTIMIZED": last.optimized_count if last else 0,
        "GUARDED": last.guarded_count if last else 0,
        "AUTHORIZED": last.authorized_count if last else 0,
        "EXECUTED": last.executed_count if last else 0,
        "MEASURED": last.measured_count if last else 0,
    }
    compliance = blocked == 0 or authorized + blocked == len(auths)
    integrity = all(
        t.execution is None
        or (
            t.authorization is not None
            and t.authorization.authorization_state == AuthorizationState.AUTHORIZED
        )
        for c in state.cycles
        for t in c.opportunities
    )
    return {
        "product": "PAYVANTA",
        "descriptor": "Autonomous Revenue Recovery Intelligence",
        "tagline": "Detect. Diagnose. Optimize. Guard. Execute. Prove.",
        "fixture_label": state.fixture_label,
        "policy_pack_version": state.policy_pack.version,
        "policy_pack_status": state.policy_pack.status.value,
        "internal_policy_id": "REVIVE",
        "seed": state.bundle.seed,
        "profile": state.bundle.profile,
        "cycles_run": len(state.cycles),
        "hero": {
            "incremental_net_recovery": _money(net),
            "at_risk_revenue": _money(at_risk),
            "recoverable_revenue": _money(
                sum(
                    t.opportunity.value_at_risk_paise
                    for t in traces
                    if t.opportunity.addressable
                )
            ),
            "natural_recovery": wf["realized"]["natural"],
            "incremental_recovery": wf["realized"]["incremental"],
            "gross_recovery": wf["realized"]["gross"],
            "recovery_rate": recovery_rate,
            "realized_cost": _money(cost),
            "authorized_interventions": authorized,
            "blocked_interventions": blocked,
            "policy_compliance": "PASS" if compliance else "REVIEW",
            "execution_integrity": "PASS" if integrity else "FAIL",
        },
        "calculations": _calculations(state, traces, wf),
        "system_pulse": system_pulse(state),
        "interactive_pipeline": interactive_pipeline(state),
        "opportunity_summary": opportunity_summary(traces),
        "pipeline": pipeline,
        "waterfall": wf,
        "top_opportunities": [opportunity_card(t) for t in traces[:12]],
        "all_opportunities": [opportunity_card(t) for t in traces],
        "recent_receipts": [
            decision_receipt(t)
            for t in traces
            if t.authorization is not None or t.assignment is not None
        ][:6],
        "allocator": {
            "mode": last.allocator_mode if last else None,
            "shadow_prices": dict(last.shadow_prices) if last else {},
            "constraints": list(last.constraint_summary) if last else [],
        },
    }


def opportunity_detail(trace: OpportunityTrace) -> dict[str, Any]:
    return {
        "card": opportunity_card(trace),
        "graph": opportunity_graph(trace),
        "counterfactual": counterfactual_lab(trace),
        "receipt": decision_receipt(trace),
        "guardrail": guardrail_proof(trace),
    }
