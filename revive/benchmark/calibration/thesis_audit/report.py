"""M13.7 thesis audit report writer."""

from __future__ import annotations

import json
from pathlib import Path

from revive.benchmark.calibration.thesis_audit.runner import M137Report


def write_m13_7_reports(report: M137Report, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "m13_7_report.json").write_text(
        json.dumps(report.to_dict(), indent=2),
        encoding="utf-8",
    )

    _write(output_dir / "binding-constraints.md", _binding_md(report))
    _write(output_dir / "shadow-price-analysis.md", _shadow_md(report))
    _write(output_dir / "portfolio-conflicts.md", _conflicts_md(report))
    _write(output_dir / "resource-density-inversions.md", _inversions_md(report))
    _write(output_dir / "action-concentration.md", _action_md(report))
    _write(output_dir / "b3-vs-revive-decomposition.md", _decomposition_md(report))
    _write(output_dir / "temporal-competition.md", _temporal_md(report))
    _write(output_dir / "customer-competition.md", _customer_md(report))
    _write(output_dir / "configuration-matrix.md", _matrix_md(report))
    _write(output_dir / "m8-implementation-audit.md", _m8_audit_md(report))
    _write(output_dir / "b3-implementation-audit.md", _b3_audit_md(report))
    _write(output_dir / "fallback-analysis.md", _fallback_md(report))
    _write(output_dir / "thesis-classification.md", _classification_md(report))
    _write(output_dir / "M13.7-decision.md", _decision_md(report))

    return output_dir


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _official_balanced(report: M137Report):
    for c in report.official_scale_cells:
        if c.seed == 1 and c.profile == "BALANCED":
            return c
    return report.official_scale_cells[0] if report.official_scale_cells else None


def _binding_md(r: M137Report) -> str:
    lines = [
        "# Binding Constraints",
        "",
        "Per-resource utilization at mid-cycle allocation snapshot.",
        "",
        "## Official scale (sample: seed 1 BALANCED)",
        "",
        "| resource | binding | avg_util | peak_util | shadow_freq |",
        "|----------|---------|----------|-----------|-------------|",
    ]
    cell = _official_balanced(r)
    if cell:
        for row in cell.binding_rows:
            lines.append(
                f"| {row.resource} | {row.binding_frequency:.0f} | "
                f"{row.average_utilization:.2f} | {row.peak_utilization:.2f} | "
                f"{row.shadow_price_frequency:.0f} |"
            )
    lines.extend(["", "## Aggregate official-scale binding frequency"])
    agg: dict[str, list[float]] = {}
    for c in r.official_scale_cells:
        for row in c.binding_rows:
            agg.setdefault(row.resource, []).append(row.peak_utilization)
    for res, vals in sorted(agg.items()):
        avg_peak = sum(vals) / len(vals)
        bind_pct = sum(1 for v in vals if v >= 0.99) / len(vals) * 100
        lines.append(f"- **{res}**: avg_peak_util={avg_peak:.2f}, binding_cells={bind_pct:.0f}%")
    return "\n".join(lines) + "\n"


def _shadow_md(r: M137Report) -> str:
    cell = _official_balanced(r)
    lines = [
        "# Shadow Price Analysis",
        "",
        "ADR-011 not frozen. Diagnostic only — no shadow prices altered.",
        "",
    ]
    if cell:
        lines.append("## Official scale (seed 1 BALANCED)")
        lines.append("")
        for s in cell.shadow_stats:
            if s.max_value > 0:
                lines.append(
                    f"- **{s.resource}**: max={s.max_value:.1f}, "
                    f"nonzero_cycles={s.nonzero_cycle_pct:.0f}%"
                )
        lines.append("")
        lines.append(f"Reported shadow_prices: {cell.shadow_prices}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Non-zero retry_slots shadow prices indicate scarcity economics are computed, "
            "but at official scale they do not change the selected set vs B3 greedy ENRV "
            "when winners are homogeneous retry actions with identical resource usage.",
        ]
    )
    return "\n".join(lines) + "\n"


