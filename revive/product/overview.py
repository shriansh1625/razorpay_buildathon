"""Machine-readable product overview.

Projects the live sandbox snapshot and the read-only official benchmark
lab into one inspectable document. Nothing here is a second copy of
engine state: every figure is taken from the session snapshot or from
``benchmark_lab()``. Official cell counts are reported only when
verification succeeded.
"""

from __future__ import annotations

from typing import Any

from revive.product.benchmark_lab import DECLARED_RUN, OFFICIAL_DIR
from revive.product.benchmark_story import M10, benchmark_story

WORKFLOW = (
    "DETECT",
    "DIAGNOSE",
    "CANDIDATES",
    "OPTIMIZE",
    "GUARD",
    "AUTHORIZE",
    "EXECUTE",
    "MEASURE",
)

API_CATALOG = (
    {"method": "GET", "path": "/api/product/overview", "returns": "This document"},
    {"method": "GET", "path": "/api/snapshot", "returns": "Full sandbox projection"},
    {"method": "GET", "path": "/api/control-room", "returns": "Control Room projection"},
    {"method": "GET", "path": "/api/opportunity/{id}", "returns": "Opportunity workspace projection"},
    {"method": "GET", "path": "/api/receipt/{id}", "returns": "Decision receipt"},
    {"method": "GET", "path": "/api/audit", "returns": "Audit ledger"},
    {"method": "GET", "path": "/api/runs", "returns": "Current sandbox run index and seed"},
    {"method": "GET", "path": "/api/benchmark", "returns": "Benchmark Lab contract + verification + story"},
    {"method": "GET", "path": "/api/benchmark/story", "returns": "Methodology, engineering timeline, M-10, access"},
    {"method": "GET", "path": "/api/benchmark/official/summary", "returns": "Official evidence summary + contract"},
    {"method": "GET", "path": "/api/benchmark/official/contract", "returns": "Structured official benchmark summary"},
    {"method": "GET", "path": "/api/benchmark/official/matrix", "returns": "6×5 profile × policy matrix"},
    {"method": "GET", "path": "/api/benchmark/official/cell/{seed}/{profile}/{policy}", "returns": "One official cell + metrics + checksum + validation"},
    {"method": "POST", "path": "/api/recovery-run", "returns": "New bounded sandbox world (does not touch official evidence)"},
)

UI_ROUTES = (
    {"hash": "#/control", "label": "Control Room"},
    {"hash": "#/opportunities", "label": "Opportunities"},
    {"hash": "#/opportunity/{id}", "label": "Recovery Workspace"},
    {"hash": "#/lab", "label": "Recovery Lab"},
    {"hash": "#/guardrails", "label": "Guardrails"},
    {"hash": "#/audit", "label": "Audit Ledger"},
    {"hash": "#/benchmark", "label": "Benchmark Lab (executive evidence)"},
    {"hash": "#/benchmark/matrix", "label": "Benchmark matrix (forensic cells)"},
    {"hash": "#/benchmark/evidence", "label": "Benchmark provenance (forensic)"},
    {"hash": "#/system", "label": "System / Evidence"},
)


def _card(snapshot: dict[str, Any], opportunity_id: str | None) -> dict[str, Any] | None:
    if not opportunity_id:
        return None
    room = snapshot.get("control_room") or {}
    for card in room.get("all_opportunities") or []:
        if card.get("opportunity_id") == opportunity_id:
            return card
    return None


def _detail(snapshot: dict[str, Any], opportunity_id: str | None) -> dict[str, Any] | None:
    if not opportunity_id:
        return None
    return (snapshot.get("opportunities") or {}).get(opportunity_id)


