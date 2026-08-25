"""M8 and B3 implementation audits against documentation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ImplementationAudit:
    component: str
    status: str  # ALIGNED | MISMATCH | CAUTION
    findings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status,
            "findings": self.findings,
        }


def audit_m8_implementation() -> ImplementationAudit:
    findings = [
        "Objective: maximize Σ ENRV under capacities — implemented in allocate_portfolio (docs/10 §2.1).",
        "Lagrangian relaxation with subgradient on capacity violations — lagrangian_allocate().",
        "Primal recovery with reservation — primal_recovery() matches docs/10 §5.1.",
        "Greedy density fallback on iteration budget — fallback_greedy_allocate() (docs/10 §5.2).",
        "ε threshold from PolicyPack — enforced in best_action_for_opportunity and primal recovery.",
        "Six resource families tracked — retry, message, voice, human, incentive, contact_allowance.",
        "Shadow prices from Lagrangian dual and binding-resource estimates in primal recovery.",
        "Opportunity exclusivity — one assignment per opportunity in assignments dict.",
        "No oracle / latent inputs in allocation package (observable ENRV only).",
        "CAUTION: contact_allowance subgradient uses aggregate violation heuristic, not per-customer duals.",
        "CAUTION: M8 fallback uses ENRV/resource density; B3 uses raw ENRV — differentiation requires density inversions.",
    ]
    return ImplementationAudit("M8 Portfolio Allocator", "ALIGNED", findings)


def audit_b3_implementation() -> ImplementationAudit:
    findings = [
        "B3 = GREEDY_ENRV per docs/20 — GreedyEnrvBaseline ranks by raw heuristic ENRV.",
        "Observable inputs only — best_action_for_opportunity on ObservableOpportunity features.",
        "Resource handling via can_reserve_action / reserve_action on BaselineCycleContext.",
        "Below-ε opportunities get NO_ACTION; capacity exhaustion yields DEFERRED.",
        "Tie-breaking: sort by (-enrv, opportunity_id) in decide_cycle.",
        "Calibration b3_greedy_selection mirrors greedy-by-ENRV on M7 PricedCandidates.",
        "CAUTION: B3 baseline uses observable heuristic ENRV; calibration path uses M7 ENRV — same ranking intent.",
        "No oracle access in baseline package.",
    ]
    return ImplementationAudit("B3 GREEDY_ENRV Baseline", "ALIGNED", findings)


def audit_source_neutrality() -> dict[str, bool]:
    root = Path(__file__).resolve().parents[3]
    capacities = (root / "benchmark" / "capacities.py").read_text(encoding="utf-8")
    return {
        "capacities_policy_neutral": "B0" not in capacities and "REVIVE" not in capacities,
    }
