# 33 · Requirement Traceability

A complete traceability framework linking every requirement to its design decision, architecture
component, data contract, test, demo evidence, and evaluation evidence. Orphaned requirements
are named, not hidden.

> **Note.** This document provides the detailed traceability framework. The matrix view is in
> [38-traceability-matrix.md](38-traceability-matrix.md). The judging-criteria mapping is in
> [27-judging-criteria-mapping.md](27-judging-criteria-mapping.md). This document is the
> authoritative source for requirement IDs and their full trace chains.

---

## 1. ID scheme

| Block | Range | Domain | Source |
|---|---|---|---|
| `RR-FUNC-001`…`009` | SEE — Detection | [05 § 1](05-functional-requirements.md) | Detection |
| `RR-FUNC-010`…`019` | UNDERSTAND — Diagnosis | [05 § 2](05-functional-requirements.md) | Diagnosis |
| `RR-FUNC-020`…`029` | SIMULATE — Candidates | [05 § 3](05-functional-requirements.md) | Pricing |
| `RR-FUNC-030`…`039` | PRIORITIZE — Allocation | [05 § 4](05-functional-requirements.md) | Allocation |
| `RR-FUNC-040`…`049` | Decision semantics | [05 § 5](05-functional-requirements.md) | Decision |
| `RR-FUNC-050`…`059` | GUARD — Stopping | [05 § 7](05-functional-requirements.md) | Stopping |
| `RR-FUNC-060`…`069` | ACT — Execution | [05 § 7](05-functional-requirements.md) | Execution |
| `RR-FUNC-070`…`079` | VERIFY — Outcomes | [05 § 7](05-functional-requirements.md) | Verification |
| `RR-FUNC-080`…`089` | LEARN | [05 § 7](05-functional-requirements.md) | Learning |
| `RR-FUNC-090`…`099` | Surface | [05 § 8](05-functional-requirements.md) | Reporting |
| `RR-GUARD-001`…`012` | Gates | [05 § 6](05-functional-requirements.md) | Each gate |
| `RR-GUARD-020`…`027` | Architectural guardrails | [05 § 6.1](05-functional-requirements.md) | Structure |
| `RR-METRIC-001`…`016` | Metrics | [37](37-metrics-dictionary.md) | Measurement |
| `RR-AUDIT-001`…`010` | Audit | [16](16-audit-trail.md) | Auditability |
| `RR-BENCH-001`…`010` | Benchmark | [20](20-benchmark.md) | Evaluation |
| `RR-DATA-001`…`010` | Dataset | [19](19-synthetic-dataset.md) | Data |
| `RR-UI-001`…`008` | Screens | [05 § 8](05-functional-requirements.md) | UI |
| `RR-NFR-*` | Non-functional | [06](06-nonfunctional-requirements.md) | NFR |

---

## 2. P0 requirement trace chains

### 2.1 SEE — Detection

| Req ID | Design decision | Component | Data contract | Test | Demo evidence | Eval evidence |
|---|---|---|---|---|---|---|
| `RR-FUNC-001` | ADR-001 (batch) | C-02 Revenue Sentinel | `RevenueOpportunity`, `Signal` ([17](17-data-model.md)) | T-FUNC-001, T-FUNC-002 | Beat 2: leakage by class | `M-01`, detection recall |
| `RR-FUNC-002` | — | C-02 | `value_at_risk_paise` on `RevenueOpportunity` | T-FUNC-003 | Beat 3: value shown | Exact-match rate |
| `RR-FUNC-003` | — | C-02 | Dedup key on `Signal` | T-FUNC-004 | — | `M-56` signal hygiene |
| `RR-FUNC-004` | — | C-02 | `recovery_window_expires_at` on `RevenueOpportunity` | T-FUNC-005 | — | Coverage |
| `RR-FUNC-005` | — | C-01 | `SignalQuarantine` | T-FUNC-006 | — | `M-56` |
| `RR-FUNC-007` | — | C-02 | `addressable` boolean | T-FUNC-007 | — | `M-01` vs `M-02` |

### 2.2 UNDERSTAND — Diagnosis

| Req ID | Design decision | Component | Data contract | Test | Demo evidence | Eval evidence |
|---|---|---|---|---|---|---|
| `RR-FUNC-010` | ADR-003 | C-05 Root Cause Analyst | `Diagnosis` ([17](17-data-model.md)) | T-FUNC-010 | Beat 3: causes shown | `M-27` |
| `RR-FUNC-011` | ADR-004 | C-05 (deterministic path) | `FailureReason` enum | T-FUNC-011 | — | — |
| `RR-FUNC-012` | — | C-05 | Vocabulary constraint | T-FUNC-012 | — | — |
| `RR-FUNC-013` | — | C-04 | `ContextObject` | T-FUNC-013 | Beat 3: context shown | Field completeness |
| `RR-FUNC-014` | — | C-04 | Fatigue state in context | T-FUNC-014 | — | Fatigue agreement |
| `RR-FUNC-015` | — | C-04 | Instrument state in context | — | — | — |

