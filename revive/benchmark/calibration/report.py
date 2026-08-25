"""Write M13.5 calibration markdown reports."""

from __future__ import annotations

import json
from pathlib import Path

from revive.benchmark.calibration.runner import CalibrationReport


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_calibration_reports(
    report: CalibrationReport,
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write(output_dir / "calibration_report.json", json.dumps(report.to_dict(), indent=2))

    _write(
        output_dir / "environment-diagnostics.md",
        _environment_md(report),
    )
    _write(output_dir / "baseline-separation.md", _baseline_md(report))
    _write(output_dir / "scarcity-analysis.md", _scarcity_md(report))
    _write(output_dir / "action-sensitivity.md", _action_md(report))
    _write(output_dir / "natural-recovery-analysis.md", _natural_md(report))
    _write(output_dir / "profile-analysis.md", _profile_md(report))
    _write(output_dir / "parameter-sensitivity.md", _parameter_md(report))
    _write(output_dir / "b3-vs-revive-diagnostics.md", _b3_revive_md(report))
    _write(output_dir / "freeze-readiness.md", _freeze_md(report))
    _write(output_dir / "M13.5-decision.md", _decision_md(report))

    return output_dir


def _environment_md(r: CalibrationReport) -> str:
    lines = [
        "# Environment Diagnostics",
        "",
        "Oracle-side analysis — no REVIVE superiority claims.",
        "",
        f"Cells analyzed: {len(r.environment_cells)}",
        "",
        "## Per-cell summary",
        "",
        "| seed | profile | opps | gross VAR (paise) | natural rate | intervention-sensitive | non-recoverable |",
        "|------|---------|------|-------------------|--------------|------------------------|-----------------|",
    ]
    for c in r.environment_cells:
        lines.append(
            f"| {c.seed} | {c.profile} | {c.opportunity_count} | {c.gross_value_at_risk_paise} | "
            f"{c.natural_recovery_rate:.2f} | {c.intervention_sensitive_count} | {c.non_recoverable_count} |"
        )

    if r.environment_cells:
        avg_nat = sum(c.natural_recovery_rate for c in r.environment_cells) / len(
            r.environment_cells
        )
        lines.extend(
            [
                "",
                f"**Average natural recovery rate:** {avg_nat:.2f}",
                "",
                "## Interpretation",
                "",
                "The environment contains recoverable revenue when natural rate and "
                "intervention-sensitive counts are non-trivial. Zero M-10 at tiny scale "
                "does not imply absent recoverable revenue at calibration scale.",
            ]
        )
    return "\n".join(lines) + "\n"


def _baseline_md(r: CalibrationReport) -> str:
    b = r.baseline_separation
    lines = [
        "# Baseline Separation",
        "",
        f"**Classification:** {b.classification}",
        "",
        f"**Rationale:** {b.rationale}",
        "",
        "## Mid-cycle snapshot (selected count by policy)",
        "",
        "| seed | profile | B0 | B1 | B2 | B3 |",
        "|------|---------|----|----|----|-----|",
    ]
    by_cell: dict[tuple[int, str], dict[str, int]] = {}
    for s in b.snapshots:
        by_cell.setdefault((s.seed, s.profile), {})[s.policy_id] = s.selected_count
    for (seed, profile), counts in sorted(by_cell.items()):
        lines.append(
            f"| {seed} | {profile} | {counts.get('B0', 0)} | {counts.get('B1', 0)} | "
            f"{counts.get('B2', 0)} | {counts.get('B3', 0)} |"
        )
    lines.extend(
        [
            "",
            "Baselines were not modified based on these results.",
        ]
    )
    return "\n".join(lines) + "\n"


def _scarcity_md(r: CalibrationReport) -> str:
    s = r.scarcity
    lines = [
        "# Scarcity Analysis",
        "",
        f"**Classification:** {s.classification}",
        "",
        f"**Rationale:** {s.rationale}",
        "",
        f"**M13 runner wires profile capacities:** {s.benchmark_wires_profile_capacities}",
        "",
        "Diagnostic uses `capacity_scarcity_factor` from profile parameters to adjust "
        "ResourceCapacities — this mapping is **not yet applied** in the M13 official runner.",
        "",
        "| seed | profile | +ENRV cands | retry demand | retry cap | competition retry |",
        "|------|---------|-------------|--------------|-----------|-------------------|",
    ]
    for c in s.cells:
        lines.append(
            f"| {c.seed} | {c.profile} | {c.positive_enrv_candidates} | {c.total_retry_demand} | "
            f"{c.retry_capacity} | {c.competition_ratio_retry:.2f} |"
        )
    return "\n".join(lines) + "\n"


def _action_md(r: CalibrationReport) -> str:
    a = r.action_sensitivity
    lines = [
        "# Action Sensitivity",
        "",
        f"**Classification:** {a.classification}",
        "",
        f"**Rationale:** {a.rationale}",
        "",
        f"Average recovering actions per opportunity: {a.avg_recovering_actions_per_opp:.2f}",
        "",
        "## Per-action oracle recovery rate (sample)",
        "",
    ]
    for code, rate in sorted(a.action_recovery_rates.items()):
        lines.append(f"- `{code}`: {rate:.2f}")
    return "\n".join(lines) + "\n"


def _natural_md(r: CalibrationReport) -> str:
    n = r.natural_recovery
    lines = [
        "# Natural Recovery Analysis",
        "",
        f"**Classification:** {n.classification}",
        "",
        f"**Rationale:** {n.rationale}",
        "",
        f"Rate range: [{n.overall_min_rate:.2f}, {n.overall_max_rate:.2f}], std={n.overall_std:.3f}",
        "",
        f"Low incremental-value cells: {n.low_incremental_cells}",
        f"High incremental-value cells: {n.high_incremental_cells}",
    ]
    return "\n".join(lines) + "\n"


def _profile_md(r: CalibrationReport) -> str:
    from revive.simulation.profiles import PROFILE_PARAMETERS

    lines = [
        "# Profile Analysis",
        "",
        "Profiles must differ through documented mechanisms, not row count alone.",
        "",
        "## Documented profile parameters",
        "",
        "| profile | natural_mult | scarcity_factor | adversarial | degradation |",
        "|---------|----------------|-----------------|-------------|-------------|",
    ]
    for profile, params in PROFILE_PARAMETERS.items():
        lines.append(
            f"| {profile.value} | {params.natural_recovery_multiplier} | "
            f"{params.capacity_scarcity_factor} | {params.adversarial_injection} | "
            f"{params.degradation_intensity} |"
        )

    lines.extend(["", "## Observed natural recovery by profile", ""])
    by_profile: dict[str, list[float]] = {}
    for c in r.environment_cells:
        by_profile.setdefault(c.profile, []).append(c.natural_recovery_rate)
    for profile, rates in sorted(by_profile.items()):
        avg = sum(rates) / len(rates)
        lines.append(f"- **{profile}**: avg natural rate={avg:.2f} (n={len(rates)} seeds)")

    lines.extend(
        [
            "",
            "## Profile integrity note",
            "",
            "HIGH_NATURAL shows elevated natural rates vs SCARCE/BALANCED when measured — "
            "profile overlays affect oracle natural probability via `natural_recovery_multiplier`.",
            "SCARCE `capacity_scarcity_factor=2.5` is documented but **not wired** to benchmark "
            "ResourceCapacities in M13 runner (implementation gap).",
        ]
    )
    return "\n".join(lines) + "\n"


def _parameter_md(r: CalibrationReport) -> str:
    p = r.parameter_sensitivity
    lines = [
        "# Parameter Sensitivity",
        "",
        f"Epsilon materially changes selection: {p.epsilon_material}",
        "",
        "## Notes",
        "",
    ]
    for note in p.notes:
        lines.append(f"- {note}")

    for sweep in p.sweeps:
        lines.extend(["", f"### Sweep: {sweep.parameter}", ""])
        for m in sweep.metrics:
            lines.append(f"- {m}")

    lines.extend(
        [
            "",
            "Diagnostic only — no parameter tuned toward a desired winner.",
        ]
    )
    return "\n".join(lines) + "\n"


def _b3_revive_md(r: CalibrationReport) -> str:
    b = r.b3_revive
    lines = [
        "# B3 vs REVIVE Diagnostics",
        "",
        f"**Classification:** {b.classification}",
        "",
        f"**Rationale:** {b.rationale}",
        "",
        "Compares raw ENRV greedy (B3) vs Lagrangian portfolio allocation (REVIVE) "
        "on identical portfolio items at mid-cycle.",
        "",
        "| seed | profile | opps | differing | b3_only | revive_only |",
        "|------|---------|------|-----------|---------|-------------|",
    ]
    for c in b.cells:
        lines.append(
            f"| {c.seed} | {c.profile} | {c.opportunity_count} | {c.differing_opportunities} | "
            f"{c.b3_only_selected} | {c.revive_only_selected} |"
        )
    return "\n".join(lines) + "\n"


def _freeze_md(r: CalibrationReport) -> str:
    f = r.freeze_readiness
    lines = [
        "# Freeze Readiness Scorecard",
        "",
        f"**Decision:** {f.decision}",
        "",
        f"**Official freeze allowed:** {f.official_freeze_allowed}",
        "",
        "| Item | Status | Detail |",
        "|------|--------|--------|",
    ]
    for item in f.items:
        lines.append(f"| {item.name} | {item.status} | {item.detail} |")
    return "\n".join(lines) + "\n"


def _decision_md(r: CalibrationReport) -> str:
    f = r.freeze_readiness
    blockers = [i for i in f.items if i.status == "BLOCKED"]
    lines = [
        "# M13.5 Decision",
        "",
        f"# {f.decision}",
        "",
    ]
    if blockers:
        lines.append("## Blockers")
        lines.append("")
        for b in blockers:
            lines.append(f"- **{b.name}**: {b.detail}")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "M13.5 calibration diagnostics completed. No official benchmark was run.",
            "No benchmark superiority claims are made.",
            "",
            f"Reproduction (development): {'identical' if r.reproduction_identical else 'FAILED'}",
        ]
    )
    return "\n".join(lines) + "\n"
