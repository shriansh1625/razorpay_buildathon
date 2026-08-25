"""Freeze readiness scorecard — M13.5 §28–29."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.config.policy_pack import default_draft_policy_pack, official_sealed_policy_pack
from revive.benchmark.official.freeze import check_freeze_prerequisites
from revive.benchmark.official.config import official_benchmark_config


@dataclass
class ScorecardItem:
    name: str
    status: str  # READY | CAUTION | BLOCKED
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


@dataclass
class FreezeReadinessReport:
    items: list[ScorecardItem] = field(default_factory=list)
    official_freeze_allowed: bool = False
    decision: str = "NOT READY FOR OFFICIAL FREEZE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "official_freeze_allowed": self.official_freeze_allowed,
            "items": [i.to_dict() for i in self.items],
        }


def _map_classification(classification: str, positive: tuple[str, ...]) -> str:
    if classification in positive:
        return "READY"
    if "PARTIAL" in classification or "WEAK" in classification or "MODERATE" in classification:
        return "CAUTION"
    if "COLLAPSED" in classification or "LOW" in classification:
        return "BLOCKED"
    return "CAUTION"


def build_freeze_readiness(
    env_cells: list,
    baseline_report,
    scarcity_report,
    action_report,
    natural_report,
    b3_revive_report,
    integrity_report,
    param_report,
    reproduction_identical: bool,
) -> FreezeReadinessReport:
    pack = default_draft_policy_pack()
    official_cfg = official_benchmark_config(policy_pack=official_sealed_policy_pack())
    freeze = check_freeze_prerequisites(official_cfg, policy_pack=pack)

    items: list[ScorecardItem] = []

    # Environment realism
    avg_natural = (
        sum(c.natural_recovery_rate for c in env_cells) / len(env_cells)
        if env_cells
        else 0.0
    )
    avg_sensitive = (
        sum(c.intervention_sensitive_count for c in env_cells) / len(env_cells)
        if env_cells
        else 0.0
    )
    env_ready = avg_natural > 0.05 and avg_sensitive > 5
    items.append(
        ScorecardItem(
            "Environment realism",
            "READY" if env_ready else "CAUTION",
            f"avg_natural_rate={avg_natural:.2f}, avg_intervention_sensitive={avg_sensitive:.1f}",
        )
    )

    items.append(
        ScorecardItem(
            "Baseline separation",
            _map_classification(
                baseline_report.classification,
                ("CLEARLY_SEPARATED",),
            ),
            baseline_report.rationale,
        )
    )

    items.append(
        ScorecardItem(
            "Scarcity",
            _map_classification(
                scarcity_report.classification,
                ("HIGH SCARCITY", "MODERATE SCARCITY"),
            ),
            scarcity_report.rationale
            + (
                "; profile capacity wired via revive.benchmark.capacities"
                if scarcity_report.benchmark_wires_profile_capacities
                else ""
            ),
        )
    )

    items.append(
        ScorecardItem(
            "Action sensitivity",
            _map_classification(
                action_report.classification,
                ("HIGH",),
            ),
            action_report.rationale,
        )
    )

    items.append(
        ScorecardItem(
            "Natural recovery variation",
            _map_classification(
                natural_report.classification,
                ("HEALTHY",),
            ),
            natural_report.rationale,
        )
    )

    items.append(
        ScorecardItem(
            "B3/REVIVE differentiation",
            _map_classification(
                b3_revive_report.classification,
                ("STRONG DISTINCTION",),
            ),
            b3_revive_report.rationale,
        )
    )

    items.append(
        ScorecardItem(
            "Benchmark integrity",
            integrity_report.classification,
            str(integrity_report.checks),
        )
    )

    items.append(
        ScorecardItem(
            "Reproducibility",
            "READY" if reproduction_identical else "BLOCKED",
            "development benchmark reproduction fingerprints",
        )
    )

    items.append(
        ScorecardItem(
            "Policy completeness",
            "BLOCKED",
            f"PolicyPack status={pack.status.value}",
        )
    )

    items.append(
        ScorecardItem(
            "Economic-model completeness",
            "CAUTION",
            "ADR-011/012/013 unresolved; profile capacities wired via revive.benchmark.capacities",
        )
    )

    for prereq in [
        ("ADR-011", "BLOCKED", "epsilon not ACCEPTED"),
        ("ADR-012", "BLOCKED", "official scale not ACCEPTED"),
        ("ADR-013", "BLOCKED", "B1 schedule DRAFT"),
        ("PolicyPack SEALED", "BLOCKED", pack.status.value),
        ("Approver model FROZEN", "BLOCKED", "simulated_v1_provisional"),
        ("Predictor strategy FROZEN", "BLOCKED", "strat_m7_dev"),
        ("Official seed set FROZEN", "BLOCKED", "not declared frozen"),
        ("Generator configuration FROZEN", "BLOCKED", "ADR-012 pending"),
    ]:
        items.append(ScorecardItem(prereq[0], prereq[1], prereq[2]))

    mandatory_blocked = any(
        i.status == "BLOCKED"
        for i in items
        if i.name in {
            "Baseline separation",
            "Scarcity",
            "Natural recovery variation",
            "B3/REVIVE differentiation",
            "Benchmark integrity",
            "Reproducibility",
            "Policy completeness",
        }
    ) or not freeze.complete

    calibration_blocked = any(
        i.status == "BLOCKED"
        for i in items
        if i.name in {
            "Baseline separation",
            "Scarcity",
            "B3/REVIVE differentiation",
            "Natural recovery variation",
        }
    )

    official_allowed = not mandatory_blocked and not calibration_blocked and freeze.complete
    decision = (
        "READY FOR OFFICIAL FREEZE"
        if official_allowed
        else "NOT READY FOR OFFICIAL FREEZE"
    )

    return FreezeReadinessReport(
        items=items,
        official_freeze_allowed=official_allowed,
        decision=decision,
    )
