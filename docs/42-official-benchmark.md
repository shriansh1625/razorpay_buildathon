# 42 · Official Benchmark as Evidence

The benchmark is **not the product**. It is the experimental proof and engineering
validation layer around PAYVANTA.

The product demonstrates a bounded recovery workflow. The official experiment
evaluates the same engine under a frozen contract.

> This is the engine you just saw operating. That engine was evaluated separately
> across 600 official cells.

Do not treat a sandbox run as a cell. Do not modify
`artefacts/benchmark/official-cloud-final/`. Do not rerun the official benchmark
into that directory.

---

## 1. Track 03 mapping

Razorpay Track 03 asks for an agent that **detects revenue at risk → determines
the right intervention → executes a bounded recovery workflow**, with **measured
money recovered across a batch**, compliant escalation, stopping rules, and an
audit trail.

The Control Room shows detect → intervene → execute. The official benchmark
supplies the **measured** and **evidence** half: 600 cells, paired M-10,
guardrail tallies, frozen hashes.

---

## 2. Official experiment (frozen)

| Axis | Value |
|---|---|
| Seeds | 20 |
| Profiles | 6 |
| Policies | 5 — B0, B1, B2, B3, REVIVE |
| Cells | 600 = 20 × 6 × 5 |
| Groups | 120 = 20 × 6 |
| Workers | 8 |
| Validation | `BENCHMARK_VALID` |
| Blocked | `false` |
| Path | `artefacts/benchmark/official-cloud-final/` |
| Frozen experiment hash | `cc8cad59779fd594f26599d5c8d7b965f774cff83a70eb44f9673e1e7556e4b0` |

`REVIVE` is the internal policy identifier. The product name is PAYVANTA.

---

## 3. Why 20 × 6 × 5 = 600

Not a claim that six hundred runs “prove superiority.”

| Factor | Why it exists |
|---|---|
| 20 seeds | Deterministic variation with repeatability. Same seed, same world. |
| 6 profiles | Different operating environments (`docs/19-synthetic-dataset.md` § 2.3). |
| 5 policies | Comparative evaluation on identical inputs (`docs/20-benchmark.md` § 2). The official run used B0–B3 + REVIVE, not B4–B6. |
| 600 cells | Every combination, once. Systematic coverage rather than one selected scenario. |
| 120 groups | One world (seed × profile) under all five policies. |

---

## 4. Profiles

From `revive/simulation/profiles.py` (docs/19 § 2.3):

| Profile | Description |
|---|---|
| BALANCED | Mixed classes, moderate scarcity — primary benchmark profile |
| HIGH_NATURAL | Many opportunities self-recover; punishes over-contacting |
| SCARCE | Severe budget/capacity limits; stresses allocation |
| ABUNDANT | Near-unlimited capacity; expected to shrink allocator advantage |
| HOSTILE | Heavy adversarial injection; tests guardrails and stopping |
| DEGRADED | Provider outage windows; timing-sensitive recovery |

---

## 5. Policies

From `docs/20-benchmark.md` § 2. Official experiment arms:

| ID | Baseline | Isolates |
|---|---|---|
| B0 | NO_ACTION | Natural recovery floor |
| B1 | FIXED_RETRY | Retry without targeting |
| B2 | CONTACT_ALL | Effort without prioritisation |
| B3 | GREEDY_ENRV | Scoring without constrained allocation |
| REVIVE | PAYVANTA recovery policy | The engine under test |

---

## 6. M-10

`docs/21-evaluation.md` § 2.1; `docs/37-metrics-dictionary.md`.

**M-10 Incremental Net Recovered Revenue** (user-facing: **incremental net recovery**):

```
M-10(policy, seed) = NetRecovered(policy, seed) − NetRecovered(B0_NO_ACTION, seed)
```

Paired. Can be negative. Primary judging metric of the experiment. Not the
Control Room sandbox figure. Not a production guarantee.

---

## 7. Sandbox vs official

| | Sandbox | Official benchmark |
|---|---|---|
| Purpose | Demonstrate the working recovery workflow | Evaluate the engine under a frozen experiment |
| Data | Synthetic test population, bounded local execution | Frozen 20 × 6 × 5 cells |
| Money | This session’s incremental net | Paired M-10 vs B0 |
| Writable | Session may be rebuilt | Read-only |

---

## 8. How we got here

Records, not slogans:

| Milestone | Kind | Record |
|---|---|---|
| M13.24 Parallel dispatch | Debugging | `implementation/m13-24-stress-worker-dispatch/` |
| M13.25 Checkpoint repair | Repair | `implementation/m13-25-checkpoint-repair/` |
| M13.26 ABUNDANT forensics | Profiling | `implementation/m13-26-abundant-revive-forensics/` |
| M13.27 Metrics-tail rescue | Optimization | `implementation/m13-27-metrics-tail-rescue/` |
| Cloud validation | Validation | `implementation/m13-27-metrics-tail-rescue/cloud-validation.md` |
| Official 600-cell run | Evidence | `artefacts/benchmark/official-cloud-final/` |

M13.24: CLI parsed `--workers 8`; stress dispatch dropped it; sequential
execution. Fix: forward workers. Fingerprints match for workers=1/2/8. Wall on
a 10-cell (2-group) stress: 72.336s / 39.788s / 31.689s — not an 8× speedup.

M13.25: workers persisted cells atomically; manifest advanced only after a
complete 5-policy group. 4/5 files existed; manifest said 26/30. Fix: startup
reconciliation, files-ahead / manifest-ahead drift, parent-owned checkpoint
updates. Tests in `tests/benchmark/test_m13_25_checkpoint_resume.py`.

M13.26: ABUNDANT × REVIVE was slower, not hung. Cell wall: BALANCED 555.1s,
SCARCE 486.5s, HOSTILE 539.7s, ABUNDANT 1363.0s. Cause: `capacity_scarcity_factor=0.2`
→ ~339,890 executions → M6/M7/M8, especially M8 Lagrangian (`lagrangian_allocate`
264s). DEVELOPMENT_FORENSIC_ONLY.

M13.27: `compute_policy_metrics` unauthorized counter was O(authorization ×
execution). Old cross-scan ~4137.6s; new `compute_policy_metrics` ~0.321s local;
cloud metrics tail ~0.39s. Cloud cell ~627.3s vs previous ~9900s.
**Performance / reliability engineering — not a benchmark score.**

Cloud validation (seed=1, ABUNDANT, REVIVE, 2016 cycles): 627.3s total, 0.39s
metrics tail, 594 MB peak RSS, 339,890 executions, 404,319 authorizations,
339,890 measurements, checksum
`80c238eb91edc64424079d2b9bac4f354886fac4089cf96668b493f8245113da`,
`run_valid=true`, `policy_violations=0`, `unauthorized_executions=0`.

Then the official experiment. Evidence kept read-only.

---

## 9. Performance validation (not a score)

```
~9900s  pre-optimization cloud cell
   ↓    metrics-tail rescue
~627s   post-optimization cloud cell

~4137s  unauthorized cross-scan
   ↓
0.39s   cloud metrics tail
```

Checksums unchanged. Do not present this as an M-10 improvement.

---

## 10. Discoverability

| Need | Where |
|---|---|
| Methodology | README § Measured, Not Claimed · this file · `GET /api/benchmark/story` · `#/benchmark` |
| Artefact location | `artefacts/benchmark/official-cloud-final/` · `GET /api/benchmark/official/contract` |
| Validation | `validation.json` · `#/benchmark/evidence` |
| Config hash / PolicyPack | manifest · contract API · Forensics tab |
| Cell matrix | `#/benchmark/matrix` · `GET /api/benchmark/official/matrix` |
| M-10 definition | `docs/21-evaluation.md` § 2.1 · story API |
| Engineering timeline | README § How We Got Here · this file · story API |
| One cell | ABUNDANT × REVIVE × seed 14 · `GET /api/benchmark/official/cell/14/ABUNDANT/REVIVE` |

`artefacts/` is gitignored. A clone without the tree still has this document,
the declared contract, and the APIs. Mount the frozen tree to verify; do not
regenerate it.

---

## 11. Pitch segment (≈ 40–50 seconds)

04:10 — “Now let’s see whether this is just one carefully selected scenario.”
04:15 — 20 × 6 × 5
04:20 — 600 official cells
04:25 — 120 groups
04:30 — matrix
04:35 — ABUNDANT × REVIVE
04:40 — seed 14
04:45 — cell evidence + checksum
04:50 — “Same engine. Measured across the experiment.”
05:00 — MEASURED. NOT CLAIMED.

---

## 12. Judge questions

| Question | Answer |
|---|---|
| What makes this different from an ordinary demo? | One run demonstrates the system. 600 official cells evaluate the engine. |
| What did you actually improve? | Parallelism, checkpoint reliability, ABUNDANT performance, metrics aggregation, cloud validation. |
| Can I inspect one result? | Yes. ABUNDANT × REVIVE × seed 14. |

Vocabulary: evaluated, measured, validated, observed, verified.
Not: scientifically proven, production proven, guaranteed recovery, 600 cells
prove superiority.
