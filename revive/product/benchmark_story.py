"""Official benchmark as a competition asset — methodology, journey, access.

This is documentation-as-data. Numbers below are taken from implementation
records and the frozen official contract. They are not a second copy of a
cell artefact and they are not a benchmark score.

The official experiment tree is read-only:

    artefacts/benchmark/official-cloud-final/

Never regenerate it. Never treat a sandbox run as a cell.
"""

from __future__ import annotations

from typing import Any

from revive.product.benchmark_lab import DECLARED_FROZEN_EXPERIMENT, DECLARED_RUN, OFFICIAL_DIR
from revive.simulation.profiles import PROFILE_PARAMETERS
from revive.simulation.types import GenerationProfile

EVIDENCE_PATH = str(OFFICIAL_DIR).replace("\\", "/")

# Official experiment used these five arms. docs/20 also specifies B4–B6;
# those arms are not part of the frozen 600-cell run.
OFFICIAL_POLICIES: tuple[dict[str, str], ...] = (
    {
        "id": "B0",
        "baseline": "NO_ACTION",
        "behaviour": "Never acts.",
        "isolates": "The natural recovery floor. Any recovery above this is the only recovery an intervening policy can claim credit for.",
        "source": "docs/20-benchmark.md § 2",
    },
    {
        "id": "B1",
        "baseline": "FIXED_RETRY",
        "behaviour": "Fixed retry schedule per class, no targeting.",
        "isolates": "Retry logic without allocation.",
        "source": "docs/20-benchmark.md § 2",
    },
    {
        "id": "B2",
        "baseline": "CONTACT_ALL",
        "behaviour": "Acts on every eligible opportunity until capacity runs out, arbitrary order.",
        "isolates": "Effort without prioritisation.",
        "source": "docs/20-benchmark.md § 2",
    },
    {
        "id": "B3",
        "baseline": "GREEDY_ENRV",
        "behaviour": "Ranks by raw ENRV, ignores resource density.",
        "isolates": "Scoring without constrained allocation.",
        "source": "docs/20-benchmark.md § 2",
    },
    {
        "id": "REVIVE",
        "baseline": "PAYVANTA recovery policy",
        "behaviour": "Allocator + gates. Internal technical policy identifier — not the product name.",
        "isolates": "The engine under test.",
        "source": "docs/20-benchmark.md; official PolicyPack pol_m13_official_v1",
    },
)

M10 = {
    "id": "M-10",
    "name": "Incremental Net Recovered Revenue",
    "user_facing": "INCREMENTAL NET RECOVERY",
    "definition": (
        "M-10(policy, seed) = NetRecovered(policy, seed) − NetRecovered(B0_NO_ACTION, seed). "
        "Paired comparison against do-nothing on the same seed and profile."
    ),
    "unit": "paise",
    "tier": "1 · Primary judging metric",
    "can_be_negative": True,
    "source": "docs/21-evaluation.md § 2.1; docs/37-metrics-dictionary.md",
    "does_not_mean": (
        "Not the Control Room sandbox incremental net. Not a guarantee of production recovery. "
        "Not a claim of superiority over every possible policy."
    ),
}

WHY_DESIGN = {
    "seeds": {
        "count": 20,
        "why": (
            "Deterministic variation with repeatability. Each seed is a frozen world: "
            "same seed, same population, same oracle. Twenty seeds show the engine across "
            "independent draws rather than one selected scenario. They are not a statistical "
            "sample of real merchants."
        ),
    },
    "profiles": {
        "count": 6,
        "why": (
            "Different operating environments. Capacity, natural recovery, adversarial "
            "injection, and degradation change what a competent policy looks like. "
            "Reporting every profile — including ABUNDANT, where allocator advantage is "
            "expected to shrink — is required so a single flattering regime is not the story."
        ),
        "source": "docs/19-synthetic-dataset.md § 2.3",
    },
    "policies": {
        "count": 5,
        "ids": ["B0", "B1", "B2", "B3", "REVIVE"],
        "why": (
            "Comparative policy evaluation on identical inputs. B0 is the do-nothing floor. "
            "B1–B3 isolate retry, untargeted contact, and greedy scoring. REVIVE is PAYVANTA’s "
            "recovery policy identifier. The official run evaluated these five arms, not B4–B6."
        ),
        "source": "artefacts/benchmark/official-cloud-final/ + docs/20-benchmark.md § 2",
    },
    "cells": {
        "count": 600,
        "formula": "20 seeds × 6 profiles × 5 policies",
        "why": (
            "Systematic coverage: every seed × profile × policy combination, once. "
            "A cell is one controlled evaluation, not a demonstration. Six hundred cells "
            "are the experiment design, not a proof of superiority."
        ),
    },
    "groups": {
        "count": 120,
        "formula": "20 seeds × 6 profiles",
        "why": "Each group is one world (seed × profile) evaluated under all five policies.",
    },
    "workers": {
        "count": 8,
        "why": "Official cloud run dispatched eight parallel workers after M13.24 made dispatch real.",
    },
}