### 2.3 SIMULATE — Candidates and pricing

| Req ID | Design decision | Component | Data contract | Test | Demo evidence | Eval evidence |
|---|---|---|---|---|---|---|
| `RR-FUNC-020` | — | C-06 | `ActionCandidate` | T-FUNC-020 | Beat 3: candidates shown | ≥ 3 per opp |
| `RR-FUNC-021` | — | C-06 | Action catalogue rules | T-FUNC-021 | — | Distinct sets |
| `RR-FUNC-023` | ADR-006 | C-07 | `p_action`, `p_natural`, `sigma` | T-FUNC-023 | Beat 3: probabilities shown | `M-24` calibration |
| `RR-FUNC-025` | ADR-002 | C-09 | `uplift` field | T-FUNC-025 | Beat 3: uplift shown | Negative uplift exists |
| `RR-FUNC-026` | — | C-08 | Cost components | T-FUNC-026 | Beat 3: cost breakdown | `M-08` |
| `RR-FUNC-027` | ADR-002 | C-09 | `ENRV` (paise) | T-FUNC-027 | Beat 3: ENRV shown | — |
| `RR-FUNC-028` | — | C-07 | `enrv_interval` | T-FUNC-028 | Beat 3: uncertainty shown | — |

### 2.4 PRIORITIZE — Allocation

| Req ID | Design decision | Component | Data contract | Test | Demo evidence | Eval evidence |
|---|---|---|---|---|---|---|
| `RR-FUNC-030` | ADR-007 | C-12 | `Decision`, allocation report | T-FUNC-030 | Beat 4: constraints shown | `M-29`, `M-32` |
| `RR-FUNC-031` | — | C-12 | One `Decision` per opp per cycle | T-FUNC-031 | — | — |
| `RR-FUNC-032` | ADR-002 | C-12 | ENRV threshold `ε` | T-FUNC-032 | — | — |
| `RR-FUNC-033` | — | C-12 | Decision completeness | T-FUNC-033 | Beat 4: all outcomes shown | Set completeness |
| `RR-FUNC-034` | — | C-12 | Tie-breaking rule | T-FUNC-034 | — | `M-46` |
| `RR-FUNC-037` | ADR-009 | C-11, C-13 | Pre-filter + post-gate | T-FUNC-037 | — | — |
| `RR-FUNC-039` | ADR-007 | C-12 | Time budget | T-FUNC-039 | — | `M-33` |

### 2.5 Gates

| Req ID | Design decision | Component | Data contract | Test | Demo evidence | Eval evidence |
|---|---|---|---|---|---|---|
| `RR-GUARD-001` | ADR-009 | C-13 | Gate verdict | T-POL-001 | Beat 5: gate denial | `M-14`, `M-16` |
| `RR-GUARD-002` | ADR-009 | C-13 | Gate verdict | T-POL-002 | — | `M-14` |
| `RR-GUARD-003` | ADR-009 | C-13 | Gate verdict | T-POL-003 | Beat 5: contact cap | `M-14` |
| `RR-GUARD-004` | ADR-009 | C-13 | Gate verdict | T-POL-004, T-POL-005 | — | `M-14` |
| `RR-GUARD-005` | ADR-009 | C-13 | Gate verdict (modification) | T-POL-006, T-POL-007 | — | `M-14` |
| `RR-GUARD-006` | ADR-009 | C-13, C-16 | Reservation | T-POL-008 | Beat 4: budget exhaustion | `M-29` |
| `RR-GUARD-007` | — | C-13, C-15 | Approval request | T-POL-009 | Beat 5: approval queue | `M-37`, `M-18` |
| `RR-GUARD-008` | — | C-13 | Risk flag | T-POL-010 | — | `M-14` |
| `RR-GUARD-009` | — | C-13 | Idempotency key | T-POL-011, T-POL-012 | — | `M-14` |
| `RR-GUARD-010` | ADR-010 | C-14 | Stop reason | T-POL-013 | Beat 5: stopping rule | `M-17` |
| `RR-GUARD-011` | — | C-13 | Channel state | T-POL-014 | — | `M-14` |
| `RR-GUARD-012` | — | C-13 | Amount checks | T-POL-015 | — | `M-14` |
| `RR-GUARD-020` | ADR-004 | All | Static check | T-SAF-001 | — | — |
| `RR-GUARD-021` | — | C-17 | Single path | T-SAF-002 | — | — |
| `RR-GUARD-022` | — | C-21 | Data-access restriction | T-SAF-003 | — | — |
| `RR-GUARD-023` | ADR-009 | C-13 | Verdict finality | T-SAF-004, T-POL-017 | — | — |
| `RR-GUARD-024` | — | Operator | HALT | T-SAF-005 | — | `M-44` |

