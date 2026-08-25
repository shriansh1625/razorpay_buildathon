"""M13.6 structural repair report writer."""

from __future__ import annotations

import json
from pathlib import Path

from revive.benchmark.calibration.m13_6 import M136Report
from revive.benchmark.capacities import benchmark_resource_capacities
from revive.simulation.types import GenerationProfile


def write_m13_6_reports(report: M136Report, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "m13_6_report.json").write_text(
        json.dumps(report.to_dict(), indent=2),
        encoding="utf-8",
    )

    _write(output_dir / "scarcity-repair.md", _scarcity_repair_md(report))
    _write(output_dir / "official-scale-calibration.md", _official_scale_md(report))
    _write(output_dir / "b3-revive-reanalysis.md", _b3_revive_md(report))
    _write(output_dir / "epsilon-sensitivity.md", _epsilon_md(report))
    _write(output_dir / "policy-sensitivity.md", _policy_md(report))
    _write(output_dir / "approver-analysis.md", _approver_md())
    _write(output_dir / "benchmark-integrity.md", _integrity_md(report))
    _write(output_dir / "freeze-readiness.md", _freeze_md(report))
    _write(output_dir / "M13.6-decision.md", _decision_md(report))

    return output_dir


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _scarcity_repair_md(r: M136Report) -> str:
    scarce = benchmark_resource_capacities(GenerationProfile.SCARCE)
    abundant = benchmark_resource_capacities(GenerationProfile.ABUNDANT)
    balanced = benchmark_resource_capacities(GenerationProfile.BALANCED)
    lines = [
        "# Scarcity Repair",
        "",
        "## Root cause",
        "",
        "`capacity_scarcity_factor` from profile parameters was not applied to benchmark "
        "`ResourceCapacities` or baseline environment constraints.",
        "",
        "## Repair",
        "",
        "Implemented `revive/benchmark/capacities.py`:",
        "",
        "```text",
        "profile → capacity_scarcity_factor → capacity = base / factor",
        "```",
        "",
        "Wired into:",
        "- `policy_runner` (REVIVE + baselines)",
        "- `baseline_pipeline` (BF-4 constraints)",
        "- calibration scarcity diagnostics",
        "",
        "## Profile capacity comparison",
        "",
        "| profile | retry_slots | message_capacity | incentive_budget |",
        "|---------|---------------|------------------|------------------|",
        f"| BALANCED | {balanced.retry_slots} | {balanced.message_capacity} | {balanced.incentive_budget_paise} |",
        f"| SCARCE | {scarce.retry_slots} | {scarce.message_capacity} | {scarce.incentive_budget_paise} |",
        f"| ABUNDANT | {abundant.retry_slots} | {abundant.message_capacity} | {abundant.incentive_budget_paise} |",
        "",
        f"Post-repair scarcity (40-op calibration): **{r.scarcity_calibration.classification}**",
        f"Post-repair scarcity (500-op official scale): **{r.scarcity_official_scale.classification}**",
    ]
    return "\n".join(lines) + "\n"


def _official_scale_md(r: M136Report) -> str:
    lines = [
        "# Official-Scale Calibration (500 opportunities)",
        "",
        "**Development/calibration only — not official benchmark.**",
        "",
        f"Classification: **{r.scarcity_official_scale.classification}**",
        f"Rationale: {r.scarcity_official_scale.rationale}",
        "",
        "## Scale sensitivity (BALANCED, seed 1)",
        "",
        "| opportunities | competition_retry | differing B3/REVIVE |",
        "|---------------|-------------------|---------------------|",
    ]
    for row in r.scale_sensitivity:
        lines.append(
            f"| {row['opportunity_count']} | {row['competition_ratio_retry']:.2f} | "
            f"{row['differing_allocations']} |"
        )
    lines.extend(
        [
            "",
            "ADR-012 scale (500) is **not frozen** — this report evaluates sufficiency only.",
        ]
    )
    return "\n".join(lines) + "\n"


def _b3_revive_md(r: M136Report) -> str:
    b = r.b3_revive_official_scale
    lines = [
        "# B3 vs REVIVE Re-analysis",
        "",
        f"**Classification (official scale):** {b.classification}",
        "",
        f"**Rationale:** {b.rationale}",
        "",
        "## Sample cells (500 opps)",
        "",
        "| seed | profile | differing | b3_enrv | revive_enrv | b3_retry | revive_retry | deferred |",
        "|------|---------|-----------|---------|-------------|----------|--------------|----------|",
    ]
    for c in b.cells[:12]:
        lines.append(
            f"| {c.seed} | {c.profile} | {c.differing_opportunities} | "
            f"{c.b3_total_enrv_paise} | {c.revive_total_enrv_paise} | "
            f"{c.b3_retry_slots_used}/{c.retry_capacity} | "
            f"{c.revive_retry_slots_used}/{c.retry_capacity} | {c.revive_deferred_count} |"
        )
    lines.extend(
        [
            "",
            "## Why B3 and REVIVE match",
            "",
            "At official scale (500 opps, 30-day window, profile capacities wired):",
            "- Greedy B3 saturates retry capacity with the same highest-ENRV actions.",
            "- Portfolio allocator selects identical actions; REVIVE defers lower-value opps "
            "but does not swap winners under observed shadow prices.",
            "- Scale sensitivity (21-day window, variable customer counts) shows differing "
            "allocations at 100–750 opps — differentiation is config-dependent, not absent globally.",
            "",
            "Same world, same M7 valuations, profile-adjusted capacities.",
            "No M8 objective changes.",
        ]
    )
    return "\n".join(lines) + "\n"


