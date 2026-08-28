"""Read-only official benchmark evidence — artefacts/benchmark/official-cloud-final/.

Never writes to the evidence tree. Never reruns the benchmark.
"""

from __future__ import annotations

import json
import re
import statistics
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from revive.benchmark.official.config import OFFICIAL_PROFILE_SET, OFFICIAL_SEED_SET
from revive.benchmark.official.hash import frozen_experiment_reference_hash
from revive.benchmark.official.config import official_benchmark_config
from revive.config.policy_pack import official_sealed_policy_pack
from revive.product.benchmark_lab import (
    DECLARED_FROZEN_EXPERIMENT,
    DECLARED_RUN,
    INADMISSIBLE_REASONS,
    OFFICIAL_DIR,
    classify_artefact_tree,
)
from revive.product.money import format_display_inr, format_inr, paise_to_inr

POLICIES: tuple[str, ...] = ("B0", "B1", "B2", "B3", "REVIVE")
PROFILES: tuple[str, ...] = tuple(p.value for p in OFFICIAL_PROFILE_SET)
SEEDS: tuple[int, ...] = tuple(OFFICIAL_SEED_SET)
POLICY_CELL_NAMES = frozenset(f"{p}.json" for p in POLICIES)

#: The arm the primary metric is paired against. M-10 is defined as
#: NetRecovered(policy) − NetRecovered(B0), so B0 is not merely one more column:
#: it is the zero of the axis. Anything said about "the baselines" has to keep
#: B0 separate from the intervening baselines, which behave nothing like it.
REFERENCE_POLICY = "B0"
INTERVENING_BASELINES: tuple[str, ...] = ("B1", "B2", "B3")

_CACHE: dict[str, Any] | None = None
_INDEX_LOCK = threading.Lock()


def _load_json(path: Path) -> Any | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _money(paise: int | None) -> dict[str, Any] | None:
    if paise is None:
        return None
    return {
        "paise": paise,
        "inr": paise_to_inr(paise),
        "display": format_inr(paise),
        "read": format_display_inr(paise),
    }


def _cell_path(root: Path, seed: int, profile: str, policy: str) -> Path:
    return root / "cells" / f"seed-{seed:03d}" / profile / f"{policy}.json"


def validate_cell_params(seed: int, profile: str, policy: str) -> None:
    if seed not in SEEDS:
        raise ValueError("invalid seed")
    if profile not in PROFILES:
        raise ValueError("invalid profile")
    if policy not in POLICIES:
        raise ValueError("invalid policy")


@dataclass
class VerificationReport:
    status: str
    verified: bool
    checks: dict[str, bool] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)
    cell_count: int = 0
    expected_cells: int = 600

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "verified": self.verified,
            "checks": self.checks,
            "failures": self.failures,
            "cell_count": self.cell_count,
            "expected_cells": self.expected_cells,
        }