### 2.6 Execution and verification

| Req ID | Design decision | Component | Data contract | Test | Demo evidence | Eval evidence |
|---|---|---|---|---|---|---|
| `RR-FUNC-050` | ADR-010 | C-14 | Stop events | T-FUNC-050 | Beat 5: rule fires | Coverage table |
| `RR-FUNC-051` | ADR-010 | C-14 | Pre-execution check | T-FUNC-051 | — | `M-17` |
| `RR-FUNC-060` | — | C-17 | Idempotency key | T-FUNC-060 | — | — |
| `RR-FUNC-061` | ADR-005 | C-17, C-22 | Audit before effect | T-FUNC-061 | Beat 5: audit trail | `M-58` |
| `RR-FUNC-062` | — | C-16 | Reservation handle | T-FUNC-062 | — | — |
| `RR-FUNC-063` | — | C-18 | Adapter interface | — | — | `M-43` |
| `RR-FUNC-064` | — | C-18 | Typed outcome | — | — | `M-43` |
| `RR-FUNC-065` | — | C-17 | `RECONCILING` state | T-FUNC-065 | — | `M-35` |
| `RR-FUNC-066` | — | C-15 | Re-gating | T-FUNC-066 | Beat 5: approval | `M-18` |
| `RR-FUNC-070` | — | C-19 | `Outcome` with partial | T-FUNC-070 | — | `M-21` |
| `RR-FUNC-071` | — | C-20 | Attribution class | — | — | `M-06`, `M-07`, `M-09` |
| `RR-FUNC-073` | — | State machine | Legal transitions | T-FUNC-073, T-SM-* | — | `M-22` |

### 2.7 Audit

| Req ID | Design decision | Component | Data contract | Test | Demo evidence | Eval evidence |
|---|---|---|---|---|---|---|
| `RR-AUDIT-001` | ADR-005 | C-22 | Append-only store | T-SAF-008 | Beat 5: audit trail | `M-58` |
| `RR-AUDIT-002` | ADR-005 | C-22 | Hash chain | — | Beat 5: chain verification | `M-58` |
| `RR-AUDIT-005` | ADR-005 | C-22 | Correlation IDs | — | Beat 5: trace | — |
| `RR-AUDIT-010` | ADR-005 | C-22 | Blocking rule | T-SAF-008 | — | — |

---

## 3. Orphan check

### 3.1 Requirements without tests

All MUST requirements have at least one test in [30](30-test-plan.md). SHOULD and MAY requirements
without explicit tests are listed:

| Req ID | Priority | Reason no test | Mitigation |
|---|---|---|---|
| `RR-FUNC-006` | SHOULD | Degradation detection coverage | Covered by integration test if C-03 is built |
| `RR-FUNC-008` | SHOULD | Ageing bucket recomputation | Covered by integration test if built |
| `RR-FUNC-009` | MAY | Subscription pre-failure | Not built unless P2 |
| `RR-FUNC-022` | MAY | Voice action | Not built unless P2 |
| `RR-FUNC-024` | SHOULD | LLM copy generation | Covered by T-FUNC-024 (slot protection) |

### 3.2 Tests without requirements

None. Every test in [30](30-test-plan.md) references a requirement ID.

### 3.3 Components without requirements

None. Every component in [08](08-agent-architecture.md) maps to at least one `RR-FUNC-*` or
`RR-GUARD-*` requirement.

---

## 4. Coverage summary

| Category | Total | With test | With demo evidence | With eval evidence |
|---|---|---|---|---|
| `RR-FUNC-*` MUST | 41 | 41 | 28 | 35 |
| `RR-GUARD-*` MUST | 17 | 17 | 5 | 12 |
| `RR-UI-*` MUST | 8 | 5 (integration) | 7 | — |
| `RR-AUDIT-*` | 10 | 6 | 3 | 4 |
| `RR-BENCH-*` | 10 | 4 (integration) | 2 | 10 |
| `RR-METRIC-*` | 16 | 7 | — | 16 |
