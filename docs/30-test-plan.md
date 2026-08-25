# 30 · Test Plan

Tests are implementation-oriented but not implemented here. Every important requirement has at
least one test. Tests reference the state machine ([34](34-state-machine.md)), policy gates
([13](13-policy-and-guardrails.md)), stopping rules ([14](14-stopping-rules.md)), and functional
requirements ([05](05-functional-requirements.md)) by their stable IDs.

---

## 1. Test categories

| Category | Purpose | Failure means |
|---|---|---|
| **Functional** | Verify that each `RR-FUNC-*` requirement is satisfied | A requirement is unmet |
| **Integration** | Verify end-to-end pipeline from signal to outcome | Components do not compose correctly |
| **Policy** | Verify every gate and every verdict | A guardrail is bypassable |
| **Safety** | Verify financial safety invariants | Money can move incorrectly |
| **Failure** | Verify behaviour under failure conditions | Failures are not contained |
| **Evaluation** | Verify metrics computation and reporting | Results are untrustworthy |
| **Reproducibility** | Verify determinism | Benchmark is invalid |
| **State-machine** | Verify legal and illegal transitions | State corruption possible |

---

## 2. Functional tests

### 2.1 SEE — Detection

| Test ID | Requirement | Description | Acceptance |
|---|---|---|---|
| T-FUNC-001 | `RR-FUNC-001` | Detection recall per risk class | Recall ≥ 0.99 per class against generator ground truth |
| T-FUNC-002 | `RR-FUNC-001` | Detection precision per risk class | Precision ≥ 0.99 per class |
| T-FUNC-003 | `RR-FUNC-002` | Value-at-risk computation | Recomputation from source record yields identical integer |
| T-FUNC-004 | `RR-FUNC-003` | Signal deduplication | Duplicate signal → one opportunity with incremented `attempt_count`, not two opportunities |
| T-FUNC-005 | `RR-FUNC-004` | Recovery window assignment | Every opportunity has non-null `recovery_window_expires_at` |
| T-FUNC-006 | `RR-FUNC-005` | Malformed signal quarantine | Zero opportunities from malformed signals; one quarantine log; one audit event |
| T-FUNC-007 | `RR-FUNC-007` | Addressability classification | Non-addressable opportunities excluded from candidate generation but counted in `M-01` |

### 2.2 UNDERSTAND — Diagnosis

| Test ID | Requirement | Description | Acceptance |
|---|---|---|---|
| T-FUNC-010 | `RR-FUNC-010` | Diagnosis completeness | 100% of acted opportunities have persisted `Diagnosis` with non-empty evidence refs |
| T-FUNC-011 | `RR-FUNC-011` | Taxonomy mapping | Pure function; unmapped inputs produce `UNCLASSIFIED`, never a new code |
| T-FUNC-012 | `RR-FUNC-012` | No "proven" language | Vocabulary scan: zero occurrences of "caused by", "proven", "root cause is" without confidence qualifier |
| T-FUNC-013 | `RR-FUNC-013` | Context completeness | Context object schema-validated; all fields present or explicitly null with reason |
| T-FUNC-014 | `RR-FUNC-014` | Fatigue state accuracy | Fatigue state matches independent recomputation from `Intervention` rows |
| T-FUNC-016 | `RR-FUNC-016` | LLM closed-set enforcement | Any LLM value outside the cause enum is rejected; deterministic fallback used |

### 2.3 SIMULATE — Candidates and pricing

| Test ID | Requirement | Description | Acceptance |
|---|---|---|---|
| T-FUNC-020 | `RR-FUNC-020` | Minimum candidate count | ≥ 3 `ActionCandidate` rows per addressable opportunity (≥ 2 real + `NO_ACTION`) |
| T-FUNC-021 | `RR-FUNC-021` | Class-aware candidate generation | Distinct candidate sets for `INSUFFICIENT_FUNDS` vs `CARD_EXPIRED` vs `NETWORK_TIMEOUT` |
| T-FUNC-023 | `RR-FUNC-023` | Prediction determinism | Identical inputs and `strategy_version` → identical `p(i,a)` and `p(i,∅)` |
| T-FUNC-024 | `RR-FUNC-024` | Template slot protection | Renderer rejects LLM output populating `*_paise` or `*_pct` slot |
| T-FUNC-025 | `RR-FUNC-025` | Negative uplift retained | Candidates with negative uplift exist in the store; never clipped |
| T-FUNC-026 | `RR-FUNC-026` | Cost recomputation | Cost recomputation from stored components reproduces stored total exactly |
| T-FUNC-027 | `RR-FUNC-027` | ENRV computation | Unit-tested against hand-computed fixtures; deterministic; integer paise |
| T-FUNC-028 | `RR-FUNC-028` | Uncertainty measure | Non-null on every candidate |