# Development / cloud validation — NOT official M-10 scores.
ENGINEERING: tuple[dict[str, Any], ...] = (
    {
        "id": "M13.24",
        "title": "Parallel worker dispatch",
        "kind": "DEBUGGING",
        "docs": [
            "implementation/m13-24-stress-worker-dispatch/root-cause.md",
            "implementation/m13-24-stress-worker-dispatch/dispatch-fix.md",
            "implementation/m13-24-stress-worker-dispatch/determinism.md",
            "implementation/m13-24-stress-worker-dispatch/performance.md",
        ],
        "tests": [
            "tests/benchmark/test_m13_24_stress_worker_dispatch.py::test_stress_cells_worker_fingerprints_identical",
        ],
        "problem": (
            "CLI parsed --workers 8, but the stress branch of execute_benchmark called "
            "run_stress_benchmark without forwarding workers. run_cell_benchmark defaulted "
            "to workers=1. Requested workers=8 ran sequentially. Metadata recorded workers=1."
        ),
        "fix": (
            "Stress benchmark now forwards workers, stop_after_cell, and benchmark_mode into "
            "the existing cell runner. Official mode was unchanged (no stress_cells)."
        ),
        "measured": {
            "label": "Development stress, 10 cells (2 groups × 5 policies). Not official evidence.",
            "workers": [
                {"workers": 1, "wall_seconds": 72.336, "dispatch": "sequential"},
                {"workers": 2, "wall_seconds": 39.788, "dispatch": "parallel workers=2"},
                {"workers": 8, "wall_seconds": 31.689, "dispatch": "parallel workers=8"},
            ],
            "fingerprints": (
                "workers=1, workers=2, and workers=8: identical aggregate fingerprint and "
                "per-cell metrics_checksum vs workers=1. Parallel dispatch became real. "
                "Extra workers beyond two groups cannot run extra groups on this stress "
                "workload — do not read the wall drop as an 8× speedup."
            ),
        },
        "classification": "DEVELOPMENT_ONLY — NOT OFFICIAL BENCHMARK EVIDENCE",
    },
    {
        "id": "M13.25",
        "title": "Checkpoint / resume repair",
        "kind": "REPAIR",
        "docs": [
            "implementation/m13-25-checkpoint-repair/root-cause.md",
            "implementation/m13-25-checkpoint-repair/reconciliation-design.md",
        ],
        "tests": [
            "tests/benchmark/test_m13_25_checkpoint_resume.py::test_reconcile_files_ahead_of_manifest",
            "tests/benchmark/test_m13_25_checkpoint_resume.py::test_reconcile_manifest_ahead_of_files",
            "tests/benchmark/test_m13_25_checkpoint_resume.py::test_corrupt_cell_is_recomputed",
            "tests/benchmark/test_m13_25_checkpoint_resume.py::test_partial_group_four_of_five_resume",
            "tests/benchmark/test_m13_25_checkpoint_resume.py::test_production_failure_shape_resume",
            "tests/benchmark/test_m13_25_checkpoint_resume.py::test_interruption_then_resume_parallel",
        ],
        "problem": (
            "Parallel workers persisted cells atomically, but the parent advanced the checkpoint "
            "manifest only after a complete 5-policy group verified. Failure shape: 4/5 cell files "
            "existed (missing seed-001/ABUNDANT/REVIVE.json) while the manifest still said 26/30. "
            "Resume appeared hung because operators trusted a stale count."
        ),
        "fix": (
            "Startup reconciliation, manifest synchronization from file truth, drift detection "
            "(files-ahead / manifest-ahead), and parent-owned checkpoint updates after each "
            "verified group."
        ),
        "measured": {
            "label": "Regression tests on the production-shaped interruption.",
            "cases": [
                "files-ahead of manifest",
                "manifest-ahead of files",
                "corrupt cell recomputed",
                "partial group (4 of 5) resume",
                "production-shaped interruption resume",
                "parallel interruption then resume",
            ],
        },
        "classification": "INFRASTRUCTURE REPAIR — NOT A SCORE CHANGE",
    },
    {
        "id": "M13.26",
        "title": "ABUNDANT × REVIVE forensic profiling",
        "kind": "PROFILING",
        "docs": [
            "implementation/m13-26-abundant-revive-forensics/root-cause.md",
            "implementation/m13-26-abundant-revive-forensics/m8-allocation.md",
            "implementation/checkpoints/M13.26-abundant-revive-forensics.md",
        ],
        "problem": (
            "ABUNDANT × REVIVE was much slower than other profiles. This was not a hang: "
            "CPU stayed near 100% in active compute. ABUNDANT capacity_scarcity_factor=0.2 "
            "(~5× resource headroom) produced many more executions and Lagrangian selections."
        ),
        "fix": (
            "Forensic classification, not a silent timeout. Ruled out opportunity-count, "
            "candidate-count, pathological loops, and persistence as the primary cause. "
            "Confirmed M6/M7/M8 — especially the M8 Lagrangian hot path."
        ),
        "measured": {
            "label": "DEVELOPMENT_FORENSIC_ONLY — NOT OFFICIAL BENCHMARK EVIDENCE. seed=1, 2016 cycles, wall_seconds.",
            "cell_wall_seconds": {
                "BALANCED": 555.1,
                "SCARCE": 486.5,
                "HOSTILE": 539.7,
                "ABUNDANT": 1363.0,
            },
            "abundant_vs_balanced": "2.46× wall",
            "executions": {"BALANCED": 102_365, "ABUNDANT": 339_890, "ratio": "3.32×"},
            "stages_seconds": {
                "M6": {"BALANCED": 136, "ABUNDANT": 271},
                "M7": {"BALANCED": 168, "ABUNDANT": 309},
                "M8": {"BALANCED": 78, "ABUNDANT": 289, "ratio": "3.68×"},
            },
            "m8_hot_path": (
                "cProfile: lagrangian_allocate 264s; _best_action_eligible ~28M calls. "
                "~340k executions on ABUNDANT."
            ),
        },
        "classification": "DEVELOPMENT_FORENSIC_ONLY — NOT OFFICIAL BENCHMARK EVIDENCE",
    },
    {
        "id": "M13.27",
        "title": "Metrics-tail rescue",
        "kind": "OPTIMIZATION",
        "docs": [
            "implementation/m13-27-metrics-tail-rescue/root-cause.md",
            "implementation/m13-27-metrics-tail-rescue/performance.md",
            "implementation/m13-27-metrics-tail-rescue/cloud-validation.md",
            "implementation/m13-27-metrics-tail-rescue/M13.27-decision.md",
        ],
        "problem": (
            "compute_policy_metrics counted unauthorized executions with an "
            "O(authorization × execution) cross-scan. At ABUNDANT scale (~404k authorizations, "
            "~340k executions) this produced a massive CPU tail after cycles had already finished."
        ),
        "fix": (
            "Indexed unauthorized-execution accounting and collapsed repeated passes over "
            "executions and measurements. Metric semantics unchanged; checksums bit-identical "
            "to the pre-optimization equivalence baseline."
        ),
        "measured": {
            "label": "PERFORMANCE / RELIABILITY ENGINEERING. Not a benchmark score improvement.",
            "old_unauthorized_cross_scan_seconds": 4137.6,
            "new_compute_policy_metrics_local_seconds": 0.321,
            "cloud_metrics_tail_seconds": 0.39,
            "pre_optimization_cloud_cell_seconds": 9900,
            "post_optimization_cloud_cell_seconds": 627.3,
        },
        "classification": "PERFORMANCE VALIDATION — NOT A BENCHMARK SCORE",
    },
    {
        "id": "CLOUD",
        "title": "Cloud validation (seed=1 ABUNDANT REVIVE)",
        "kind": "VALIDATION",
        "docs": ["implementation/m13-27-metrics-tail-rescue/cloud-validation.md"],
        "problem": "Confirm the metrics-tail rescue on the production cell path before the official experiment.",
        "fix": "Single-cell production-equivalent gate on the cloud runner. Official 600-cell run was not part of this milestone.",
        "measured": {
            "label": "Cloud validation cell. Not the official 600-cell experiment.",
            "seed": 1,
            "profile": "ABUNDANT",
            "policy": "REVIVE",
            "cycles": 2016,
            "total_cell_seconds": 627.3,
            "metrics_tail_seconds": 0.39,
            "peak_rss_mb": 594,
            "executions": 339_890,
            "authorizations": 404_319,
            "measurements": 339_890,
            "metrics_checksum": "80c238eb91edc64424079d2b9bac4f354886fac4089cf96668b493f8245113da",
            "run_valid": True,
            "policy_violations": 0,
            "unauthorized_executions": 0,
        },
        "classification": "CLOUD VALIDATION — NOT OFFICIAL 600-CELL EVIDENCE",
    },
    {
        "id": "OFFICIAL",
        "title": "Official 600-cell evaluation",
        "kind": "EVIDENCE",
        "docs": [
            "artefacts/benchmark/official-cloud-final/manifest.json",
            "artefacts/benchmark/official-cloud-final/validation.json",
        ],
        "problem": "Evaluate the engine under a frozen controlled experiment — not one sandbox scenario.",
        "fix": "Run the declared 20 × 6 × 5 design. Freeze the tree. Keep it read-only.",
        "measured": {
            "label": "The completed official experiment.",
            "cells": 600,
            "groups": 120,
            "seeds": 20,
            "profiles": 6,
            "policies": 5,
            "workers": 8,
            "validation": "BENCHMARK_VALID",
            "blocked": False,
            "frozen_experiment_hash": DECLARED_FROZEN_EXPERIMENT,
        },
        "classification": "OFFICIAL EVIDENCE — READ-ONLY",
    },
)

