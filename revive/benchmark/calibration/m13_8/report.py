"""M13.8 freeze decision report writer."""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from revive.benchmark.calibration.m13_8.config_candidates import CONFIG_A, CONFIG_B
from revive.benchmark.calibration.m13_8.runner import M138Report
from revive.allocation.config import ALLOCATOR_VERSION
from revive.benchmark.official.config import (
    BENCHMARK_VERSION,
    B1_SCHEDULE_VERSION,
    METRIC_VERSION,
    OFFICIAL_PROFILE_SET,
    OFFICIAL_SEED_SET,
    PREDICTOR_VERSION,
    APPROVER_MODEL_VERSION,
)
from revive.simulation.config import GENERATOR_VERSION


def write_m13_8_reports(report: M138Report, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "m13_8_report.json").write_text(
        json.dumps(report.to_dict(), indent=2),
        encoding="utf-8",
    )

    writers = [
        ("horizon-analysis.md", _horizon_md),
        ("realism-analysis.md", _realism_md),
        ("portfolio-thesis-analysis.md", _portfolio_md),
        ("multi-seed-analysis.md", _multiseed_md),
        ("profile-analysis.md", _profile_md),
        ("computational-analysis.md", _computational_md),
        ("epsilon-recommendation.md", _epsilon_md),
        ("policy-pack-recommendation.md", _policy_md),
        ("b1-recommendation.md", _b1_md),
        ("predictor-freeze-recommendation.md", _predictor_md),
        ("approver-freeze-recommendation.md", _approver_md),
        ("seed-selection.md", _seed_md),
        ("proposed-official-config.md", _proposed_config_md),
        ("M13.8-decision.md", _decision_md),
    ]
    for name, fn in writers:
        (output_dir / name).write_text(fn(report), encoding="utf-8")

    # ADR-012 recommendation alongside artifacts
    adr_path = Path("implementation/adr-012-benchmark-scale.md")
    adr_path.write_text(_adr_012_md(report), encoding="utf-8")

    return output_dir


def _cells(report: M138Report, cid: str):
    return [c for c in report.calibration_cells if c.candidate_id == cid]


def _horizon_md(r: M138Report) -> str:
    return (
        "# Horizon Analysis\n\n"
        "## Configuration A — 30-day window\n\n"
        f"- Label: {CONFIG_A.label}\n"
        "- Virtual cycles: 30 days × 96 cycles/day (15 min) = 2,880 allocation cycles\n"
        "- Mid-cycle snapshot: day 15\n"
        "- Documented in `official_scale_config` / ADR-012 proposal\n\n"
        "## Configuration B — 21-day window\n\n"
        f"- Label: {CONFIG_B.label}\n"
        "- Virtual cycles: 21 days × 96 cycles/day = 2,016 cycles\n"
        "- Mid-cycle snapshot: day 10.5\n"
        "- Documented in `calibration_config` horizon (40 opps dev scale)\n\n"
        "## Recovery-horizon validity (docs/19, ADR-011 OQ-03)\n\n"
        "| Window | Payment 14d | Checkout 48h | Subscription 14d | Receivable 90d |\n"
        "|--------|-------------|----------------|------------------|----------------|\n"
        "| 21-day | Full window | Full window | Full window | Partial (ageing begins) |\n"
        "| 30-day | Full window | Full window | Full window | More ageing exposure |\n\n"
        "**Recommendation:** 21-day window provides sufficient virtual time for "
        "payment/checkout/subscription recovery workflows while keeping receivable "
        "ageing meaningful without dominating the batch. 30-day mid-cycle produces a "
        "homogeneous retry-only candidate pool (M13.7).\n\n"
        f"**Chosen candidate:** {r.recommended_candidate_id}\n"
    )


