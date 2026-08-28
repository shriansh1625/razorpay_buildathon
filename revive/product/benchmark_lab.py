"""Read-only Benchmark Lab. Never writes official artefacts.

Admissible product evidence is only:

    artefacts/benchmark/official-cloud-final/

Local sibling trees exist and MUST NOT be presented as official proof:

- artefacts/benchmark/official/ — 600 cells, structurally BENCHMARK_VALID,
  but INVALIDATED_BY_M13.17 (zero executions; all M-10 = 0)
- artefacts/benchmark/preflight-m13-19/ — PREFLIGHT_ONLY, not official evidence
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from revive.benchmark.official.config import (
    OFFICIAL_PROFILE_SET,
    OFFICIAL_SEED_SET,
    official_benchmark_config,
)
from revive.benchmark.official.hash import frozen_experiment_reference_hash
from revive.config.policy_pack import official_sealed_policy_pack

OFFICIAL_DIR = Path("artefacts/benchmark/official-cloud-final")
DECLARED_FROZEN_EXPERIMENT = (
    "cc8cad59779fd594f26599d5c8d7b965f774cff83a70eb44f9673e1e7556e4b0"
)
INVALIDATED_OFFICIAL = Path("artefacts/benchmark/official")
PREFLIGHT_DIR = Path("artefacts/benchmark/preflight-m13-19")

INADMISSIBLE_REASONS = {
    "official": (
        "INVALIDATED_BY_M13.17_EXECUTION_BRIDGE_DEFECT — "
        "600 cells retained, not admissible. All M-10 medians are 0. "
        "See implementation/m13-18-execution-bridge/prior-run-invalidated.md."
    ),
    "preflight-m13-19": "PREFLIGHT_ONLY — NOT BENCHMARK EVIDENCE.",
    "official-run2": "Incomplete / non-evidence cell dump.",
    "official-run3": "Incomplete / non-evidence cell dump.",
    "official-run4": "PARTIAL_NON_EVIDENCE.",
}

DECLARED_RUN = {
    "cells_completed": "600 / 600",
    "groups_completed": "120 / 120",
    "workers": 8,
    "mode": "OFFICIAL",
    "blocked": False,
    "validation": "BENCHMARK_VALID",
    "seeds": 20,
    "profiles": 6,
    "policies": 5,
    "cells": 600,
    "groups": 120,
    "policy_set": ["B0", "B1", "B2", "B3", "REVIVE"],
    "profile_set": [p.value for p in OFFICIAL_PROFILE_SET],
    "seed_set": list(OFFICIAL_SEED_SET),
    "frozen_experiment_reference": DECLARED_FROZEN_EXPERIMENT,
    "evidence_directory": str(OFFICIAL_DIR).replace("\\", "/"),
}


def _load_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def classify_artefact_tree(path: Path) -> str:
    """Admissibility label. Never treat the M13.17 tree as product proof."""
    name = path.name
    if name == "official-cloud-final":
        return "ADMISSIBLE_OFFICIAL" if path.is_dir() else "NOT_MOUNTED"
    if name == "preflight-m13-19":
        return "PREFLIGHT_ONLY"
    if name in INADMISSIBLE_REASONS:
        return "INADMISSIBLE"
    return "NON_EVIDENCE"


def workspace_artefact_scan(base: Path | None = None) -> list[dict[str, Any]]:
    root = base or Path("artefacts/benchmark")
    if not root.is_dir():
        return []
    rows: list[dict[str, Any]] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        status = classify_artefact_tree(child)
        rows.append(
            {
                "path": str(child).replace("\\", "/"),
                "name": child.name,
                "status": status,
                "reason": INADMISSIBLE_REASONS.get(child.name),
                "admissible_for_product_proof": status == "ADMISSIBLE_OFFICIAL",
            }
        )
    return rows


def benchmark_lab(root: Path | None = None) -> dict[str, Any]:
    """Frozen contract plus optional read-only artefact inspection."""
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    computed_ref = frozen_experiment_reference_hash(config)
    directory = root or OFFICIAL_DIR
    classification = classify_artefact_tree(directory)
    present = directory.is_dir()
    admissible = classification == "ADMISSIBLE_OFFICIAL" and present

    manifest = _load_json(directory / "manifest.json") if admissible else None
    aggregate = _load_json(directory / "aggregate.json") if admissible else None
    per_policy = _load_json(directory / "per_policy.json") if admissible else None

    artefact_status = "MOUNTED" if admissible else (
        "INADMISSIBLE_LOCAL_TREE" if present and not admissible else "NOT_MOUNTED_IN_THIS_WORKSPACE"
    )

    preflight_manifest = _load_json(PREFLIGHT_DIR / "manifest.json")
    preflight_hash = None
    if isinstance(preflight_manifest, dict):
        preflight_hash = preflight_manifest.get("frozen_experiment_reference_hash")

    from revive.product import official_evidence as oe
    from revive.product.benchmark_story import benchmark_story

    verification = oe.verify_evidence(directory) if admissible else None
    evidence_verified = verification.verified if verification else False
    official = oe.official_summary(directory) if evidence_verified else None
    story = benchmark_story()
    contract = (official or {}).get("contract") or oe.official_contract(directory)

    return {
        "headline": "Measured, not claimed.",
        "declared_official_run": DECLARED_RUN,
        "computed_frozen_experiment_reference": computed_ref,
        "declared_matches_computed": computed_ref == DECLARED_FROZEN_EXPERIMENT,
        "artefact_status": "VERIFIED" if evidence_verified else artefact_status,
        "evidence_status": verification.status if verification else "NOT_MOUNTED",
        "evidence_verified": evidence_verified,
        "verification": verification.to_dict() if verification else None,
        "artefact_classification": classification,
        "artefact_root": str(directory).replace("\\", "/"),
        "policy_pack_version": pack.version,
        "policy_pack_hash": pack.config_hash(),
        "internal_policy_id": "REVIVE",
        "manifest": manifest,
        "aggregate": aggregate if evidence_verified else None,
        "aggregate_present": aggregate is not None,
        "policy_summaries": per_policy if isinstance(per_policy, dict) and evidence_verified else None,
        "provenance": official.get("provenance") if official else None,
        # The run's own refutation attempts and its guardrail tally. Both are
        # cheap metadata reads, so they ride the first payload — a headline of
        # "measured, not claimed" that arrives before its own falsification
        # results would be a claim.
        "falsification": official.get("falsification") if official else None,
        "safety": official.get("safety") if official else None,
        # Per-profile M-10 split by policy. `aggregate.per_profile` pools all five
        # arms and four of them are exactly zero, so its mean is REVIVE's fifth.
        "profile_stats": official.get("profile_stats") if official else None,
        "reference_policy": oe.REFERENCE_POLICY,
        "intervening_baselines": list(oe.INTERVENING_BASELINES),
        "profile_policy_matrix": {
            "profiles": [p.value for p in OFFICIAL_PROFILE_SET],
            "policies": list(DECLARED_RUN["policy_set"]),
            "verified": evidence_verified,
            "matrix": {},
            "lazy_load": evidence_verified,
        },
        "workspace_scan": workspace_artefact_scan(),
        "preflight_frozen_hash_observed": preflight_hash,
        "preflight_hash_matches_declared": preflight_hash == DECLARED_FROZEN_EXPERIMENT,
        "integrity": {
            "official_directory_writable_by_product": False,
            "benchmark_semantics_unchanged": True,
            "never_use_invalidated_official_tree": True,
            "note": (
                "Productization never writes official-cloud-final. "
                "artefacts/benchmark/official/ is retained historical evidence of a "
                "failed integration run and is not shown as M-10 product proof."
            ),
        },
        "story": story,
        "contract": contract,
    }


__all__ = [
    "benchmark_lab",
    "classify_artefact_tree",
    "OFFICIAL_DIR",
    "DECLARED_FROZEN_EXPERIMENT",
    "INVALIDATED_OFFICIAL",
]