SANDBOX_VS_OFFICIAL = {
    "sandbox": {
        "name": "PAYVANTA Sandbox",
        "does": "Demonstrates the working recovery workflow on a synthetic test population with bounded local execution.",
        "is_not": "An official benchmark cell. Control Room money is this session, not M-10 of the experiment.",
    },
    "official": {
        "name": "Official benchmark",
        "does": "Evaluates the same engine under a frozen controlled experiment (20 × 6 × 5 = 600 cells).",
        "is_not": "The product itself. It is the experimental proof and engineering validation layer around the product.",
    },
    "relationship": (
        "This is the engine you just saw operating. That engine was evaluated separately "
        "across 600 official cells."
    ),
}

LIMITATIONS = (
    {
        "id": "sandbox_vs_production",
        "title": "Sandbox is not production",
        "text": (
            "The Control Room runs a synthetic population with simulated adapters. "
            "It is not a live merchant integration and not an official cell."
        ),
    },
    {
        "id": "synthetic_population",
        "title": "Synthetic population",
        "text": (
            "Profiles and oracles are generated. They are designed to be adversarial and "
            "internally coherent. They are not derived from Razorpay production traffic."
        ),
    },
    {
        "id": "benchmark_scope",
        "title": "Benchmark scope",
        "text": (
            "The official experiment evaluates five policies on six synthetic profiles and "
            "twenty deterministic seeds. It does not evaluate every possible policy, profile, "
            "or real-world cohort."
        ),
    },
    {
        "id": "m10_measures",
        "title": "What M-10 measures",
        "text": (
            "Incremental net recovery versus B0 on the same seed and profile. It can be "
            "negative. It does not measure gross recovered, messages sent, or production ROI."
        ),
    },
    {
        "id": "does_not_prove",
        "title": "What the benchmark does not prove",
        "text": (
            "It does not prove superiority in production, guaranteed recovery, scientific "
            "certainty, or that PAYVANTA will recover any particular merchant’s revenue. "
            "It shows what was evaluated and measured under the frozen contract."
        ),
    },
    {
        "id": "integrations",
        "title": "Production integrations",
        "text": (
            "Live Razorpay rails, merchant accounts, and production credentials are not "
            "part of this submission. Adapters in the sandbox and the official experiment "
            "are simulated."
        ),
    },
)