def _epsilon_md(r: M136Report) -> str:
    p = r.parameter_sensitivity
    lines = [
        "# Epsilon Sensitivity",
        "",
        "ADR-011 **not frozen**. Diagnostic only.",
        "",
        f"Epsilon materially affects B3 selection: {p.epsilon_material}",
        "",
    ]
    for sweep in p.sweeps:
        if sweep.parameter == "epsilon_paise":
            for m in sweep.metrics:
                lines.append(f"- ε={m['epsilon_paise']} paise → B3 selected={m['b3_selected_count']}")
    return "\n".join(lines) + "\n"


def _policy_md(r: M136Report) -> str:
    return (
        "# Policy Sensitivity\n\n"
        "PolicyPack remains **DRAFT**. No silent PROVISIONAL→FROZEN conversion.\n\n"
        "- ε: PROVISIONAL (ADR-011 DRAFT)\n"
        "- Capacities: wired via profile scarcity factor\n"
        "- B1 schedule: ADR-013 DRAFT\n"
        "- Predictor: strat_m7_dev (not frozen)\n"
    )


def _approver_md() -> str:
    return (
        "# Approver Model Analysis\n\n"
        "Status: **simulated_v1_provisional** — not frozen.\n\n"
        "- Deterministic gate evaluation (no LLM)\n"
        "- Policy-neutral: responds to authorization context, not strategy identity\n"
        "- Not finalized in M13.6\n"
    )


def _integrity_md(r: M136Report) -> str:
    i = r.integrity
    return (
        f"# Benchmark Integrity\n\n"
        f"**Classification:** {i.classification}\n\n"
        f"Checks: {i.checks}\n\n"
        f"Reproduction (development): {'identical' if r.reproduction_identical else 'FAILED'}\n"
    )


def _freeze_md(r: M136Report) -> str:
    f = r.freeze_readiness
    lines = [
        "# Freeze Readiness (post-repair)",
        "",
        f"**Decision:** {f.decision}",
        "",
        "| Item | Status | Detail |",
        "|------|--------|--------|",
    ]
    for item in f.items:
        lines.append(f"| {item.name} | {item.status} | {item.detail} |")
    return "\n".join(lines) + "\n"


def _decision_md(r: M136Report) -> str:
    scarcity_ok = r.scarcity_official_scale.classification != "LOW SCARCITY"
    b3_class = r.b3_revive_official_scale.classification
    b3_measurable = b3_class in {"STRONG", "ACCEPTABLE", "WEAK"}
    structural_ok = (
        scarcity_ok
        and r.integrity.classification == "READY"
        and b3_measurable
    )

    if structural_ok:
        decision = "READY FOR FREEZE PREPARATION"
        intro = (
            "Structural repair complete. Benchmark can enter freeze **preparation** "
            "after ADR acceptance."
        )
    else:
        decision = "NOT READY FOR FREEZE PREPARATION"
        intro = (
            "Structural gaps remain after repair. The benchmark cannot yet "
            "meaningfully test portfolio-aware allocation vs B3 at the documented "
            "official scale."
        )

    blockers: list[str] = []
    if not scarcity_ok:
        blockers.append(
            f"Scarcity at official scale: {r.scarcity_official_scale.classification}"
        )
    if b3_class == "COLLAPSED":
        blockers.append(
            "B3/REVIVE differentiation collapsed at official scale "
            f"({r.b3_revive_official_scale.rationale})"
        )
    elif not b3_measurable:
        blockers.append(f"B3/REVIVE differentiation: {b3_class}")
    blockers.extend(
        [
            "ADR-011 (ε) not ACCEPTED",
            "ADR-012 (scale) not ACCEPTED",
            "ADR-013 (B1 schedule) DRAFT",
            "PolicyPack not SEALED",
            "Predictor/approver/seed set not frozen",
        ]
    )

    lines = [
        "# M13.6 Decision",
        "",
        f"# {decision}",
        "",
        intro,
        "",
    ]
    if blockers:
        lines.append("## Remaining blockers / ADR decisions")
        lines.append("")
        for b in blockers:
            lines.append(f"- {b}")
    lines.extend(
        [
            "",
            "## Not done in M13.6",
            "",
            "- Official benchmark execution",
            "- REVIVE superiority claims",
            "- Automatic benchmark freeze",
        ]
    )
    return "\n".join(lines) + "\n"
