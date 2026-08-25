# 38 · Traceability Matrix

A compact matrix view linking requirements → components → contracts → tests → demo beats.
The detailed trace chains are in [33-requirement-traceability.md](33-requirement-traceability.md).

---

## 1. Matrix

| Req ID | Name (short) | Priority | Component(s) | Data contract | Test(s) | Demo | Metric |
|---|---|---|---|---|---|---|---|
| `RR-FUNC-001` | Detection, 4 classes | MUST | C-02 | `RevenueOpportunity` | T-FUNC-001, 002 | Beat 2 | `M-01` |
| `RR-FUNC-002` | Value at risk | MUST | C-02 | `value_at_risk_paise` | T-FUNC-003 | Beat 3 | — |
| `RR-FUNC-003` | Deduplication | MUST | C-02 | Dedup key | T-FUNC-004 | — | `M-56` |
| `RR-FUNC-004` | Recovery window | MUST | C-02 | `recovery_window_expires_at` | T-FUNC-005 | — | — |
| `RR-FUNC-005` | Quarantine | MUST | C-01 | `SignalQuarantine` | T-FUNC-006 | — | `M-56` |
| `RR-FUNC-006` | Degradation | SHOULD | C-03 | Degradation flag | — | Beat 2* | — |
| `RR-FUNC-007` | Addressability | MUST | C-02 | `addressable` flag | T-FUNC-007 | — | `M-01` vs `M-02` |
| `RR-FUNC-008` | Ageing buckets | SHOULD | C-02 | Bucket field | — | Beat 2 | — |
| `RR-FUNC-010` | Diagnosis | MUST | C-05 | `Diagnosis` | T-FUNC-010 | Beat 3 | `M-27` |
| `RR-FUNC-011` | Taxonomy mapping | MUST | C-05 | Enum | T-FUNC-011 | — | — |
| `RR-FUNC-012` | No "proven" language | MUST | C-05 | Vocabulary | T-FUNC-012 | — | — |
| `RR-FUNC-013` | Context assembly | MUST | C-04 | `ContextObject` | T-FUNC-013 | Beat 3 | — |
| `RR-FUNC-014` | Fatigue state | MUST | C-04 | Fatigue in context | T-FUNC-014 | — | — |
| `RR-FUNC-016` | LLM closed set | SHOULD | C-05 | Schema enforcement | T-FUNC-016 | — | `M-50` |
| `RR-FUNC-020` | ≥ 3 candidates | MUST | C-06 | `ActionCandidate` | T-FUNC-020 | Beat 3 | — |
| `RR-FUNC-021` | Class-aware sets | MUST | C-06 | Catalogue rules | T-FUNC-021 | — | — |
| `RR-FUNC-023` | Prediction | MUST | C-07 | `p_action`, `p_natural`, `sigma` | T-FUNC-023 | Beat 3 | `M-24` |
| `RR-FUNC-024` | Template copy | SHOULD | C-10 | Template slots | T-FUNC-024 | — | — |
| `RR-FUNC-025` | Negative uplift | MUST | C-09 | `uplift` | T-FUNC-025 | Beat 3 | — |
| `RR-FUNC-026` | Cost computation | MUST | C-08 | Cost components | T-FUNC-026 | Beat 3 | `M-08` |
| `RR-FUNC-027` | ENRV computation | MUST | C-09 | `ENRV` (paise) | T-FUNC-027 | Beat 3 | — |
| `RR-FUNC-028` | Uncertainty | MUST | C-07 | `enrv_interval` | T-FUNC-028 | Beat 3 | — |
| `RR-FUNC-030` | Multi-constraint | MUST | C-12 | Allocation report | T-FUNC-030 | Beat 4 | `M-29`, `M-32` |
| `RR-FUNC-031` | 1 action/opp/cycle | MUST | C-12 | Decision | T-FUNC-031 | — | — |
| `RR-FUNC-032` | ENRV threshold | MUST | C-12 | `ε` | T-FUNC-032 | — | — |
| `RR-FUNC-033` | Decision complete | MUST | C-12 | Sets partition | T-FUNC-033 | Beat 4 | — |
| `RR-FUNC-034` | Tie-breaking | MUST | C-12 | Tie-break rule | T-FUNC-034 | — | `M-46` |
| `RR-FUNC-037` | Pre-filter + post-gate | MUST | C-11, C-13 | Verdicts | T-FUNC-037 | — | — |
| `RR-FUNC-039` | Allocator timeout | MUST | C-12 | Time budget | T-FUNC-039 | — | `M-33` |
| `RR-FUNC-040` | NO_ACTION valid | MUST | C-12 | Reason code | T-FUNC-040 | — | `M-15` |
| `RR-FUNC-041` | Deferral reconsidered | MUST | C-12, C-23 | Re-entry | T-FUNC-041 | — | — |
| `RR-FUNC-042` | Decision persistence | MUST | C-12 | Decision store | T-FUNC-042 | — | — |
| `RR-FUNC-043` | Stale-decision | MUST | C-17, C-23 | State comparison | T-FUNC-043 | — | — |
| `RR-FUNC-050` | 11 stopping rules | MUST | C-14 | Stop events | T-FUNC-050 | Beat 5 | Coverage |
| `RR-FUNC-051` | Pre-exec stopping | MUST | C-14 | Re-evaluation | T-FUNC-051 | — | `M-17` |
| `RR-FUNC-060` | Idempotent exec | MUST | C-17 | Idempotency key | T-FUNC-060 | — | — |
| `RR-FUNC-061` | Audit before effect | MUST | C-17, C-22 | Audit event | T-FUNC-061 | Beat 5 | `M-58` |
| `RR-FUNC-062` | Two-phase reservation | MUST | C-16 | ReservationHandle | T-FUNC-062 | — | — |
| `RR-FUNC-065` | Timeout handling | MUST | C-17 | Reconciliation | T-FUNC-065 | — | `M-35` |
| `RR-FUNC-066` | Approval re-gating | MUST | C-15, C-13 | Re-gate | T-FUNC-066 | Beat 5 | `M-18` |
| `RR-FUNC-070` | Partial recovery | MUST | C-19 | Outcome | T-FUNC-070 | — | `M-21` |
| `RR-FUNC-073` | Legal transitions | MUST | State machine | Transition guard | T-FUNC-073, T-SM-* | — | `M-22` |
| `RR-FUNC-090` | Metrics artefact | MUST | Report gen | MetricSnapshot | T-EVAL-001…007 | Beat 6 | All |
| `RR-FUNC-091` | Limitations section | MUST | Report gen | Mandatory section | T-EVAL-005 | Beat 7 | — |
| `RR-GUARD-001`…`012` | 12 gates | MUST | C-13 | Gate verdicts | T-POL-001…018 | Beat 5 | `M-14`…`M-18` |
| `RR-GUARD-020` | No LLM in money path | MUST | All | Static check | T-SAF-001 | — | — |
| `RR-GUARD-021` | Single execution path | MUST | C-17 | Code path | T-SAF-002 | — | — |
| `RR-GUARD-022` | Learning cannot write policy | MUST | C-21 | Data-access restriction | T-SAF-003 | — | — |
| `RR-GUARD-023` | Verdict finality | MUST | C-13 | No re-alloc after deny | T-SAF-004, T-POL-017 | — | — |
| `RR-AUDIT-001`…`010` | Audit properties | MUST | C-22 | AuditEvent | T-SAF-008 | Beat 5 | `M-58` |
| `RR-UI-001`…`008` | 7 screens + disclosure | MUST | UI | Screen specs | T-INT-005 | All beats | — |

---

## 2. Coverage summary

| Category | MUST count | With component | With test | With demo | With metric |
|---|---|---|---|---|---|
| `RR-FUNC-*` | 41 | 41 | 41 | 28 | 25 |
| `RR-GUARD-*` | 17 | 17 | 17 | 5 | 12 |
| `RR-UI-*` | 8 | 8 | 5 | 7 | — |
| `RR-AUDIT-*` | 10 | 10 | 6 | 3 | 4 |
| **Total** | **76** | **76** | **69** | **43** | **41** |

---

## 3. Gap list

| Req ID | Gap type | Description | Severity |
|---|---|---|---|
| `RR-FUNC-009` | No test | MAY-tier (subscription pre-failure) | LOW |
| `RR-FUNC-022` | No test | MAY-tier (voice action) | LOW |
| `RR-UI-001`…`007` | No unit test | Integration test covers screens; no per-screen unit test | LOW |

No MUST requirement has an unresolved gap.