def _official(bench: dict[str, Any] | None) -> dict[str, Any]:
    declared = dict(DECLARED_RUN)
    story = (bench or {}).get("story") or benchmark_story()
    contract = (bench or {}).get("contract") or {}
    if not bench:
        return {
            "kind": "OFFICIAL_EVIDENCE",
            "path": str(OFFICIAL_DIR).replace("\\", "/"),
            "verified": False,
            "status": "NOT_PROVIDED",
            "cells": None,
            "cell_count": None,
            "group_count": None,
            "seed_count": None,
            "profile_count": None,
            "policy_count": None,
            "benchmark_version": None,
            "metric_version": None,
            "validation": None,
            "blocked": None,
            "frozen_experiment_hash": declared.get("frozen_experiment_reference"),
            "config_hash": None,
            "policy_pack": None,
            "evidence_path": str(OFFICIAL_DIR).replace("\\", "/"),
            "m10": dict(M10),
            "note": "Pass benchmark_lab() to report observed official evidence.",
        }
    verified = bool(bench.get("evidence_verified"))
    verification = bench.get("verification") or {}
    pack = contract.get("policy_pack")
    return {
        "kind": "OFFICIAL_EVIDENCE",
        "path": str(OFFICIAL_DIR).replace("\\", "/"),
        "verified": verified,
        "status": bench.get("evidence_status") or ("VERIFIED" if verified else "UNKNOWN"),
        "artefact_status": bench.get("artefact_status"),
        "benchmark_version": contract.get("benchmark_version") if verified else None,
        "metric_version": contract.get("metric_version") if verified else None,
        "validation": declared.get("validation") if verified else None,
        "blocked": declared.get("blocked") if verified else None,
        "cells": verification.get("cell_count") if verified else None,
        "cell_count": verification.get("cell_count") if verified else None,
        "expected_cells": verification.get("expected_cells") or declared.get("cells"),
        "groups": declared.get("groups") if verified else None,
        "group_count": declared.get("groups") if verified else None,
        "seeds": declared.get("seeds") if verified else None,
        "seed_count": declared.get("seeds") if verified else None,
        "profiles": declared.get("profiles") if verified else None,
        "profile_count": declared.get("profiles") if verified else None,
        "policies": declared.get("policies") if verified else None,
        "policy_count": declared.get("policies") if verified else None,
        "policy_set": list(declared.get("policy_set") or []) if verified else None,
        "profile_set": list(declared.get("profile_set") or []) if verified else None,
        "frozen_experiment_hash": (
            contract.get("frozen_experiment_hash")
            or bench.get("computed_frozen_experiment_reference")
        ),
        "frozen_experiment_reference": bench.get("computed_frozen_experiment_reference"),
        "declared_matches_computed": bench.get("declared_matches_computed"),
        "config_hash": contract.get("config_hash") if verified else None,
        "policy_pack": pack,
        "policy_pack_version": bench.get("policy_pack_version"),
        "policy_pack_hash": bench.get("policy_pack_hash"),
        "evidence_path": str(OFFICIAL_DIR).replace("\\", "/"),
        "internal_policy_id": "REVIVE",
        "m10": dict(M10),
        "engineering": [step["id"] + " " + step["title"] for step in story.get("engineering") or []],
        "story_api": "/api/benchmark/story",
        "contract_api": "/api/benchmark/official/contract",
        "reference_cell": story.get("reference_cell"),
        "note": (
            "Official experiment evaluates the engine across a frozen 20×6×5 design. "
            "It is not this sandbox run. Verification does not claim superiority."
        ),
    }