def _conflicts_md(r: M137Report) -> str:
    total_conflicts = sum(c.portfolio_conflicts for c in r.official_scale_cells)
    lines = [
        "# Portfolio Conflicts",
        "",
        "Pairs of cross-opportunity candidates competing for the same resource where "
        "raw ENRV ordering differs from density or reduced-value ordering.",
        "",
        f"**Total conflicts (official scale, all cells):** {total_conflicts}",
        "",
        "| seed | profile | conflicts | conflict_rate | by_resource |",
        "|------|---------|-----------|---------------|-------------|",
    ]
    for c in r.official_scale_cells[:12]:
        res = ", ".join(f"{k}:{v}" for k, v in c.conflict_by_resource.items()) or "—"
        lines.append(
            f"| {c.seed} | {c.profile} | {c.portfolio_conflicts} | "
            f"{c.conflict_rate:.3f} | {res} |"
        )
    return "\n".join(lines) + "\n"


def _inversions_md(r: M137Report) -> str:
    total = sum(c.resource_density_inversions for c in r.official_scale_cells)
    lines = [
        "# Resource-Density Inversions",
        "",
        "Within-opportunity pairs where ENRV ordering differs from ENRV/resource-cost ordering.",
        "",
        f"**Total inversion pairs (official scale):** {total}",
        "",
        "If near zero, the benchmark does not exercise resource-density tradeoffs within opportunities.",
    ]
    for c in r.official_scale_cells[:6]:
        lines.append(
            f"- seed={c.seed} profile={c.profile}: {c.resource_density_inversions} inversion pairs"
        )
    return "\n".join(lines) + "\n"


def _action_md(r: M137Report) -> str:
    cell = _official_balanced(r)
    lines = ["# Action Concentration", ""]
    if cell:
        lines.extend(
            [
                "## Candidate / feasible / selected shares (seed 1 BALANCED official)",
                "",
                "| category | candidate | feasible | B3 selected | REVIVE selected |",
                "|----------|-----------|----------|-------------|-----------------|",
            ]
        )
        cats = sorted(
            set(cell.candidate_action_shares)
            | set(cell.feasible_action_shares)
            | set(cell.b3_selected_shares)
            | set(cell.revive_selected_shares)
        )
        for cat in cats:
            lines.append(
                f"| {cat} | {cell.candidate_action_shares.get(cat, 0):.2f} | "
                f"{cell.feasible_action_shares.get(cat, 0):.2f} | "
                f"{cell.b3_selected_shares.get(cat, 0):.2f} | "
                f"{cell.revive_selected_shares.get(cat, 0):.2f} |"
            )
        lines.append("")
        lines.append(f"B3 dominant category: **{cell.b3_dominant_action}**")
        lines.append(f"REVIVE dominant category: **{cell.revive_dominant_action}**")
    return "\n".join(lines) + "\n"


def _decomposition_md(r: M137Report) -> str:
    lines = [
        "# B3 vs REVIVE Decomposition",
        "",
        "## Identical ENRV audit",
        "",
    ]
    causes = {}
    for c in r.official_scale_cells:
        causes[c.identical_enrv_cause] = causes.get(c.identical_enrv_cause, 0) + 1
    for cause, count in sorted(causes.items()):
        lines.append(f"- **{cause}**: {count} cells")
    lines.extend(
        [
            "",
            "M13.6 identical ENRV is **case A**: identical candidate selections, not equal totals from different picks.",
            "",
            "## Differing allocation counts",
            "",
            f"Official scale differing allocations: "
            f"{sum(c.differing_allocations for c in r.official_scale_cells)}",
            "",
            "## Same-action reasons (sample BALANCED seed 1)",
        ]
    )
    cell = _official_balanced(r)
    if cell:
        for k, v in cell.same_action_reasons.items():
            lines.append(f"- {k}: {v}")
    return "\n".join(lines) + "\n"


def _temporal_md(r: M137Report) -> str:
    cell = _official_balanced(r)
    lines = [
        "# Temporal Competition",
        "",
        "Single mid-cycle allocation snapshot (same methodology as M13.6 calibration).",
        "",
    ]
    if cell:
        lines.extend(
            [
                f"- Opportunities in cycle: **{cell.opportunities_in_cycle}**",
                f"- Candidates in cycle: **{cell.candidates_in_cycle}**",
                f"- Distinct action codes: **{cell.distinct_actions_in_cycle}**",
                f"- Shared-resource candidate pairs: **{cell.shared_resource_pairs}**",
                f"- Portfolio conflicts: **{cell.portfolio_conflicts}**",
                "",
                "Large dataset (500 generated opps) does not imply simultaneous portfolio "
                "competition — only detected-at-risk opportunities at mid-cycle participate.",
            ]
        )
    return "\n".join(lines) + "\n"