CLAIMS: tuple[dict[str, str], ...] = (
    {
        "claim": "600 official cells",
        "source": "artefacts/benchmark/official-cloud-final/ (manifest + cells/)",
        "test": "tests/product/test_official_evidence.py::TestOfficialCloudFinal::test_verify_evidence_passes",
        "ui": "#/benchmark",
        "api": "GET /api/benchmark/official/contract",
    },
    {
        "claim": "20 × 6 × 5 design",
        "source": "Declared contract + cell matrix completeness check",
        "test": "tests/product/test_official_evidence.py::TestOfficialCloudFinal::test_official_matrix_complete",
        "ui": "#/benchmark/matrix",
        "api": "GET /api/benchmark/official/matrix",
    },
    {
        "claim": "120 groups",
        "source": "20 seeds × 6 profiles; declared_official_run.groups",
        "test": "tests/product/test_overview.py::test_overview_matches_sandbox_snapshot",
        "ui": "#/benchmark",
        "api": "GET /api/product/overview → official_benchmark.group_count",
    },
    {
        "claim": "BENCHMARK_VALID · blocked=false",
        "source": "artefacts/benchmark/official-cloud-final/validation.json + manifest.json",
        "test": "tests/product/test_official_evidence.py::TestOfficialCloudFinal::test_summary_provenance_fields",
        "ui": "#/benchmark/evidence",
        "api": "GET /api/benchmark/official/summary",
    },
    {
        "claim": "M-10 incremental net recovery",
        "source": "per_policy.json + per-cell artefacts paired against B0",
        "test": "tests/product/test_official_evidence.py::TestOfficialCloudFinal::test_cell_lookup_abundant_revive_seed_14",
        "ui": "#/benchmark/matrix (ABUNDANT × REVIVE × seed 14)",
        "api": "GET /api/benchmark/official/cell/14/ABUNDANT/REVIVE",
    },
    {
        "claim": "Frozen experiment hash",
        "source": "manifest.frozen_experiment_reference_hash",
        "test": "tests/product/test_official_evidence.py::TestOfficialCloudFinal::test_verify_evidence_passes",
        "ui": "#/benchmark/evidence",
        "api": "GET /api/benchmark/official/contract → frozen_experiment_hash",
    },
    {
        "claim": "Sandbox is not a cell",
        "source": "ProductSession / Control Room snapshot",
        "test": "tests/product/test_overview.py::test_overview_matches_sandbox_snapshot",
        "ui": "#/control · #/system",
        "api": "GET /api/product/overview → integrity.sandbox_is_not_official_evidence",
    },
)