def _opportunity_block(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    wow_id = snapshot.get("wow_opportunity_id")
    card = _card(snapshot, wow_id)
    detail = _detail(snapshot, wow_id)
    if not card:
        return None
    guard = (detail or {}).get("guardrail") or {}
    receipt = (detail or {}).get("receipt") or {}
    families = [
        {
            "family": row.get("family"),
            "status": row.get("status"),
            "result": row.get("result"),
        }
        for row in (guard.get("gate_groups") or [])
    ]
    execution = None
    if receipt.get("execution"):
        execution = {
            "stage": receipt["execution"].get("stage"),
            "idempotency_key": receipt["execution"].get("idempotency_key"),
        }
    return {
        "opportunity_id": card.get("opportunity_id"),
        "risk_label": card.get("risk_label"),
        "cause": card.get("cause"),
        "recommended_action": card.get("best_action") or card.get("selected_action"),
        "value_at_risk": card.get("value_at_risk"),
        "expected_incremental": card.get("expected_incremental"),
        "incremental_net": card.get("incremental_net"),
        "authorization_state": card.get("authorization_state"),
        "execution_state": card.get("execution_state"),
        "blocked": bool(card.get("blocked")),
        "blocking_reason": card.get("blocking_reason"),
        "measured": bool(card.get("measured")),
        "guardrail_families": families or None,
        "stopping_fired": guard.get("stopping_fired"),
        "autonomy_bound": guard.get("autonomy_bound"),
        "execution": execution,
        "audit_reference": receipt.get("audit_reference"),
    }


def product_overview(
    snapshot: dict[str, Any],
    bench: dict[str, Any] | None = None,
    *,
    run_index: int = 0,
) -> dict[str, Any]:
    """Trustworthy product-level state for humans and evaluators."""
    room = snapshot.get("control_room") or {}
    hero = room.get("hero") or {}
    waterfall = room.get("waterfall") or {}
    realized = waterfall.get("realized") or {}
    pulse = room.get("system_pulse") or {}
    official = _official(bench)
    current = _opportunity_block(snapshot)

    claims = [
        {
            "id": "incremental_net_recovery",
            "claim": "Incremental net recovery",
            "source": "sandbox_engine_measurement",
            "value": hero.get("incremental_net_recovery"),
            "provenance": "control_room.hero.incremental_net_recovery",
            "environment": "SANDBOX",
        },
        {
            "id": "bounded_execution",
            "claim": "Execution integrity",
            "source": "authorization_gate",
            "value": hero.get("execution_integrity"),
            "provenance": "control_room.hero.execution_integrity — execution requires AUTHORIZED",
            "environment": "SANDBOX",
        },
        {
            "id": "official_cells",
            "claim": "Official experiment cells",
            "source": "official_manifest_and_verification",
            "value": official.get("cells"),
            "provenance": official.get("path"),
            "environment": "OFFICIAL_EVIDENCE",
            "status": official.get("status"),
            "test": "tests/product/test_official_evidence.py::TestOfficialCloudFinal::test_verify_evidence_passes",
            "ui": "#/benchmark",
            "api": "GET /api/benchmark/official/contract",
        },
        {
            "id": "benchmark_valid",
            "claim": "BENCHMARK_VALID · blocked=false",
            "source": "validation.json + manifest.json",
            "value": {
                "validation": official.get("validation"),
                "blocked": official.get("blocked"),
            },
            "provenance": official.get("path"),
            "environment": "OFFICIAL_EVIDENCE",
            "ui": "#/benchmark/evidence",
            "api": "GET /api/benchmark/official/summary",
        },
        {
            "id": "m10",
            "claim": "M-10 Incremental Net Recovery",
            "source": "docs/21-evaluation.md § 2.1",
            "value": (official.get("m10") or {}).get("user_facing"),
            "provenance": "NetRecovered(policy) − NetRecovered(B0) on the same seed and profile",
            "environment": "OFFICIAL_EVIDENCE",
            "ui": "#/benchmark/matrix",
            "api": "GET /api/benchmark/official/cell/{seed}/{profile}/{policy}",
        },
    ]
    if current:
        claims.append(
            {
                "id": "active_opportunity",
                "claim": "Active recovery opportunity",
                "source": "sandbox_opportunity_projection",
                "value": {
                    "opportunity_id": current["opportunity_id"],
                    "authorization_state": current["authorization_state"],
                    "execution_state": current["execution_state"],
                    "blocked": current["blocked"],
                    "blocking_reason": current["blocking_reason"],
                    "incremental_net": current["incremental_net"],
                },
                "provenance": f"opportunities.{current['opportunity_id']}",
                "environment": "SANDBOX",
            }
        )

    return {
        "product": "PAYVANTA",
        "descriptor": room.get("descriptor") or "Autonomous Revenue Recovery Intelligence",
        "purpose": (
            "Detect revenue at risk, select an economically justified intervention, "
            "execute only inside deterministic bounds, measure incremental net recovery, "
            "and audit the decision."
        ),
        "environment": {
            "kind": "SANDBOX",
            "name": "PAYVANTA Sandbox",
            "seed": room.get("seed"),
            "profile": room.get("profile"),
            "data": "Synthetic test population",
            "execution": "Bounded local execution",
            "label": room.get("fixture_label"),
        },
        "engine": {
            "name": "PAYVANTA Recovery Engine",
            "status": "READY",
            "policy_pack_version": room.get("policy_pack_version"),
            "policy_pack_status": room.get("policy_pack_status"),
            "internal_policy_id": room.get("internal_policy_id") or "REVIVE",
        },
        "intelligence": {
            "kind": "DETERMINISTIC_DECISION_SYSTEM",
            "llm_used": False,
            "official_llm_mode": "LLM_OFF",
            "diagnosis": "deterministic taxonomy ranking",
            "copy_composer": "not_implemented",
            "allocator": "deterministic Lagrangian",
            "note": (
                "No LLM is invoked in this submission. Official benchmark cells "
                "were evaluated with llm_mode=LLM_OFF. See docs/why-ai.md."
            ),
        },
        "current_run": {
            "server_run_index": run_index,
            "seed": room.get("seed"),
            "cycles_run": room.get("cycles_run"),
            "opportunity_id": snapshot.get("wow_opportunity_id"),
        },
        "financial": {
            "at_risk": hero.get("at_risk_revenue"),
            "recoverable": hero.get("recoverable_revenue"),
            "natural": realized.get("natural") or hero.get("natural_recovery"),
            "gross": realized.get("gross") or hero.get("gross_recovery"),
            "incremental": realized.get("incremental") or hero.get("incremental_recovery"),
            "cost": hero.get("realized_cost"),
            "incremental_net_recovery": hero.get("incremental_net_recovery"),
            "source": "sandbox_engine_measurement",
            "note": "These figures are this sandbox session. They are not an official benchmark cell.",
        },
        "workflow": {
            "loop": list(WORKFLOW),
            "pulse": pulse,
            "stages": room.get("interactive_pipeline"),
        },
        "current_opportunity": current,
        "guardrails": {
            "authorization_state": (current or {}).get("authorization_state"),
            "families": (current or {}).get("guardrail_families"),
            "stopping_fired": (current or {}).get("stopping_fired"),
            "autonomy_bound": (current or {}).get("autonomy_bound"),
            "policy_compliance": hero.get("policy_compliance"),
            "execution_integrity": hero.get("execution_integrity"),
        },
        "official_benchmark": official,
        "audit": {
            "ledger_count": len(snapshot.get("audit_ledger") or []),
            "api": "/api/audit",
            "ui": "#/audit",
        },
        "track03": {
            "detect": True,
            "determine_intervention": True,
            "bounded_execution": True,
            "batch_measurement": True,
            "escalation": True,
            "stopping_rules": True,
            "audit_trail": True,
            "evidence": "docs/track3-evidence.md",
        },
        "claims": claims,
        "inspect": {
            "ui": list(UI_ROUTES),
            "api": list(API_CATALOG),
        },
        "integrity": {
            "official_evidence_writable_by_product": False,
            "sandbox_is_not_official_evidence": True,
            "one_product_for_humans_and_evaluators": True,
        },
    }