### 2.4 PRIORITIZE — Allocation

| Test ID | Requirement | Description | Acceptance |
|---|---|---|---|
| T-FUNC-030 | `RR-FUNC-030` | Multi-constraint allocation | Allocation report shows ≥ 4 constraints with at least one binding |
| T-FUNC-031 | `RR-FUNC-031` | One action per opportunity per cycle | No cycle has two selected candidates for the same `opportunity_id` |
| T-FUNC-032 | `RR-FUNC-032` | ENRV threshold enforcement | Zero selected candidates with `ENRV ≤ ε` |
| T-FUNC-033 | `RR-FUNC-033` | Decision completeness | Selected ∪ deferred ∪ rejected ∪ no-action = considered; sets are disjoint |
| T-FUNC-034 | `RR-FUNC-034` | Deterministic tie-breaking | Same-seed runs produce identical allocations |
| T-FUNC-037 | `RR-FUNC-037` | Pre-filter and post-gate | Both verdicts persisted; no action executes on pre-filter-only pass |
| T-FUNC-039 | `RR-FUNC-039` | Allocator timeout | Allocator returns a feasible solution within configured time limit |

### 2.5 Decision semantics

| Test ID | Requirement | Description | Acceptance |
|---|---|---|---|
| T-FUNC-040 | `RR-FUNC-040` | NO_ACTION validity | `NO_ACTION` share > 0 on benchmark; every instance has reason code |
| T-FUNC-041 | `RR-FUNC-041` | Deferral reconsidered | Deferred opportunities reappear in the next cycle's candidate pool |
| T-FUNC-042 | `RR-FUNC-042` | Decision persistence | Decision replay test reconstructs from stored rows alone |
| T-FUNC-043 | `RR-FUNC-043` | Stale-decision detection | State-changed opportunity → action not executed; opportunity re-enters pipeline |

### 2.6 Execution and verification

| Test ID | Requirement | Description | Acceptance |
|---|---|---|---|
| T-FUNC-050 | `RR-FUNC-050` | All 11 stopping rules | Coverage report: every rule fired at least once across benchmark |
| T-FUNC-051 | `RR-FUNC-051` | Pre-execution stopping | Mid-cycle success signal → no action executed on recovered opportunity |
| T-FUNC-060 | `RR-FUNC-060` | Idempotent execution | Duplicate attempt returns stored result; no new effect |
| T-FUNC-061 | `RR-FUNC-061` | Audit before adapter | Crash between audit-intent and adapter leaves auditable `EXECUTING` record |
| T-FUNC-062 | `RR-FUNC-062` | Two-phase reservation | Concurrency test: two cycles cannot over-consume a budget |
| T-FUNC-065 | `RR-FUNC-065` | Timeout reconciliation | `TIMEOUT_UNKNOWN` → no duplicate action; opportunity enters `RECONCILING` |
| T-FUNC-066 | `RR-FUNC-066` | Modified approval re-gating | Modified action is re-gated; gate-violating modification is denied |
| T-FUNC-070 | `RR-FUNC-070` | Partial recovery | Outcome records partial amount; opportunity state is re-priced |
| T-FUNC-073 | `RR-FUNC-073` | Legal state transitions | Illegal-transition attempt raises |

---

## 3. Integration tests

| Test ID | Description | Acceptance |
|---|---|---|
| T-INT-001 | Full cycle: signal → opportunity → diagnosis → candidates → allocation → gate → execution → outcome | All stages complete; opportunity reaches a terminal or resting state |
| T-INT-002 | Multi-cycle lifecycle: opportunity deferred in cycle 1 → re-priced and actioned in cycle 2 → outcome in cycle 3 | State transitions follow [34](34-state-machine.md) legal table |
| T-INT-003 | Full benchmark run at a single seed | `M-46 = PASS` (reproducible); `M-16 = 0`; metrics artefact generated |
| T-INT-004 | Benchmark comparison: REVIVE vs B0 | `M-10` computed as paired difference; artefact contains both policies |
| T-INT-005 | All seven UI screens render from a completed benchmark run | No screen errors; synthetic-data banners present |

---

## 4. Policy tests

One test per gate, plus cross-gate tests.