DISCOVERABILITY = {
    "methodology": [
        "README.md § Measured, Not Claimed",
        "docs/42-official-benchmark.md",
        "docs/20-benchmark.md",
        "docs/21-evaluation.md",
        "GET /api/benchmark/story",
        "#/benchmark",
    ],
    "artefact_location": [
        EVIDENCE_PATH,
        "GET /api/benchmark/official/contract → evidence_path",
        "#/benchmark/evidence",
    ],
    "validation": [
        f"{EVIDENCE_PATH}/validation.json",
        "GET /api/benchmark/official/summary",
        "#/benchmark/evidence",
    ],
    "config_hash": [
        f"{EVIDENCE_PATH}/manifest.json",
        "GET /api/benchmark/official/contract → config_hash",
    ],
    "policy_pack": [
        "revive.config.policy_pack.official_sealed_policy_pack",
        "GET /api/benchmark/official/contract → policy_pack",
        "#/benchmark/evidence",
    ],
    "cell_matrix": [
        "GET /api/benchmark/official/matrix",
        "#/benchmark/matrix",
    ],
    "m10_definition": [
        "docs/21-evaluation.md § 2.1",
        "docs/37-metrics-dictionary.md",
        "GET /api/benchmark/story → m10",
    ],
    "engineering_timeline": [
        "README.md § How We Got Here",
        "docs/42-official-benchmark.md",
        "GET /api/benchmark/story → engineering",
        "#/benchmark",
    ],
}

PITCH_SEGMENT = {
    "duration_seconds": "40–50",
    "window": "04:10–05:00 of the 5-minute pitch",
    "beats": [
        {"t": "04:10", "line": "Now let’s see whether this is just one carefully selected scenario."},
        {"t": "04:15", "line": "20 seeds × 6 profiles × 5 policies."},
        {"t": "04:20", "line": "600 official cells."},
        {"t": "04:25", "line": "120 groups."},
        {"t": "04:30", "line": "Open the profile × policy matrix."},
        {"t": "04:35", "line": "ABUNDANT × REVIVE."},
        {"t": "04:40", "line": "Seed 14."},
        {"t": "04:45", "line": "Cell evidence + checksum."},
        {"t": "04:50", "line": "Same engine. Measured across the experiment."},
        {"t": "05:00", "line": "MEASURED. NOT CLAIMED."},
    ],
}

