"""Write machine-readable benchmark artefacts — M13 §31."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from revive.benchmark.official.aggregate import BenchmarkAggregate
from revive.benchmark.official.config import OfficialBenchmarkConfig
from revive.benchmark.official.falsification import FalsificationReport
from revive.benchmark.official.freeze import FreezeCheckResult
from revive.benchmark.official.validate import ValidationResult


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_benchmark_artifacts(
    output_dir: Path,
    config: OfficialBenchmarkConfig,
    config_hash: str,
    aggregate: BenchmarkAggregate,
    validation: ValidationResult,
    falsification: FalsificationReport,
    freeze: FreezeCheckResult | None = None,
    *,
    mode: str,
    blocked: bool = False,
    frozen_experiment_hash: str | None = None,
    preflight_gate=None,
    implementation_revision: str | None = None,
    runner_version: str | None = None,
) -> Path:
    root = output_dir
    root.mkdir(parents=True, exist_ok=True)

    _write_json(root / "config.json", config.to_dict())
    (root / "config_hash.txt").write_text(config_hash, encoding="utf-8")

    manifest = {
        "benchmark_version": config.benchmark_version,
        "config_hash": config_hash,
        "frozen_experiment_reference_hash": frozen_experiment_hash,
        "implementation_revision": implementation_revision,
        "benchmark_runner_version": runner_version,
        "code_revision": config.code_revision,
        "generator_version": config.generator_version,
        "policy_pack_version": config.policy_pack_version,
        "metrics_version": config.metric_version,
        "mode": mode,
        "blocked": blocked,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "validation_status": validation.status,
    }
    if preflight_gate is not None:
        manifest["preflight_label"] = preflight_gate.label
        manifest["preflight_passed"] = preflight_gate.passed
    _write_json(root / "manifest.json", manifest)

    runs_dir = root / "runs"
    for m in aggregate.per_run:
        run_path = runs_dir / f"seed-{m.seed:03d}" / m.profile / m.policy_id
        _write_json(run_path / "metrics.json", m.to_dict())

    _write_json(root / "aggregate.json", aggregate.to_dict())
    _write_json(
        root / "per_profile.json",
        {
            profile: [m.to_dict() for m in runs]
            for profile, runs in aggregate.per_profile.items()
        },
    )
    _write_json(
        root / "per_policy.json",
        {pid: aggregate.policy_summary(pid) for pid in aggregate.per_policy},
    )

    failures = [
        m.to_dict()
        for m in aggregate.per_run
        if not m.run_valid or m.execution_failures > 0
    ]
    _write_json(root / "failure_report.json", {"failures": failures})

    safety = {
        "unauthorized_actions": sum(m.unauthorized_executions for m in aggregate.per_run),
        "stopping_rule_violations": sum(
            m.stopping_rule_violations for m in aggregate.per_run
        ),
        "policy_violations": sum(m.policy_violations for m in aggregate.per_run),
        "duplicate_effects": sum(m.duplicate_effects for m in aggregate.per_run),
        "resource_oversubscriptions": sum(
            m.resource_oversubscriptions for m in aggregate.per_run
        ),
    }
    _write_json(root / "audit_report.json", {"safety": safety})

    repro = {
        "reproduction_command": "revive benchmark --mode development --reproduce",
        "config_hash": config_hash,
        "code_revision": config.code_revision,
        "seed_set": list(config.seed_set),
        "profile_set": [p.value for p in config.profile_set],
    }
    _write_json(root / "reproducibility.json", repro)

    _write_json(root / "validation.json", validation.to_dict())
    _write_json(root / "falsification.json", falsification.to_dict())

    if freeze is not None:
        _write_json(root / "freeze_check.json", freeze.to_dict())

    if preflight_gate is not None:
        _write_json(root / "preflight_gate.json", preflight_gate.to_dict())

    summary_path = root / "benchmark_summary.md"
    summary_path.write_text(
        _human_summary(
            config,
            config_hash,
            aggregate,
            validation,
            falsification,
            mode,
            blocked,
            preflight_gate=preflight_gate,
            frozen_experiment_hash=frozen_experiment_hash,
            implementation_revision=implementation_revision,
        ),
        encoding="utf-8",
    )

    return root


def _human_summary(
    config: OfficialBenchmarkConfig,
    config_hash: str,
    aggregate: BenchmarkAggregate,
    validation: ValidationResult,
    falsification: FalsificationReport,
    mode: str,
    blocked: bool,
    *,
    preflight_gate=None,
    frozen_experiment_hash: str | None = None,
    implementation_revision: str | None = None,
) -> str:
    lines = [
        "# M13 Benchmark Summary",
        "",
        f"Mode: **{mode}**",
    ]
    if preflight_gate is not None:
        lines.extend(
            [
                "",
                f"> **{preflight_gate.label}**",
                f"> Preflight gate passed: **{preflight_gate.passed}**",
            ]
        )
    lines.extend(
        [
        f"Blocked: **{blocked}**",
        f"Config hash: `{config_hash}`",
        ]
    )
    if frozen_experiment_hash:
        lines.append(f"Frozen experiment reference hash: `{frozen_experiment_hash}`")
    if implementation_revision:
        lines.append(f"Implementation revision: `{implementation_revision}`")
    lines.extend(
        [
        f"Validation: **{validation.status}**",
        "",
        "## Primary metric (M-10) — per policy",
        "",
        ]
    )
    for pid in ("B0", "B1", "B2", "B3", "REVIVE"):
        summary = aggregate.policy_summary(pid)
        runs = aggregate.per_policy.get(pid, [])
        intervention_total = sum(r.intervention_count for r in runs)
        if summary:
            lines.append(
                f"- **{pid}**: M-10 median={summary.get('M-10_median_paise')} paise, "
                f"mean={summary.get('M-10_mean_paise')} paise, "
                f"interventions={intervention_total}"
            )

    if aggregate.revive_vs_b3:
        lines.extend(
            [
                "",
                "## REVIVE vs B3 (allocation lift)",
                "",
                f"- {aggregate.revive_vs_b3.get('label')}",
                f"- Mean lift (M-10): {aggregate.revive_vs_b3.get('allocation_lift_m10_paise_mean')} paise",
            ]
        )

    lines.extend(
        [
            "",
            "## Safety",
            "",
            f"- Unauthorized executions (total): {sum(m.unauthorized_executions for m in aggregate.per_run)}",
            "",
            "## Falsification",
            "",
        ]
    )
    for fr in falsification.results:
        lines.append(
            f"- **{fr.test_id}**: triggered={fr.triggered} — {fr.actual_result}"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Results reported without inflation. Under the frozen benchmark configuration, "
            "compare policies using paired M-10 per seed/profile.",
            "",
            "## Limitations",
            "",
            "- Freeze prerequisites may be incomplete for official claims.",
            "- ADR-012 official scale pending.",
            "- Results are synthetic-environment comparisons only.",
        ]
    )
    return "\n".join(lines) + "\n"