def verify_evidence(root: Path | None = None) -> VerificationReport:
    """Application-level official evidence verification."""
    directory = root or OFFICIAL_DIR
    report = VerificationReport(status="OFFICIAL_EVIDENCE_UNVERIFIED", verified=False)
    if not directory.is_dir():
        report.failures.append("official-cloud-final directory not present")
        return report

    if classify_artefact_tree(directory) != "ADMISSIBLE_OFFICIAL":
        report.failures.append(f"tree classification: {classify_artefact_tree(directory)}")
        return report

    cell_files = [
        p
        for p in (directory / "cells").rglob("*.json")
        if p.name in POLICY_CELL_NAMES
    ]
    report.cell_count = len(cell_files)
    report.checks["cell_count_600"] = report.cell_count == 600

    seen: set[tuple[int, str, str]] = set()
    missing: list[tuple[int, str, str]] = []
    for seed in SEEDS:
        for profile in PROFILES:
            for policy in POLICIES:
                key = (seed, profile, policy)
                path = _cell_path(directory, seed, profile, policy)
                if path.is_file():
                    if key in seen:
                        report.failures.append(f"duplicate cell {key}")
                    seen.add(key)
                else:
                    missing.append(key)
    report.checks["matrix_complete"] = len(missing) == 0 and len(seen) == 600
    if missing:
        report.failures.append(f"missing {len(missing)} expected cells")

    manifest = _load_json(directory / "manifest.json")
    validation = _load_json(directory / "validation.json")
    freeze_check = _load_json(directory / "freeze_check.json")
    config = _load_json(directory / "config.json")
    config_hash_file = (
        directory / "config_hash.txt"
    ).read_text(encoding="utf-8").strip() if (directory / "config_hash.txt").is_file() else None

    pack = official_sealed_policy_pack()
    computed_frozen = frozen_experiment_reference_hash(official_benchmark_config(policy_pack=pack))

    frozen_ok = (
        isinstance(manifest, dict)
        and manifest.get("frozen_experiment_reference_hash") == DECLARED_FROZEN_EXPERIMENT
        and computed_frozen == DECLARED_FROZEN_EXPERIMENT
    )
    report.checks["frozen_experiment_hash"] = frozen_ok
    if not frozen_ok:
        report.failures.append("frozen experiment reference mismatch")

    config_hash_ok = (
        isinstance(manifest, dict)
        and config_hash_file is not None
        and config_hash_file == manifest.get("config_hash")
    )
    report.checks["config_hash"] = config_hash_ok
    if not config_hash_ok:
        report.failures.append("config hash mismatch")

    validation_ok = (
        isinstance(validation, dict)
        and validation.get("valid") is True
        and validation.get("status") == "BENCHMARK_VALID"
    )
    report.checks["validation"] = validation_ok
    if not validation_ok:
        report.failures.append("validation.json not BENCHMARK_VALID")

    freeze_ok = isinstance(freeze_check, dict) and freeze_check.get("complete") is True
    report.checks["freeze_check"] = freeze_ok

    pack_ok = (
        isinstance(config, dict)
        and config.get("PolicyPack_version") == pack.version
        and config.get("PolicyPack_hash") == pack.config_hash()
    )
    report.checks["policy_pack"] = pack_ok
    if not pack_ok:
        report.failures.append("policy pack metadata mismatch")

    report.verified = all(report.checks.values()) and not report.failures
    report.status = (
        "OFFICIAL_EVIDENCE_VERIFIED" if report.verified else "OFFICIAL_EVIDENCE_UNVERIFIED"
    )
    return report


def _b0_lookup(root: Path) -> dict[tuple[int, str], int]:
    lookup: dict[tuple[int, str], int] = {}
    for seed in SEEDS:
        for profile in PROFILES:
            data = _load_json(_cell_path(root, seed, profile, "B0"))
            if isinstance(data, dict):
                lookup[(seed, profile)] = int(data.get("metrics", {}).get("net_recovered_paise", 0))
    return lookup


def m10_from_cell(metrics: dict[str, Any], b0_net: int) -> int:
    stored = metrics.get("M-10_incremental_net_paise")
    if stored is not None:
        return int(stored)
    return int(metrics.get("net_recovered_paise", 0)) - b0_net


