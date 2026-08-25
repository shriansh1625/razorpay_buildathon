# M13 — Official Benchmark + Evidence Engine

**Status:** COMPLETE (engine + development validation)  
**Official benchmark run:** BLOCKED — FREEZE INCOMPLETE  
**Date:** 2026-08-23  
**Tests:** 211 passing (10 new M13 tests)

---

## Benchmark objective

Compare **B0, B1, B2, B3, REVIVE** under identical controlled conditions on the primary metric **M-10 Incremental Net Recovered Revenue** (paired against B0 per docs/21 §2.1).

Hypothesis to test (not assumed): portfolio-aware constrained allocation recovers more incremental net revenue than simpler strategies under scarce shared resources.

---

## Frozen configuration

| Field | Value |
|-------|-------|
| `benchmark_id` | `revive_official_v1` (official template) / `revive_dev_m13` (development) |
| `benchmark_version` | `0.13.0-m13` |
| `generator_version` | `0.2.0-m2` |
| `predictor_version` | `0.7.0-m7:strat_m7_dev` |
| `allocator_version` | `0.8.0-m8` |
| `metric_version` | `0.12.0-m12` |
| `B1_schedule_version` | `adr-013_draft_v1` |
| `approver_model_version` | `simulated_v1_provisional` |
| `llm_mode` | `LLM_OFF` |
| `allocator_mode` | `LAGRANGIAN` |
| Official scale (PROPOSED) | 500 opportunities, 100 customers, 30-day horizon, 15-min cycles |
| Development scale | `tiny_config` (12 opportunities, 8 customers, 14 days) |

**Development config hash:** `44b4d9dd617233f44eccc370519255e0b673214029e78e2f8b0b2f5bfc74f070`

---

## Freeze gate — OFFICIAL RUN BLOCKED

Required freeze items **not** resolved:

| Item | Status |
|------|--------|
| ADR-011 (ε) | DRAFT — PolicyPack not SEALED |
| PolicyPack | DRAFT |
| ADR-012 (official scale) | PENDING |
| ADR-013 (B1 schedule) | DRAFT |
| Approver model | provisional |
| Generator config | PROVISIONAL |
| Predictor/strategy | `strat_m7_dev` (development) |
| Official seed set (≥20) | Not executed at official scale |

**Official mode returns:** `BENCHMARK BLOCKED — FREEZE INCOMPLETE`

Development runs continue separately with explicit `DEVELOPMENT` mode labeling.

---

## Seed policy

- Official (documented): **20 seeds** (`seed 1…20`) — `RR-NFR-033` PROPOSED
- Development: **1 seed** (`seed=1`) for fast validation

---

## Profile policy

Official profile set (all required when freeze complete):

- BALANCED, HIGH_NATURAL, SCARCE, ABUNDANT, HOSTILE, DEGRADED

Development: BALANCED only.

---

## Policy set

| ID | Pipeline |
|----|----------|
| B0 | NO_ACTION baseline → shared execution/measurement |
| B1 | FIXED_RETRY → authorize → execute → measure |
| B2 | CONTACT_ALL → authorize → execute → measure |
| B3 | GREEDY_ENRV → authorize → execute → measure |
| REVIVE | Full M4–M12: detect → understand → candidates → value → allocate → seal → authorize → execute → measure |

No benchmark-only simplified REVIVE path.

---

## Metrics

Primary: **M-10** = `NetRecovered(policy) − NetRecovered(B0)` per seed/profile.

Secondary collected: gross/natural/incremental recovery, costs, contacts, interventions, safety counts, prediction error, budget/resource utilization.

---

## Fairness controls

- One `generate_shared_world()` per seed/profile; policies run on **cloned worlds** (same oracle partition, independent observable state)
- Identical PolicyPack, costs, capacities, horizons, RNG architecture
- Baselines extended with `persist_context` for multi-cycle contact accounting
- REVIVE uses per-assignment seal to respect M9 ledger semantics