ACCESS = {
    "path": EVIDENCE_PATH,
    "git_tracked": False,
    "gitignore_rule": "artefacts/",
    "writable_by_product": False,
    "how_to_supply": (
        "The official cell JSON tree is gitignored with the rest of artefacts/. "
        "A fresh clone still contains the methodology, the declared 20×6×5 contract, "
        "the engineering records under implementation/m13-24…m13-27, the tests, and "
        "this machine-readable story. To verify the frozen run, mount the official "
        "cloud-final tree at artefacts/benchmark/official-cloud-final/ without modifying it. "
        "Do not rerun the official benchmark into that directory."
    ),
    "when_absent": (
        "Benchmark Lab and GET /api/benchmark still expose the declared contract and "
        "this story. Cell counts and M-10 figures are reported only after verification."
    ),
    "when_present": (
        "verify_evidence must report 600 cells, BENCHMARK_VALID, blocked=false, and "
        "matching frozen experiment hash before the product treats the tree as official evidence."
    ),
}

DIFFERENTIATOR = (
    "We didn’t stop at a working demo. We built the infrastructure to stress, "
    "profile, repair, optimize, validate, and finally evaluate the engine across "
    "600 official experiment cells."
)

JUDGE_QA = (
    {
        "q": "What makes this different from an ordinary demo?",
        "a": "One run demonstrates the system. 600 official cells evaluate the engine.",
    },
    {
        "q": "What did you actually improve?",
        "a": "Parallelism, checkpoint reliability, ABUNDANT performance forensics, metrics aggregation, cloud validation.",
    },
    {
        "q": "Can I inspect one result?",
        "a": "Yes. ABUNDANT × REVIVE × seed 14 — artefact, metrics, checksum, validation.",
    },
)


def _profiles() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in GenerationProfile:
        params = PROFILE_PARAMETERS[profile]
        rows.append(
            {
                "id": profile.value,
                "description": params.description,
                "capacity_scarcity_factor": params.capacity_scarcity_factor,
                "natural_recovery_multiplier": params.natural_recovery_multiplier,
                "adversarial_injection": params.adversarial_injection,
                "degradation_intensity": params.degradation_intensity,
                "source": "revive/simulation/profiles.py (docs/19-synthetic-dataset.md § 2.3)",
            }
        )
    return rows


def benchmark_story() -> dict[str, Any]:
    """Always available — does not require the official evidence tree."""
    run = dict(DECLARED_RUN)
    return {
        "product": "PAYVANTA",
        "internal_policy_id": "REVIVE",
        "role": (
            "The experimental proof and engineering validation layer around the product. "
            "The benchmark is not the product itself."
        ),
        "north_star": (
            "We built it. We stressed it. We found the bottlenecks. We repaired them. "
            "We measured the optimizations. We validated them in cloud. Then we ran the "
            "official experiment. 600 cells. 120 groups. 20 seeds. 6 profiles. 5 policies. "
            "And we kept the evidence read-only."
        ),
        "vocabulary": ["evaluated", "measured", "validated", "observed", "verified"],
        "do_not_claim": [
            "600 cells prove superiority",
            "scientifically proven",
            "production proven",
            "guaranteed recovery",
        ],
        "declared_run": {
            "seeds": run["seeds"],
            "profiles": run["profiles"],
            "policies": run["policies"],
            "cells": run["cells"],
            "groups": run["groups"],
            "workers": run["workers"],
            "validation": run["validation"],
            "blocked": run["blocked"],
            "mode": run["mode"],
            "policy_set": list(run["policy_set"]),
            "profile_set": list(run["profile_set"]),
            "frozen_experiment_hash": run["frozen_experiment_reference"],
            "evidence_path": EVIDENCE_PATH,
        },
        "why": WHY_DESIGN,
        "profiles": _profiles(),
        "policies": [dict(p) for p in OFFICIAL_POLICIES],
        "m10": dict(M10),
        "sandbox_vs_official": SANDBOX_VS_OFFICIAL,
        "engineering": [dict(step) for step in ENGINEERING],
        "limitations": [dict(row) for row in LIMITATIONS],
        "claims": [dict(row) for row in CLAIMS],
        "discoverability": DISCOVERABILITY,
        "pitch_segment": PITCH_SEGMENT,
        "access": ACCESS,
        "differentiator": DIFFERENTIATOR,
        "judge_qa": [dict(row) for row in JUDGE_QA],
        "reference_cell": {
            "seed": 14,
            "profile": "ABUNDANT",
            "policy": "REVIVE",
            "ui": "#/benchmark/matrix",
            "api": "/api/benchmark/official/cell/14/ABUNDANT/REVIVE",
        },
    }


__all__ = ["benchmark_story", "EVIDENCE_PATH", "M10"]