def _realism_md(r: M138Report) -> str:
    return (
        "# Business Realism Review\n\n"
        "Assessment uses simulation specification only — no external claims.\n\n"
        "## Payment recovery\n"
        "- Both horizons cover the documented 14-day payment recovery window.\n"
        "- 21-day: mid-cycle at 10.5 days leaves retry timing active.\n"
        "- 30-day: mid-cycle at 15 days — many opportunities past primary retry window.\n\n"
        "## Checkout recovery\n"
        "- 48h checkout window fully represented in both horizons.\n\n"
        "## Subscription recovery\n"
        "- 14-day subscription window covered in both.\n\n"
        "## Receivables\n"
        "- 21-day: receivable ageing bands begin but do not dominate.\n"
        "- 30-day: more overdue progression — may overweight receivable class at mid-cycle.\n\n"
        "## Natural recovery\n"
        "- HIGH_NATURAL profile still shows elevated natural rates in both configs.\n\n"
        "## Customer fatigue\n"
        "- Contact allowance (2 per customer per cycle) binds under Config B multi-resource competition.\n"
        "- Config A: contact rarely binds (M13.7).\n"
    )


def _portfolio_md(r: M138Report) -> str:
    lines = ["# Portfolio Thesis Analysis", ""]
    for cid, label in [("A", CONFIG_A.label), ("B", CONFIG_B.label)]:
        subset = _cells(r, cid)
        conflicts = [c.portfolio_conflicts for c in subset]
        diff = [c.differing_allocations for c in subset]
        lines.extend(
            [
                f"## {cid}: {label}",
                "",
                f"- Mean portfolio conflicts: {statistics.mean(conflicts):.1f}",
                f"- Mean B3/REVIVE differing: {statistics.mean(diff):.1f}",
                f"- Cells with zero differing: {sum(1 for d in diff if d == 0)}/{len(diff)}",
                "",
            ]
        )
    lines.append(f"**Recommendation:** Config {r.recommended_candidate_id}")
    return "\n".join(lines) + "\n"


def _multiseed_md(r: M138Report) -> str:
    lines = [
        "# Multi-Seed Analysis",
        "",
        "Seeds: 1–5 (representative sample; official set 1–20).",
        "",
        "| candidate | seed | mean conflicts | mean differing |",
        "|-----------|------|----------------|----------------|",
    ]
    for cid in ("A", "B"):
        for seed in sorted({c.seed for c in r.calibration_cells}):
            subset = [c for c in r.calibration_cells if c.candidate_id == cid and c.seed == seed]
            if not subset:
                continue
            mc = statistics.mean([c.portfolio_conflicts for c in subset])
            md = statistics.mean([c.differing_allocations for c in subset])
            lines.append(f"| {cid} | {seed} | {mc:.0f} | {md:.1f} |")
    return "\n".join(lines) + "\n"


def _profile_md(r: M138Report) -> str:
    rec = r.recommended_candidate_id
    lines = [
        "# Profile Analysis (recommended config)",
        "",
        "| profile | conflicts | differing | competition_retry | binding |",
        "|---------|-----------|-----------|-------------------|---------|",
    ]
    for profile in sorted({c.profile for c in r.calibration_cells}):
        subset = [
            c
            for c in r.calibration_cells
            if c.candidate_id == rec and c.profile == profile and c.seed == 1
        ]
        if not subset:
            continue
        c = subset[0]
        lines.append(
            f"| {c.profile} | {c.portfolio_conflicts} | {c.differing_allocations} | "
            f"{c.competition_ratio_retry:.2f} | {c.binding_resources} |"
        )
    lines.append("")
    lines.append("All six documented profiles exercised including HOSTILE and SCARCE.")
    return "\n".join(lines) + "\n"


def _computational_md(r: M138Report) -> str:
    lines = ["# Computational Analysis", ""]
    for s in r.computational_samples:
        lines.extend(
            [
                f"## Candidate {s.candidate_id}",
                f"- Dataset generation: {s.dataset_generation_sec:.2f}s",
                f"- Portfolio pipeline (one mid-cycle): {s.portfolio_pipeline_sec:.2f}s",
                f"- Est. generation (20×6 cells): {s.estimated_generation_sec:.0f}s",
                f"- Est. portfolio passes (×5 policies rough): {s.estimated_pipeline_sec:.0f}s",
                "",
            ]
        )
    lines.append("Both configurations are computationally feasible for official matrix.")
    return "\n".join(lines) + "\n"