def _build_index(root: Path) -> dict[str, Any]:
    """The one full pass over the 600 cells. Everything cell-derived rides on it.

    §57's rule is that the Lab must not read 600 files at startup — not that it
    can never read them. So this stays behind ``build_index=True``, and anything
    that needs per-cell truth is accumulated here rather than opening the tree a
    second time.
    """
    b0 = _b0_lookup(root)
    matrix: dict[str, dict[str, Any]] = {}
    index: list[dict[str, Any]] = []
    effort: dict[str, dict[str, int]] = {
        policy: {
            "cells": 0,
            "interventions": 0,
            "gross": 0,
            "net": 0,
            "cost": 0,
            "natural": 0,
            "failures": 0,
            "cells_with_recovery": 0,
        }
        for policy in POLICIES
    }

    for profile in PROFILES:
        matrix[profile] = {}
        for policy in POLICIES:
            m10_vals: list[int] = []
            valid = 0
            for seed in SEEDS:
                data = _load_json(_cell_path(root, seed, profile, policy))
                if not isinstance(data, dict):
                    continue
                metrics = data.get("metrics", {})
                m10 = m10_from_cell(metrics, b0.get((seed, profile), 0))
                m10_vals.append(m10)
                if metrics.get("run_valid", True):
                    valid += 1
                net = int(metrics.get("net_recovered_paise") or 0)
                acc = effort[policy]
                acc["cells"] += 1
                acc["interventions"] += int(metrics.get("intervention_count") or 0)
                acc["gross"] += int(metrics.get("gross_recovered_paise") or 0)
                acc["net"] += net
                acc["cost"] += int(metrics.get("realized_cost_paise") or 0)
                acc["natural"] += int(metrics.get("natural_recovered_paise") or 0)
                acc["failures"] += int(metrics.get("execution_failures") or 0)
                if net != 0:
                    acc["cells_with_recovery"] += 1
                index.append(
                    {
                        "seed": seed,
                        "profile": profile,
                        "policy": policy,
                        "cell_index": data.get("cell_index"),
                        "m10_paise": m10,
                        "run_valid": bool(metrics.get("run_valid", True)),
                        "recovery_rate": metrics.get("recovery_rate"),
                        "net_recovered_paise": metrics.get("net_recovered_paise"),
                    }
                )
            matrix[profile][policy] = {
                "seed_count": len(m10_vals),
                "valid_count": valid,
                "m10_median_paise": statistics.median(m10_vals) if m10_vals else None,
                "m10_mean_paise": statistics.mean(m10_vals) if m10_vals else None,
                "m10_median": _money(int(statistics.median(m10_vals)) if m10_vals else None),
                "status": "valid" if valid == 20 else "partial",
            }

    return {
        "matrix": matrix,
        "search_index": index,
        "b0_lookup": b0,
        "policy_behaviour": _policy_behaviour_rows(effort),
    }


