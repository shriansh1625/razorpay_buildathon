# Root Cause — M13.17 Official Zero Execution

## Classification: **H — CONFIGURATION / RUNNER**

Official benchmark pipeline uses a materially different and **broken execution path** relative to what M13.5 calibration validated.

Two distinct integration defects share the same outcome (`intervention_count = 0` for all policies):

---

## Defect 1 — Baseline sentinel ID bridge (B1/B2/B3)

### Stage

Between baseline policy decision and M10 — **`run_baseline_cycle_full()` sentinel lookup**.

### Code path

```92:98:revive/benchmark/official/baseline_pipeline.py
    for bd in cycle_result.decisions:
        if bd.outcome != DecisionOutcome.SELECTED or bd.action_code == ActionCode.A00:
            continue

        detected = opp_by_id.get(bd.opportunity_id)
        if detected is None:
            continue
```

`opp_by_id` is built from `detect(view, now_micros).opportunities` (line 87-88).

Baseline decisions use world `opportunity_id` from `opportunities_from_observable(view)` (`revive/benchmark/runner.py:17-21`).

Sentinel assigns **`opportunity_id_for(natural_key)`** (`revive/recovery/sentinel/detect.py:312`), not the generator world ID (`revive/simulation/generator.py:453`).

### Counts (seed=1 BALANCED, official config)

| Policy | Decisions SELECTED | Sentinel match | Authorizations |
|--------|-------------------:|---------------:|---------------:|
| B1 | 117,949 | 0 | 0 |
| B2 | 158,252 | 0 | 0 |
| B3 | 100,902 | 0 | 0 |

### Artifact evidence

`artefacts/benchmark/official/cells/seed-001/BALANCED/B{1,2,3}.json` — all zero execution metrics, `run_valid: true`.

---

## Defect 2 — Missing simulated approver (REVIVE)

### Stage

**M10 — Gate G7** (`revive/policy/gates.py:207-240`).

### Code path

REVIVE reaches `authorize_execution()` (`revive_pipeline.py:193-204`) but skips execution when not `AUTHORIZED`:

```203:204:revive/benchmark/official/revive_pipeline.py
        if auth.authorization_state != AuthorizationState.AUTHORIZED:
            continue
```

### Counts (seed=1 BALANCED, full 2016 cycles)

| Metric | Value |
|--------|------:|
| M8 selected | > 0 |
| M10 authorization calls | 121,107 |
| M10 AUTHORIZED | **0** |
| M10 REQUIRES_HUMAN_APPROVAL | **121,107 (100%)** |
| G7 trigger UNCERTAINTY | **121,107 (100%)** |
| M11 executions | 0 |

### Config vs implementation

Frozen config: `approver_model_version: simulated_v1`.

`AuthorizeContext.approval_state` defaults to `None`; official pipelines never set `ApprovalRequestState.APPROVED`.

G7 fires UNCERTAINTY on ENRV interval width; without simulated approval, every authorization stalls at `REQUIRES_HUMAN_APPROVAL`.

### Artifact evidence

`artefacts/benchmark/official/cells/seed-001/BALANCED/REVIVE.json` — ~570 s runtime, zero interventions.

---

## What this is NOT

| Ruled out | Evidence |
|-----------|----------|
| M-10 aggregation-only bug | All underlying recovery fields zero in 600/600 cells |
| M8 fails to select (REVIVE) | M8 selected count > 0 |
| M10 G1–G6 / SR blocks (REVIVE) | 100% G7 UNCERTAINTY only |
| M11 execution failure | M11 never invoked (0 authorized) |
| M12 measurement loss | 0 executions to measure |
| Genuine zero-recovery environment | M13.5 oracle: 61% avg natural rate, intervention-sensitive opps; M13.5 B1/B2/B3 nonzero decision snapshots |

---

## Why validator reports BENCHMARK_VALID

Zero is internally consistent: no unauthorized executions, no guardrail violations, complete run matrix. Validity checks structure — not economic interpretability.

---

## Diagnostic script

Reproducible read-only counters:

`implementation/m13-17-zero-execution-trace/trace_official_zero_execution.py`

Does not modify official artifacts or repository logic.