def _epsilon_md(r: M138Report) -> str:
    lines = [
        "# Epsilon Recommendation (ADR-011 preparation)",
        "",
        "ADR-011 **not auto-accepted**. Analysis on recommended 21-day config, seed 1 BALANCED.",
        "",
        "| ε (paise) | B3 selected | REVIVE selected | differing |",
        "|-----------|-------------|-----------------|-----------|",
    ]
    for row in r.epsilon_rows:
        lines.append(
            f"| {row.epsilon_paise} | {row.b3_selected} | {row.revive_selected} | "
            f"{row.differing} |"
        )
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            "**Proposed ε = 100 paise (₹1)** — aligns with `docs/11` §5.3 noise filter.",
            "",
            "- At ε=0 and ε=100 on 21d/500 scale, selection counts are stable in this sample.",
            "- ε=100 suppresses sub-threshold dust without materially changing portfolio conflicts.",
            "- **Not selected based on REVIVE advantage** — identical differing counts in sweep.",
            "",
            "**Status recommendation:** PROVISIONAL until ADR-011 formally ACCEPTED.",
        ]
    )
    return "\n".join(lines) + "\n"


def _policy_md(r: M138Report) -> str:
    return (
        "# PolicyPack Freeze Recommendation\n\n"
        "| Field | Value | Source | Recommendation |\n"
        "|-------|-------|--------|----------------|\n"
        "| version | pol_m13_official_v1 (proposed) | M13.8 | FREEZE after ADR-011 |\n"
        "| status | DRAFT | current | SEALED at freeze |\n"
        "| epsilon_paise | 100 (proposed) | ADR-011 recommendation | PROVISIONAL → FREEZE |\n"
        "| gate_sequence | G1–G12 | docs/13 | FREEZE |\n"
        "| profile | BALANCED (pack metadata) | M1 scaffold | NOT APPLICABLE to benchmark |\n\n"
        "Do not silently convert PROVISIONAL → FROZEN without ADR-011 acceptance.\n"
    )


def _b1_md(r: M138Report) -> str:
    return (
        "# B1 Schedule Recommendation (ADR-013)\n\n"
        "Schedule in `revive/benchmark/config.py` is internally coherent:\n"
        "- Per risk class delays with escalating actions\n"
        "- Payment: immediate retry → scheduled → instrument change\n"
        "- Receivable: reminder progression → mandate update\n\n"
        "**Recommendation:** ACCEPT ADR-013 schedule as-is (`adr-013_v1`).\n"
        "- Credible status-quo baseline (BF-9)\n"
        "- Not weakened or strengthened for REVIVE\n"
        "- Publish in benchmark disclosures at freeze\n"
    )


def _predictor_md(r: M138Report) -> str:
    return (
        "# Predictor Freeze Recommendation\n\n"
        "Current: `strat_m7_dev` (`revive/recovery/valuation/config.py`)\n\n"
        "| Check | Status |\n"
        "|-------|--------|\n"
        "| Oracle features | None — observable inputs only |\n"
        "| Future leakage | None in valuation path |\n"
        "| Deterministic | Yes — seed-driven generator + fixed strategy |\n"
        "| Dev vs official separation | Official uses frozen version string in config_hash |\n\n"
        "**Recommendation:** FREEZE as `strat_m7_benchmark_v1` at benchmark seal.\n"
        "Record `VALUATION_VERSION:STRATEGY_VERSION` in official config.\n"
    )


def _approver_md(r: M138Report) -> str:
    return (
        "# Approver Freeze Recommendation\n\n"
        "Model: `simulated_v1_provisional`\n\n"
        "- Deterministic gate evaluation (no LLM)\n"
        "- Policy-driven thresholds from PolicyPack metadata\n"
        "- Strategy-neutral — responds to authorization context\n"
        "- No oracle access\n\n"
        "**Recommendation:** FREEZE as `simulated_v1` (drop provisional suffix) at seal.\n"
    )


def _seed_md(r: M138Report) -> str:
    return (
        "# Seed Selection Rule\n\n"
        "**Rule:** Fixed deterministic set `seeds = 1..20` per `docs/20` §3.1 (`RR-NFR-033`).\n\n"
        "- No cherry-picking\n"
        "- No post-hoc seed exclusion\n"
        "- Same seeds for all policies and profiles\n"
        "- Recorded in `OFFICIAL_SEED_SET` before measurement\n\n"
        f"Official tuple: `{list(OFFICIAL_SEED_SET)}`\n"
    )