def _policy_behaviour_rows(effort: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    """What each arm actually did, as opposed to what it scored.

    `per_policy.json` reports M-10 and nothing about effort, so an arm that spent
    millions of interventions and recovered nothing is indistinguishable there
    from B0, which spent none. That difference is the entire reason the policy
    comparison needs a caveat instead of a victory lap, so it is measured from
    the cells rather than asserted.
    """
    rows: list[dict[str, Any]] = []
    for policy in POLICIES:
        acc = effort.get(policy) or {}
        if not acc.get("cells"):
            continue
        interventions = acc["interventions"]
        net = acc["net"]
        rows.append(
            {
                "policy": policy,
                "cells": acc["cells"],
                "interventions": interventions,
                "execution_failures": acc["failures"],
                "cells_with_recovery": acc["cells_with_recovery"],
                "gross_recovered": _money(acc["gross"]),
                "net_recovered": _money(acc["net"]),
                "realized_cost": _money(acc["cost"]),
                "natural_recovered": _money(acc["natural"]),
                "is_reference": policy == REFERENCE_POLICY,
                # An arm that acted and recovered nothing is a different object
                # from an arm that never acted. Named here so no surface has to
                # infer the distinction from a pair of zeroes.
                "acted": interventions > 0,
                "recovered": net != 0,
                "intervened_without_recovery": interventions > 0 and net == 0,
            }
        )
    return rows


#: `falsification.json` names each test by the failure it is looking for, not by
#: what it proves. Read cold, "REVIVE contacts per unit recovered worse than best
#: baseline / triggered: true" is unreadable — you cannot tell whether triggered
#: is good news. These are the plain readings, and every one is written so it
#: stays true whichever way the test came out. `note` carries the caveat where
#: the test's own construction limits what its result can mean.
_FALSIFICATION_MEANING: dict[str, dict[str, str]] = {
    "F-1": {
        "question": "In BALANCED, does REVIVE's median M-10 beat the best baseline?",
        "triggered": "No. Median M-10 in BALANCED did not exceed the best baseline.",
        "held": "Yes. Median M-10 in BALANCED exceeded the best baseline.",
    },
    "F-2": {
        "question": "Does REVIVE spend more customer contacts per rupee recovered?",
        "triggered": "Could not be cleared. REVIVE's contacts-per-rupee is above the baseline figure.",
        "held": "No. Contacts per rupee recovered were no worse than the best baseline.",
        "note": (
            "The baseline figure is 0.0 because the comparison only admits arms "
            "with positive M-10, and no baseline has any. So the bar REVIVE is "
            "measured against is an empty set, and any non-zero contact ratio "
            "trips this test. It says nothing about REVIVE's actual efficiency."
        ),
    },
    "F-3": {
        "question": "Does the recovery advantage survive its own costs in every cell?",
        "triggered": (
            "Not everywhere. At least one seed/profile ended at or below zero M-10 "
            "once realized cost was subtracted."
        ),
        "held": "Yes. M-10 stayed positive after costs in every cell.",
    },
    "F-4": {
        "question": "Did any guardrail metric fail during the run?",
        "triggered": "Yes. Guardrail violations were recorded.",
        "held": "No. Unauthorized executions, stopping-rule and policy violations were all zero.",
    },
    "F-5": {
        "question": "Does REVIVE ever land below the do-nothing floor?",
        "triggered": (
            "Yes. In at least one cell REVIVE's net came in below B0 — intervening "
            "cost more than letting natural recovery run."
        ),
        "held": "No. REVIVE stayed at or above the do-nothing floor in every cell.",
    },
    "F-6": {
        "question": "Is the run byte-for-byte reproducible?",
        "triggered": "A byte or numeric mismatch appeared on re-run.",
        "held": "Not evaluated in-run — deferred to the separate reproduction command.",
    },
}


def falsification_report(root: Path | None = None) -> dict[str, Any] | None:
    """The run's own attempts to refute itself, read in plain language.

    This is the least flattering file in the evidence tree and the most valuable
    one. A benchmark whose headline is "measured, not claimed" cannot show the
    600-cell count and quietly omit the three tests that fired.
    """
    directory = root or OFFICIAL_DIR
    data = _load_json(directory / "falsification.json")
    if not isinstance(data, dict):
        return None
    tests = []
    for t in data.get("tests", []):
        tid = str(t.get("test_id", ""))
        fired = bool(t.get("triggered"))
        meaning = _FALSIFICATION_MEANING.get(tid, {})
        tests.append(
            {
                "test_id": tid,
                "triggered": fired,
                "description": t.get("description"),
                "expected_failure_mode": t.get("expected_failure_mode"),
                "actual_result": t.get("actual_result"),
                "degraded_safely": bool(t.get("degraded_safely")),
                "unauthorized_actions": t.get("unauthorized_actions", 0),
                "question": meaning.get("question"),
                "reading": meaning.get("triggered" if fired else "held"),
                "note": meaning.get("note"),
            }
        )
    fired = [t["test_id"] for t in tests if t["triggered"]]
    return {
        "tests": tests,
        "any_triggered": bool(data.get("any_triggered")),
        "triggered_ids": fired,
        "triggered_count": len(fired),
        "total": len(tests),
        "unauthorized_actions_total": sum(int(t["unauthorized_actions"] or 0) for t in tests),
        "all_degraded_safely": all(t["degraded_safely"] for t in tests) if tests else False,
    }


#: What each safety counter would mean if it were not zero. A row of zeroes is
#: only reassuring once you know what a non-zero would have meant.
_SAFETY_MEANING: dict[str, str] = {
    "unauthorized_actions": "an action executed without an AUTHORIZED authorization",
    "policy_violations": "an action executed against a PolicyPack rule",
    "resource_oversubscriptions": "a resource committed beyond its declared capacity",
    "duplicate_effects": "the same effect applied to one opportunity twice",
    "stopping_rule_violations": "a run continued past a stopping rule",
}


def safety_audit(root: Path | None = None) -> dict[str, Any] | None:
    """Guardrail counters across all 600 cells — the CONTROL claim's evidence."""
    directory = root or OFFICIAL_DIR
    data = _load_json(directory / "audit_report.json")
    if not isinstance(data, dict):
        return None
    safety = data.get("safety")
    if not isinstance(safety, dict):
        return None
    counters = [
        {
            "key": key,
            "count": int(value or 0),
            "clean": int(value or 0) == 0,
            "means": _SAFETY_MEANING.get(key, "a recorded safety exception"),
        }
        for key, value in sorted(safety.items())
    ]
    return {
        "counters": counters,
        "all_clean": all(c["clean"] for c in counters),
        "total_exceptions": sum(c["count"] for c in counters),
        "scope": "600 cells · 120 groups · 20 seeds · 6 profiles · 5 policies",
    }


def policy_behaviour(root: Path | None = None) -> list[dict[str, Any]] | None:
    """Per-arm effort and realized recovery, from the indexed cell pass."""
    cache = _cache(root, build_index=True)
    return cache.get("policy_behaviour")


def profile_stats(root: Path | None = None) -> dict[str, Any] | None:
    """Per-profile M-10, held to one policy at a time.

    `aggregate.json.per_profile` pools all five arms, and four of them sit at
    exactly zero, so its mean is REVIVE's divided by five. Presenting that as
    "M-10 by profile" both understates the figure and mislabels an average over
    policies as a property of the operating profile. Split by policy instead —
    then a profile figure means what its label says.
    """
    directory = root or OFFICIAL_DIR
    per_profile = _load_json(directory / "per_profile.json")
    if not isinstance(per_profile, dict):
        return None
    out: dict[str, Any] = {}
    for profile, rows in per_profile.items():
        if not isinstance(rows, list):
            continue
        by_policy: dict[str, Any] = {}
        for policy in POLICIES:
            vals = [
                int(r.get("M-10_incremental_net_paise") or 0)
                for r in rows
                if isinstance(r, dict) and r.get("policy_id") == policy
            ]
            if not vals:
                continue
            by_policy[policy] = {
                "seeds": len(vals),
                "median": _money(int(statistics.median(vals))),
                "mean": _money(int(statistics.mean(vals))),
                "min": _money(min(vals)),
                "max": _money(max(vals)),
                "negative_seeds": sum(1 for v in vals if v < 0),
            }
        if by_policy:
            out[profile] = by_policy
    return out or None


def _load_metadata(root: Path) -> dict[str, Any]:
    manifest = _load_json(root / "manifest.json")
    aggregate = _load_json(root / "aggregate.json")
    per_policy = _load_json(root / "per_policy.json")
    config = _load_json(root / "config.json")
    validation = _load_json(root / "validation.json")
    freeze_check = _load_json(root / "freeze_check.json")
    reproducibility = _load_json(root / "reproducibility.json")
    return {
        "manifest": manifest,
        "aggregate": aggregate,
        "per_policy": per_policy,
        "per_profile_summary": aggregate.get("per_profile") if isinstance(aggregate, dict) else None,
        "config": config,
        "validation": validation,
        "freeze_check": freeze_check,
        "reproducibility": reproducibility,
        "falsification": falsification_report(root),
        "safety": safety_audit(root),
        "profile_stats": profile_stats(root),
        # `policy_behaviour` is deliberately absent here: it is cell-derived, and
        # this function is the cheap path. It arrives with the index instead.
        "provenance": {
            "source": "OFFICIAL CLOUD RUN",
            "source_path": str(root).replace("\\", "/"),
            "benchmark_version": manifest.get("benchmark_version") if manifest else None,
            "metrics_version": manifest.get("metrics_version") if manifest else None,
            "config_hash": manifest.get("config_hash") if manifest else None,
            "policy_pack_version": manifest.get("policy_pack_version") if manifest else None,
            "policy_pack_hash": config.get("PolicyPack_hash") if config else None,
            "frozen_experiment_reference": manifest.get("frozen_experiment_reference_hash") if manifest else None,
            "validation_status": manifest.get("validation_status") if manifest else None,
            "blocked": manifest.get("blocked") if manifest else None,
            "run_count": aggregate.get("run_count") if isinstance(aggregate, dict) else 600,
            "groups": 120,
            "cells": 600,
            "seeds": 20,
            "profiles": 6,
            "policies": 5,
        },
    }


def _cache(root: Path | None = None, *, build_index: bool = False) -> dict[str, Any]:
    global _CACHE
    directory = root or OFFICIAL_DIR
    cache_key = str(directory.resolve())
    if _CACHE is not None and _CACHE.get("root") == cache_key:
        if build_index and "matrix" not in _CACHE:
            with _INDEX_LOCK:
                if "matrix" not in _CACHE:
                    idx = _build_index(directory)
                    _CACHE["matrix"] = idx["matrix"]
                    _CACHE["search_index"] = idx["search_index"]
                    _CACHE["policy_behaviour"] = idx["policy_behaviour"]
        return _CACHE
    verification = verify_evidence(directory)
    payload: dict[str, Any] = {
        "root": cache_key,
        "verification": verification.to_dict(),
        "verified": verification.verified,
    }
    if verification.verified:
        payload.update(_load_metadata(directory))
        if build_index:
            idx = _build_index(directory)
            payload["matrix"] = idx["matrix"]
            payload["search_index"] = idx["search_index"]
            payload["policy_behaviour"] = idx["policy_behaviour"]
    _CACHE = payload
    return payload


def official_contract(
    root: Path | None = None, *, cache: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Machine-readable official experiment contract for evaluators.

    Available without mounted artefacts: declared design, methodology, engineering
    timeline, and how to supply evidence. Observed hashes and cell counts appear
    only when verification succeeded.
    """
    from revive.config.policy_pack import official_sealed_policy_pack
    from revive.product.benchmark_story import ACCESS, EVIDENCE_PATH, benchmark_story

    directory = root or OFFICIAL_DIR
    cache = cache if cache is not None else _cache(directory, build_index=False)
    verified = bool(cache.get("verified"))
    prov = cache.get("provenance") if isinstance(cache.get("provenance"), dict) else {}
    manifest = cache.get("manifest") if isinstance(cache.get("manifest"), dict) else {}
    verification = cache.get("verification") if isinstance(cache.get("verification"), dict) else {}
    declared = dict(DECLARED_RUN)
    pack = official_sealed_policy_pack()
    story = benchmark_story()

    def observed(key: str) -> Any:
        if not verified:
            return None
        if prov.get(key) is not None:
            return prov.get(key)
        return manifest.get(key)

    return {
        "product": "PAYVANTA",
        "internal_policy_id": "REVIVE",
        "role": story["role"],
        "benchmark_version": observed("benchmark_version"),
        "metric_version": observed("metrics_version"),
        "cell_count": verification.get("cell_count") if verified else None,
        "expected_cell_count": declared["cells"],
        "group_count": declared["groups"] if verified else None,
        "seed_count": declared["seeds"] if verified else None,
        "profile_count": declared["profiles"] if verified else None,
        "policy_count": declared["policies"] if verified else None,
        "validation": observed("validation_status"),
        "blocked": observed("blocked"),
        "verified": verified,
        "frozen_experiment_hash": (
            observed("frozen_experiment_reference") or declared["frozen_experiment_reference"]
        ),
        "config_hash": observed("config_hash"),
        "policy_pack": {
            "version": pack.version,
            "hash": pack.config_hash(),
            "observed_version": observed("policy_pack_version"),
            "observed_hash": observed("policy_pack_hash"),
        },
        "evidence_path": EVIDENCE_PATH,
        "access": ACCESS,
        "m10": story["m10"],
        "why": story["why"],
        "profiles": story["profiles"],
        "policies": story["policies"],
        "engineering": story["engineering"],
        "limitations": story["limitations"],
        "claims": story["claims"],
        "discoverability": story["discoverability"],
        "sandbox_vs_official": story["sandbox_vs_official"],
        "reference_cell": story["reference_cell"],
        "story": story,
    }


def official_summary(root: Path | None = None) -> dict[str, Any]:
    cache = _cache(root, build_index=False)
    payload = dict(cache)
    payload["contract"] = official_contract(root, cache=cache)
    return payload


def official_matrix(root: Path | None = None) -> dict[str, Any]:
    cache = _cache(root, build_index=True)
    matrix = cache.get("matrix", {})
    return {
        "status": "ready" if cache.get("verified") and matrix else "unavailable",
        "verified": cache.get("verified", False),
        "profiles": list(PROFILES),
        "policies": list(POLICIES),
        "matrix": matrix,
        "cell_groups": sum(len(row) for row in matrix.values()) if matrix else 0,
        "policy_behaviour": cache.get("policy_behaviour"),
        "reference_policy": REFERENCE_POLICY,
        "intervening_baselines": list(INTERVENING_BASELINES),
    }


def official_cell_detail(
    seed: int,
    profile: str,
    policy: str,
    root: Path | None = None,
) -> dict[str, Any]:
    validate_cell_params(seed, profile, policy)
    directory = root or OFFICIAL_DIR
    path = _cell_path(directory, seed, profile, policy)
    resolved = path.resolve()
    if not str(resolved).startswith(str((directory / "cells").resolve())):
        raise ValueError("path traversal rejected")
    if not resolved.is_file():
        raise FileNotFoundError("cell not found")

    data = _load_json(resolved)
    if not isinstance(data, dict):
        raise ValueError("invalid cell artefact")

    cache = _cache(directory, build_index=True)
    b0_lookup = _b0_lookup(directory)
    metrics = data.get("metrics", {})
    b0_net = b0_lookup.get((seed, profile), 0)
    m10 = m10_from_cell(metrics, b0_net)
    # Every official cell records ``M-10_incremental_net_paise: null`` — the metric is
    # a paired quantity, so it is resolved against the B0 run of the same seed and
    # profile rather than stored per cell. The surface must not present the result as
    # a field it read out of this file, so the reference and its origin travel with it.
    m10_stored = metrics.get("M-10_incremental_net_paise") is not None

    artefact_rel = str(resolved.relative_to(directory.resolve())).replace("\\", "/")
    metrics_block = {
        "run_valid": metrics.get("run_valid"),
        "m10_incremental_net": _money(m10),
        "recovery_rate": metrics.get("recovery_rate"),
        "gross_recovered": _money(metrics.get("gross_recovered_paise")),
        "incremental_recovered": _money(metrics.get("incremental_recovered_paise")),
        "natural_recovered": _money(metrics.get("natural_recovered_paise")),
        "net_recovered": _money(metrics.get("net_recovered_paise")),
        "realized_cost": _money(metrics.get("realized_cost_paise")),
        "interventions": metrics.get("intervention_count"),
        "execution_failures": metrics.get("execution_failures"),
        "policy_violations": metrics.get("policy_violations"),
        "unauthorized_executions": metrics.get("unauthorized_executions"),
        "resource_utilization": metrics.get("resource_utilization"),
    }
    validation = {
        "run_valid": metrics.get("run_valid"),
        "metrics_checksum": data.get("metrics_checksum"),
        "artefact_path": artefact_rel,
        "evidence_path": str(directory).replace("\\", "/"),
        "official_verified": bool(cache.get("verified")),
    }
    return {
        "seed": seed,
        "profile": profile,
        "policy": policy,
        "cell_index": data.get("cell_index"),
        "run_valid": metrics.get("run_valid"),
        "m10_incremental_net": _money(m10),
        "m10_source": "artefact" if m10_stored else "derived",
        "m10_reference_policy": REFERENCE_POLICY,
        "m10_reference_net": _money(b0_net),
        "recovery_rate": metrics.get("recovery_rate"),
        "gross_recovered": _money(metrics.get("gross_recovered_paise")),
        "incremental_recovered": _money(metrics.get("incremental_recovered_paise")),
        "natural_recovered": _money(metrics.get("natural_recovered_paise")),
        "net_recovered": _money(metrics.get("net_recovered_paise")),
        "realized_cost": _money(metrics.get("realized_cost_paise")),
        "interventions": metrics.get("intervention_count"),
        "execution_failures": metrics.get("execution_failures"),
        "policy_violations": metrics.get("policy_violations"),
        "unauthorized_executions": metrics.get("unauthorized_executions"),
        "resource_utilization": metrics.get("resource_utilization"),
        "metrics": metrics_block,
        "metrics_checksum": data.get("metrics_checksum"),
        "config_hash": data.get("config_hash"),
        "policy_pack_version": data.get("policy_pack_version"),
        "policy_pack_hash": data.get("policy_pack_hash"),
        "artefact_path": artefact_rel,
        "artifact": artefact_rel,
        "validation": validation,
        "raw": data,
    }


SEARCH_RESULT_CAP = 40

# Words that name an axis rather than a value on it. A reader types what the field's
# own placeholder suggests — "seed 14 ABUNDANT REVIVE" — and every token had to match
# a profile, policy or number, so the axis word matched nothing and the whole query
# returned empty. Dropping them makes the documented example work without loosening
# what an actual value token has to match.
SEARCH_NOISE_TOKENS = frozenset(
    {"SEED", "SEEDS", "PROFILE", "POLICY", "CELL", "CELLS", "INDEX", "X", "×", "V", "VS"}
)


def search_official_cells_page(
    query: str, root: Path | None = None
) -> dict[str, Any]:
    """Matching cells, plus what the cap withheld.

    Returning only the capped list makes a truncated result read as a complete one —
    40 of 100 matches looks like "there are 40". The total travels with the page so the
    surface can say which it is.
    """
    q = query.strip().upper()
    if not q:
        return {"results": [], "total": 0, "cap": SEARCH_RESULT_CAP, "truncated": False}
    cache = _cache(root, build_index=True)
    if not cache.get("verified"):
        return {"results": [], "total": 0, "cap": SEARCH_RESULT_CAP, "truncated": False}
    tokens = [
        t
        for t in re.split(r"[\s,/]+", q)
        if t and t not in SEARCH_NOISE_TOKENS
    ]
    if not tokens:
        return {"results": [], "total": 0, "cap": SEARCH_RESULT_CAP, "truncated": False}
    results: list[dict[str, Any]] = []
    for row in cache.get("search_index", []):
        seed_s = str(row["seed"])
        profile = str(row["profile"]).upper()
        policy = str(row["policy"]).upper()
        cell_index = str(row.get("cell_index", ""))
        ok = True
        for token in tokens:
            if token.isdigit():
                if token != seed_s and token != cell_index:
                    ok = False
                    break
            elif token not in (profile, policy) and token not in f"{profile} {policy} {cell_index}":
                ok = False
                break
        if ok:
            results.append(row)
    return {
        "results": results[:SEARCH_RESULT_CAP],
        "total": len(results),
        "cap": SEARCH_RESULT_CAP,
        "truncated": len(results) > SEARCH_RESULT_CAP,
    }


def search_official_cells(query: str, root: Path | None = None) -> list[dict[str, Any]]:
    return search_official_cells_page(query, root)["results"]


def invalidate_cache() -> None:
    global _CACHE
    _CACHE = None