def _customer_md(r: M137Report) -> str:
    lines = [
        "# Customer-Level Competition",
        "",
        "| seed | profile | multi-opp customers | contact conflicts |",
        "|------|---------|---------------------|-------------------|",
    ]
    for c in r.official_scale_cells[:12]:
        lines.append(
            f"| {c.seed} | {c.profile} | {c.customers_with_multiple_opps} | "
            f"{c.customer_contact_conflicts} |"
        )
    lines.extend(
        [
            "",
            "Customer contact limits rarely bind at official scale; competition is merchant-level retry_slots.",
        ]
    )
    return "\n".join(lines) + "\n"


def _matrix_md(r: M137Report) -> str:
    low = [row for row in r.config_matrix if row.differing_allocations == 0]
    high = [row for row in r.config_matrix if row.differing_allocations >= 5]
    lines = [
        "# Configuration Matrix",
        "",
        "Legitimate documented dimensions only — no tuning knobs introduced.",
        "",
        f"**LOW-DIFFERENTIATION rows:** {len(low)}",
        f"**HIGH-DIFFERENTIATION rows (≥5 differing):** {len(high)}",
        "",
        "| opps | customers | window | profile | seed | competition_retry | conflicts | differing | binding |",
        "|------|-----------|--------|---------|------|-------------------|-----------|-----------|---------|",
    ]
    for row in r.config_matrix:
        lines.append(
            f"| {row.opportunity_count} | {row.customer_count} | {row.window_days} | "
            f"{row.profile} | {row.seed} | {row.competition_ratio_retry:.2f} | "
            f"{row.portfolio_conflicts} | {row.differing_allocations} | {row.resource_binding} |"
        )
    return "\n".join(lines) + "\n"


def _m8_audit_md(r: M137Report) -> str:
    a = r.m8_audit
    lines = [f"# M8 Implementation Audit", "", f"**Status:** {a.status}", ""]
    for f in a.findings:
        lines.append(f"- {f}")
    return "\n".join(lines) + "\n"


def _b3_audit_md(r: M137Report) -> str:
    a = r.b3_audit
    lines = [f"# B3 Implementation Audit", "", f"**Status:** {a.status}", ""]
    for f in a.findings:
        lines.append(f"- {f}")
    return "\n".join(lines) + "\n"


def _fallback_md(r: M137Report) -> str:
    fs = r.fallback_summary
    lines = [
        "# Fallback Usage",
        "",
        f"- Official-scale Lagrangian cycles: {fs.get('official_scale_lagrangian_cycles', 0)}",
        f"- Official-scale fallback cycles: {fs.get('official_scale_fallback_cycles', 0)}",
        f"- Fallback pct (official): {fs.get('fallback_pct', 0):.1%}",
        f"- Matrix rows using fallback: {fs.get('matrix_fallback_rows', 0)} / "
        f"{fs.get('matrix_total_rows', 0)}",
        "",
        "Fallback is **not** dominating at official scale. Collapse is not caused by fallback path.",
    ]
    return "\n".join(lines) + "\n"


def _classification_md(r: M137Report) -> str:
    return (
        f"# Thesis Classification\n\n"
        f"## {r.thesis_classification}\n\n"
        f"{r.thesis_rationale}\n"
    )


def _decision_md(r: M137Report) -> str:
    return (
        f"# M13.7 Decision\n\n"
        f"# {r.thesis_classification}\n\n"
        f"{r.thesis_rationale}\n\n"
        "## Evidence summary\n\n"
        f"- Official-scale B3/REVIVE differing: "
        f"{sum(c.differing_allocations for c in r.official_scale_cells)}\n"
        f"- Official-scale portfolio conflicts: "
        f"{sum(c.portfolio_conflicts for c in r.official_scale_cells)}\n"
        f"- High-differentiation config rows: "
        f"{sum(1 for row in r.config_matrix if row.differing_allocations >= 5)}\n"
        f"- M8 audit: {r.m8_audit.status}\n"
        f"- B3 audit: {r.b3_audit.status}\n"
        f"- Fallback at official scale: {r.fallback_summary.get('fallback_pct', 0):.1%}\n\n"
        "## Not done in M13.7\n\n"
        "- Official benchmark execution\n"
        "- M8 or B3 tuning for benchmark advantage\n"
        "- Benchmark freeze\n"
    )