---

## Oracle isolation

- `assert_decision_path_does_not_import_oracle()` — pass
- `assert_baseline_modules_do_not_import_oracle()` — pass
- Oracle partition only at execution/measurement boundary

---

## B3 ablation

`revive_vs_b3` reports paired M-10 difference per cell:

> comparative outcome under the benchmark environment (REVIVE M-10 − B3 M-10)

No causal claim beyond experiment design.

---

## Falsification (F-1…F-6)

Engine runs falsification tests on completed aggregates. Development run (1 seed, BALANCED):

| Test | Triggered | Notes |
|------|-----------|-------|
| F-1 | Yes | median REVIVE M-10 ≤ best baseline (both 0) |
| F-2 | No | contacts per unit |
| F-3 | Yes | non-positive M-10 (0) |
| F-4 | No | guardrails |
| F-5 | No | net vs B0 |
| F-6 | Deferred | `reproduce_benchmark()` — **pass** (identical fingerprints) |

---

## Development results (NOT official evidence)

Single cell: seed=1, profile=BALANCED, tiny scale.

| Policy | M-10 median (paise) | Unauthorized |
|--------|---------------------|--------------|
| B0 | 0 | 0 |
| B1 | 0 | 0 |
| B2 | 0 | 0 |
| B3 | 0 | 0 |
| REVIVE | 0 | 0 |

**Interpretation:** Under the development configuration, all policies tied at zero incremental net recovery vs B0. This is **not** evidence of superiority or inferiority — scale is tiny and freeze is incomplete.

**REVIVE vs B3 allocation lift (M-10):** 0 paise (1 cell).

---

## Failures

- No execution failures in development run
- No unauthorized executions
- Official matrix not executed (freeze blocked)

---

## Safety

Development aggregate:

- `unauthorized_actions` = 0
- `stopping_rule_violations` = 0 (not independently re-evaluated in aggregate)
- `policy_violations` = 0

---

## Reproducibility

- Command: `revive benchmark --mode development --reproduce`
- Python: `reproduce_benchmark(mode=BenchmarkMode.DEVELOPMENT)` → identical aggregate fingerprints
- Artefacts: `artefacts/benchmark/dev/`

---

## Package layout

```
revive/benchmark/official/
  config.py          # OfficialBenchmarkConfig
  freeze.py          # Freeze gate
  hash.py            # OFFICIAL_BENCHMARK_CONFIG_HASH
  world.py           # Shared world + clone
  policies.py        # B0–B3 + REVIVE
  revive_pipeline.py # Full M4–M12
  baseline_pipeline.py
  policy_runner.py
  metrics.py
  aggregate.py
  validate.py        # BENCHMARK_VALID / INVALID
  falsification.py
  artifacts.py
  runner.py          # execute_benchmark()
  reproduce.py
```

CLI: `revive benchmark --mode development|official`

---

## Limitations

1. Official benchmark cannot be published until freeze prerequisites resolved
2. ADR-012 official scale not finalized
3. Development tiny config may produce zero recovery — not representative
4. REVIVE detect() vs baseline `world.opportunities` path may differ — documented architectural seam from M3/M4
5. Multi-assignment seal uses per-assignment workaround for M9 ledger global-resource semantics

---

## Final interpretation

M13 delivers an **honest evidence engine** with freeze gate, config hash, shared-world fairness, full REVIVE pipeline, falsification hooks, and artefact output.

**No official comparative claim is made:** freeze is incomplete and development results show no incremental recovery at tiny scale.

Under the frozen benchmark configuration (when complete), report:

> "REVIVE achieved X compared with Y for B3" — **not yet measurable at official scale**.

---

## Next milestone

**STOP.** M13 is the evidence gate.

Do **not** proceed to learning, final UI, voice, or pitch deck without explicit review and official freeze + benchmark rerun.