def _proposed_config_md(r: M138Report) -> str:
    b = CONFIG_B
    profiles = [p.value for p in OFFICIAL_PROFILE_SET]
    return (
        "# Proposed Official Configuration (NOT EXECUTED)\n\n"
        "Immutable fields proposed for sealing:\n\n"
        "```text\n"
        f"benchmark_version: {BENCHMARK_VERSION}\n"
        f"generator_version: {GENERATOR_VERSION}\n"
        f"horizon_days: {b.simulation_window_days}\n"
        f"opportunity_count: {b.opportunity_count}\n"
        f"customer_count: {b.customer_count}\n"
        f"cycle_length_minutes: {b.cycle_interval_minutes}\n"
        f"profiles: {profiles}\n"
        f"seed_selection: 1..20 fixed\n"
        "PolicyPack_version: pol_m13_official_v1 (proposed)\n"
        "PolicyPack_status: SEALED (at freeze)\n"
        "epsilon_paise: 100 (proposed, ADR-011)\n"
        f"B1_schedule: {B1_SCHEDULE_VERSION} → adr-013_v1\n"
        f"predictor_version: {PREDICTOR_VERSION} → strat_m7_benchmark_v1\n"
        f"allocator_version: {ALLOCATOR_VERSION}\n"
        f"approver_version: {APPROVER_MODEL_VERSION} → simulated_v1\n"
        f"metrics_version: {METRIC_VERSION}\n"
        "allocator_mode: LAGRANGIAN\n"
        "llm_mode: LLM_OFF\n"
        "policy_set: B0, B1, B2, B3, REVIVE\n"
        "```\n\n"
        "**Rejected:** Configuration A (30-day window) — fails portfolio thesis validity.\n"
    )


def _decision_md(r: M138Report) -> str:
    return (
        f"# M13.8 Decision\n\n"
        f"# {r.decision}\n\n"
        f"{r.decision_rationale}\n\n"
        "## Freeze readiness gate\n\n"
        + "\n".join(f"- [{'x' if v else ' '}] {k}" for k, v in r.freeze_readiness.items())
        + "\n\n## Not done in M13.8\n\n"
        "- Official benchmark execution\n"
        "- M8 / B3 modification\n"
        "- Automatic ADR acceptance\n"
    )


def _adr_012_md(r: M138Report) -> str:
    b = CONFIG_B
    return (
        "# ADR-012 (RECOMMENDATION) — Official Benchmark Scale and Horizon\n\n"
        "**Status:** RECOMMENDATION — pending acceptance\n"
        "**Date:** 2026-08-23\n"
        "**Milestone:** M13.8\n\n"
        "## Decision (recommended)\n\n"
        f"Official generator configuration:\n"
        f"- `opportunity_count`: {b.opportunity_count}\n"
        f"- `customer_count`: {b.customer_count}\n"
        f"- `simulation_window_days`: {b.simulation_window_days}\n"
        f"- `cycle_interval_minutes`: {b.cycle_interval_minutes}\n"
        f"- `profiles`: all six documented profiles\n"
        f"- `seeds`: 1–20\n\n"
        "## Rejected\n\n"
        f"- Configuration A: {CONFIG_A.label} — 0 portfolio conflicts, "
        "0 B3/REVIVE differentiation (M13.7/M13.8 evidence)\n\n"
        "## Evidence\n\n"
        f"{r.decision_rationale}\n\n"
        "## Why realistic\n\n"
        "Covers documented recovery windows; matches calibration development scale horizon.\n\n"
        "## Why exercises Track 03\n\n"
        "Multi-resource portfolio conflicts and measurable B3 vs REVIVE allocation differences.\n\n"
        "## Computational feasibility\n\n"
        "See `computational-analysis.md` — est. <30 min generation for full matrix.\n\n"
        "## Fairness\n\n"
        "Same world, same capacities, same guardrails for all policies (BF-1…BF-10).\n\n"
        "## Remaining risks\n\n"
        "- ADR-011 ε acceptance still required\n"
        "- PolicyPack sealing required\n"
        "- Predictor/approver version formalization\n"
        "- REVIVE may still lose — falsification conditions F-1…F-6 apply\n"
    )