| Test ID | Gate | Description | Acceptance |
|---|---|---|---|
| T-POL-001 | G1 Consent | Customer with opt-out → action denied | `DENY`; audit event |
| T-POL-002 | G2 Window | Action outside communication window → deferred | `DEFER` |
| T-POL-003 | G3 Contact cap | Customer at per-day cap → denied | `DENY` |
| T-POL-004 | G4 Retry cap | Retry attempts exhausted → denied | `DENY` |
| T-POL-005 | G4 Cooldown | Retry inside cooldown → deferred | `DEFER` |
| T-POL-006 | G5 Ceiling | Incentive above ceiling → clamped or denied | `ALLOW_WITH_MODIFICATION` or `DENY` |
| T-POL-007 | G5 Re-price | Clamped incentive makes `ENRV ≤ ε` → becomes `NO_ACTION` | No execution |
| T-POL-008 | G6 Budget | Budget exhausted → deferred | `DEFER` |
| T-POL-009 | G7 Approval | High-value action → routed to approval | `REQUIRE_APPROVAL` |
| T-POL-010 | G8 Risk block | Risk flag → denied | `DENY` |
| T-POL-011 | G9 Duplicate | Idempotency key collision → denied | `DENY` |
| T-POL-012 | G9 Semantic | Same-family action to same customer in window → denied | `DENY` |
| T-POL-013 | G10 Stopping | Stopping rule satisfied → denied | `DENY` |
| T-POL-014 | G11 Channel | No valid channel → denied | `DENY` |
| T-POL-015 | G12 Amount | Amount exceeds sanity check → denied | `DENY` |
| T-POL-016 | All gates | Every gate appears in every applicable trace | No gate silently skipped |
| T-POL-017 | Verdict finality | Denied action → no re-allocation within cycle | `REJECTED` or `DEFERRED`; no runner-up promotion |
| T-POL-018 | Policy replay | Historical verdict reproduced from original pack | Identical verdict |

---

## 5. Safety tests

| Test ID | Description | Acceptance | Requirement |
|---|---|---|---|
| T-SAF-001 | No LLM output becomes a monetary value | Static check over all LLM call sites | `RR-GUARD-020` |
| T-SAF-002 | Single execution path to adapter | Adapter invocation outside the path raises | `RR-GUARD-021` |
| T-SAF-003 | Learning cannot write policy | Write attempt from C-21 to policy/budget/threshold raises | `RR-GUARD-022` |
| T-SAF-004 | Verdict finality | No code path re-evaluates a `DENY` into `ALLOW` | `RR-GUARD-023` |
| T-SAF-005 | Global halt | Halt engaged → no interventions; reservations released; audit recorded | `RR-GUARD-024` |
| T-SAF-006 | Step budget | Cycle exceeding step budget terminates cleanly | `RR-GUARD-025` |
| T-SAF-007 | Ledger invariant | `committed + reserved ≤ limit` after every transition | `RR-NFR-041` |
| T-SAF-008 | Audit store blocking | Unwritable audit store → execution halts | `RR-AUDIT-010` |
| T-SAF-009 | Privacy canary | Sentinel values in output → `M-57 > 0` → build failure | `RR-NFR-053` |

---

## 6. Failure tests

| Test ID | Description | Acceptance | Reference |
|---|---|---|---|
| T-FAIL-001 | Adapter timeout | `TIMEOUT_UNKNOWN` → `RECONCILING`; no further action | [23](23-failure-recovery.md) F-02 |
| T-FAIL-002 | LLM unavailable | Deterministic fallback activates; cycle completes | [23](23-failure-recovery.md) F-10 |
| T-FAIL-003 | Policy pack missing | All actions denied for cycle | [23](23-failure-recovery.md) F-12 |
| T-FAIL-004 | Predictor parameters corrupt | Entire cycle defers; no actions | [23](23-failure-recovery.md) F-09 |
| T-FAIL-005 | Ledger invariant violation | Cycle aborted; `M-22` incremented | [23](23-failure-recovery.md) F-07 |
| T-FAIL-006 | Crash between audit-intent and adapter | Auditable `EXECUTING` record; no duplicate effect on restart | `RR-FUNC-061` |
| T-FAIL-007 | Double reservation attempt | Second attempt refused; invariant holds | `RR-NFR-041` |
| T-FAIL-008 | Out-of-order signal | Quarantined or processed with reordering flag; no illegal transition | [23](23-failure-recovery.md) F-16 |
| T-FAIL-009 | Partial recovery | `V(i)` reduced; opportunity re-enters with smaller value | [23](23-failure-recovery.md) F-17 |

---

## 7. Evaluation tests

| Test ID | Description | Acceptance | Requirement |
|---|---|---|---|
| T-EVAL-001 | `M-10` paired computation | Computed as `NetRecovered(REVIVE, seed) − NetRecovered(B0, seed)` | `RR-METRIC-001` |
| T-EVAL-002 | Metric derivation reference | Every `MetricSnapshot` has a `derivation_ref` | `RR-METRIC-002` |
| T-EVAL-003 | `M-05` decomposition | `M-05 = M-06 + M-07 + M-09` asserted | `RR-METRIC-003` |
| T-EVAL-004 | Tier-0 independent computation | `M-16`, `M-17`, `M-18` computed by paths independent of runtime | `RR-METRIC-005` |
| T-EVAL-005 | Mandatory report sections | Report generation fails if limitations or adverse-findings empty | `RR-FUNC-091` |
| T-EVAL-006 | No undefined metric | Every metric in the artefact is defined in [37](37-metrics-dictionary.md) | `RR-METRIC-013` |
| T-EVAL-007 | Oracle-dependent labelling | Oracle-dependent metrics carry `D-E3` label | `RR-METRIC-012` |

---

## 8. Reproducibility tests

| Test ID | Description | Acceptance | Requirement |
|---|---|---|---|
| T-REPR-001 | Byte-identical artefacts at fixed seed | Two runs at the same seed produce identical metric output | `RR-NFR-020` |
| T-REPR-002 | No wall-clock dependency | Replacing system clock has no effect on output | `RR-NFR-022` |
| T-REPR-003 | No uncached LLM in evaluation | `M-47 = 0` during measured run | `RR-NFR-035` |
| T-REPR-004 | PRNG stream independence | Consuming extra draws in one stream does not shift another | [19 § 2.1](19-synthetic-dataset.md) |
| T-REPR-005 | Deterministic ULIDs | ULIDs from seeded PRNG are identical across runs | [README § C-4](README.md) |

---

## 9. State-machine tests

| Test ID | Description | Acceptance | Reference |
|---|---|---|---|
| T-SM-001 | Every legal transition has a test | Transition succeeds and state updates | [34 § 1.2](34-state-machine.md) |
| T-SM-002 | Every illegal transition has a test | Transition raises | [34 § 1.3](34-state-machine.md) |
| T-SM-003 | Exhaustive illegal-pair sweep | All `(state, state)` pairs minus legal table → all raise | [34 § 7](34-state-machine.md) |
| T-SM-004 | Every state reached in benchmark | Unreached states named and explained | [34 § 7](34-state-machine.md) |
| T-SM-005 | No transition out of terminal state | Except `STOPPED → PRICED` with external evidence | [34 § 7](34-state-machine.md) |
| T-SM-006 | Cross-machine invariants SM-1…SM-10 | All hold after every cycle | [34 § 6](34-state-machine.md) |
| T-SM-007 | State reconstruction from audit chain | Reconstructed state = live state (SM-9) | `RR-AUDIT-009` |

---

## 10. Adversarial tests

| Test ID | Description | Acceptance |
|---|---|---|
| T-ADV-001 | Discount above ceiling | G5 clamps or denies; no executed incentive exceeds ceiling |
| T-ADV-002 | Third customer contact (at cap) | G3 denies; no third contact executes |
| T-ADV-003 | Duplicate retry | G9 denies; no duplicate effect |
| T-ADV-004 | Budget race (concurrent reservations) | Invariant `committed + reserved ≤ limit` holds |
| T-ADV-005 | Stale opportunity (state changed mid-cycle) | Stale-decision detection fires; action not executed |
| T-ADV-006 | Conflicting policies (contradictory gate modifications) | Stricter clamp applies; contradiction logged as defect |
| T-ADV-007 | Invalid policy pack (missing fields) | All actions denied for cycle; defect logged |
| T-ADV-008 | No recovery path (no addressable action) | `NOT_ADDRESSABLE`; no candidate generation; counted in `M-01` |
| T-ADV-009 | Unavailable action (adapter unreachable) | Treated as `TIMEOUT_UNKNOWN` or pre-flight failure per [23](23-failure-recovery.md) |
| T-ADV-010 | Model uncertainty (wide sigma) | G7 triggers approval or action deferred; no reckless execution |
| T-ADV-011 | Prompt injection in failure reason | Zero out-of-taxonomy outputs; zero pricing impact |
| T-ADV-012 | Prompt injection in template variables | Zero monetary-slot violations; zero unauthorised offers |

---

## 11. Test count summary

| Category | Count |
|---|---|
| Functional | 37 |
| Integration | 5 |
| Policy | 18 |
| Safety | 9 |
| Failure | 9 |
| Evaluation | 7 |
| Reproducibility | 5 |
| State-machine | 7 |
| Adversarial | 12 |
| **Total** | **109** |
