# 32 · Implementation Contract

This is the most important handoff document. The implementation agent (Cursor or developer) is
bound by the rules in this document. Read this before writing a single line of code.

---

## 1. Binding rules

The implementation phase **MUST**:

| # | Rule | Rationale |
|---|---|---|
| IC-01 | **Read all documentation before implementation.** Start with this document, then [00](00-project-charter.md), then [03](03-scope-boundaries.md), then [05](05-functional-requirements.md), then the reading order in [README](README.md) | Prevents scope misunderstanding and redundant design |
| IC-02 | **Treat `docs/` as the source of truth.** Where code and docs disagree, docs win unless a deviation is recorded in [31](31-decision-records.md) | Prevents silent spec drift |
| IC-03 | **Follow Track 03.** Every feature must pass the scope firewall in [03](03-scope-boundaries.md). Features outside the track are removed, not deferred | Prevents disqualification |
| IC-04 | **Never invent APIs.** The Razorpay API surface is `UNVERIFIED` ([36-razorpay-integration-assumptions.md](36-razorpay-integration-assumptions.md)). Use only the adapter interface. Do not fabricate endpoint names, parameters, or behaviours | Prevents false claims |
| IC-05 | **Never fabricate benchmark results.** Every number in every artefact, report, and UI must come from a generated artefact. No hand-entered values. No illustrative round numbers in production artefacts | Prevents dishonesty |
| IC-06 | **Never remove guardrails.** All 12 gates (`RR-GUARD-001`…`012`) and all architectural guardrails (`RR-GUARD-020`…`027`) must be implemented. Removing a gate "for simplicity" is a build failure | Prevents safety regression |
| IC-07 | **Never bypass policy checks.** The policy engine (C-13) is the sole authority. No code path may execute an action without a complete gate trace. `M-16 = 0` is mandatory | Prevents guardrail circumvention |
| IC-08 | **Never remove auditability.** The audit trail ([16](16-audit-trail.md)) is the system of record. Every material action has an audit event. If the audit store is unwritable, execution halts (`RR-AUDIT-010`) | Prevents untrackable actions |
| IC-09 | **Never silently alter scope.** Adding a feature, domain, risk class, or action code not in [03](03-scope-boundaries.md) requires a scope-firewall pass and an ADR. Removing a MUST requirement requires an ADR with explicit product-owner approval | Prevents scope creep |
| IC-10 | **Never replace measurable recovery with cosmetic metrics.** The primary metric is `M-10` (incremental net recovered revenue), computed by paired policy comparison. Substituting gross recovery, action count, or model confidence is a defect | Prevents metric gaming |
| IC-11 | **Preserve reproducibility.** Two runs at the same seed must produce byte-identical metric output (`M-46`). No wall-clock dependency, no unseeded randomness, no unsorted collections | Prevents invalid benchmarks |
| IC-12 | **Prefer the smallest implementation that satisfies the specification.** Do not add microservices, additional agents, or architectural layers not specified in [07](07-system-architecture.md) or [08](08-agent-architecture.md). Complexity is a cost, not a feature | Prevents over-engineering |
| IC-13 | **Record deviations.** Any departure from the specification — however small — is recorded as an ADR in [31](31-decision-records.md) with rationale. Silent divergence is the single failure mode this contract most wants to prevent | Prevents hidden drift |
| IC-14 | **Ask for clarification when specifications genuinely conflict.** Log the question in [40-open-questions.md](40-open-questions.md). Do not guess, do not silently interpret, do not work around | Prevents misinterpretation |
| IC-15 | **Never use an LLM where deterministic logic is required for financial safety.** `RR-GUARD-020` is the boundary. Every probability, monetary value, and allow/deny verdict must come from deterministic code. LLMs produce labels, rankings, evidence references, and text | Prevents financial safety violations |
| IC-16 | **Never perform real-money actions in the hackathon environment unless explicitly authorised and sandboxed.** All adapters are simulators. No real payment rail, no real messaging provider, no real voice call | Prevents real-world financial actions |

---

## 2. Implementation priority

### P0 — Mandatory

Required for a valid submission. Build all of these first.

| Area | P0 items |
|---|---|
| **Detection** | All four risk classes (`RR-FUNC-001`); value-at-risk computation (`002`); deduplication (`003`); recovery window (`004`); malformed-signal quarantine (`005`); addressability (`007`) |
| **Diagnosis** | Deterministic taxonomy mapping (`011`); ranked candidate causes with confidence (`010`); context assembly (`013`…`015`); no "proven" language (`012`) |
| **Candidates** | ≥ 3 per opportunity including `NO_ACTION` (`020`); class-aware sets (`021`); deterministic `p(i,a)` and `p(i,∅)` (`023`); uplift retained including negative (`025`); cost computation (`026`); ENRV computation (`027`); uncertainty measure (`028`) |
| **Allocation** | Multi-constraint solve under ≥ 4 constraints (`030`); one action per opportunity per cycle (`031`); ENRV threshold (`032`); decision completeness (`033`); deterministic ties (`034`); pre-filter and post-gate (`037`); allocator timeout (`039`) |
| **Decision semantics** | `NO_ACTION` valid (`040`); deferral reconsidered (`041`); decision persistence (`042`); stale-decision detection (`043`) |
| **Gates** | All 12 gates (`RR-GUARD-001`…`012`); architectural guardrails (`020`…`027`) |
| **Stopping** | All 11 rules (`050`); pre-execution re-evaluation (`051`) |
| **Execution** | Idempotent execution (`060`); audit before effect (`061`); two-phase reservation (`062`); adapter interface with simulators (`063`); typed outcomes (`064`); timeout handling (`065`) |
| **Approval** | Human approval queue (`066`) |
| **Verification** | Outcome observation with partial recovery (`070`); attribution (`071`); cost reconciliation (`072`); legal state transitions (`073`) |
| **Strategy** | Version recording on every decision (`082`); learning cannot modify policy (`083`) |
| **Audit** | Hash-chained, append-only, PII-free audit trail (`RR-AUDIT-001`…`010`) |
| **Benchmark** | Synthetic generator (`RR-DATA-001`); baselines B0–B3 + oracle (`RR-BENCH-001`…`006`); multi-seed evaluation with CI (`RR-BENCH-007`) |
| **Evaluation** | Metrics artefact (`RR-FUNC-090`); mandatory limitations section (`091`) |
| **UI** | All 7 screens (`RR-UI-001`…`008`) |
| **Reproducibility** | Deterministic from seed (`RR-NFR-020`) |

### P1 — High value

Should be built if time permits after all P0 are stable.

| Area | P1 items |
|---|---|
| **Detection** | Cohort degradation (`006`); ageing buckets (`008`) |
| **Diagnosis** | LLM-assisted diagnosis (`016`); timing context (`017`) |
| **Candidates** | Template copy with LLM (`024`); counterfactual rendering (`029`) |
| **Allocation** | Shadow prices (`035`); exploration budget (`036`); fallback allocator (`038`) |
| **Decision** | Natural-language explanation (`044`) |
| **Learning** | Posterior updating (`080`); calibration monitoring (`081`) |
| **Actions** | `MSG_WHATSAPP`, `DUNNING_SEQUENCE`, `MANDATE_RETRY_SEQUENCE`, `PROMISE_TO_PAY_CAPTURE` |
| **Observability** | Full observability stack ([24](24-observability.md)) |
| **Baselines** | B4–B6 |

### P2 — Enhancement

Build only after all P0 requirements are stable and tested.

| Area | P2 items |
|---|---|
| **Detection** | Subscription pre-failure (`009`) |
| **Actions** | `VOICE_CALL` with Hinglish template (`022`) |
| **Policy** | Natural-language policy compilation (`RR-GUARD-027`) |
| **Advanced** | LLM message copy generation beyond templates |

---

## 3. Implementation sequence

| Phase | What | Dependency |
|---|---|---|
| 1 | Data model ([17](17-data-model.md)) + state machines ([34](34-state-machine.md)) | None |
| 2 | Synthetic generator ([19](19-synthetic-dataset.md)) | Phase 1 |
| 3 | SEE: Signal ingestor + Revenue Sentinel | Phase 1 |
| 4 | UNDERSTAND: Context Enricher + Root Cause Analyst (deterministic path first) | Phase 3 |
| 5 | SIMULATE: Candidate Generator + Recovery Predictor + Cost Model + Counterfactual Evaluator | Phase 4 |
| 6 | Policy engine + Stopping-rule evaluator | Phase 1 |
| 7 | PRIORITIZE: Recovery Allocator (greedy first, then Lagrangian) | Phase 5 + 6 |
| 8 | ACT: Resource Ledger + Execution Agent + Adapters (simulators) | Phase 6 + 7 |
| 9 | VERIFY: Outcome Observer + Attribution Classifier | Phase 8 |
| 10 | Audit store + hash chain | Phase 1 (parallel with phases 3–9) |
| 11 | Benchmark harness + baselines | Phase 2 + 9 + 10 |
| 12 | Evaluation report generator | Phase 11 |
| 13 | LEARN: Learning Engine (P1) | Phase 9 |
| 14 | UI: 7 screens | Phase 11 + 12 |
| 15 | Demo preparation | Phase 14 |

---

## 4. Quality gates

Before declaring any phase complete:

| Gate | Check |
|---|---|
| **Tests pass** | All tests in [30](30-test-plan.md) relevant to the phase pass |
| **Metrics emit** | Relevant `MetricSnapshot` rows are generated with `derivation_ref` |
| **Audit events** | Every material action in the phase produces an audit event |
| **Reproducibility** | Phase output is deterministic at a fixed seed |
| **No silent deviation** | Any departure from spec is recorded as an ADR |
| **State machine** | Every state transition in the phase is in the legal-transition table |

---

## 5. Escalation protocol

| Situation | Action |
|---|---|
| Specification is ambiguous | Log in [40-open-questions.md](40-open-questions.md); ask the product owner; do not guess |
| Specification is wrong | Propose an ADR in [31](31-decision-records.md); do not silently work around |
| A MUST requirement cannot be met | Record the gap; propose a mitigation; do not hide the gap |
| A P0 item is blocked | Escalate; do not skip to P1/P2 items |
| Implementation discovers a new risk | Add to [28-risk-register.md](28-risk-register.md) |
| Implementation discovers a documentation inconsistency | Add to [36-documentation-consistency-check.md](36-documentation-consistency-check.md) |

---

## 6. What this contract does NOT permit

The implementation agent may NOT:

- Add features not in scope without a scope-firewall pass
- Remove a MUST requirement without product-owner approval
- Replace `M-10` with a different primary metric
- Use an LLM for pricing, allocation, policy enforcement, or allow/deny verdicts
- Create real adapters that contact real payment rails or messaging providers
- Generate or display fabricated performance numbers
- Commit API keys or secrets to version control
- Skip the audit trail for any financial action
- Suppress the limitations section of the evaluation report
- Silently change the meaning of a metric defined in [37](37-metrics-dictionary.md)
- Introduce nondeterminism (unseeded randomness, wall-clock dependency, unsorted collections)
- Create additional agents without passing the anti-proliferation test ([08 § 1](08-agent-architecture.md))

---

## 7. Definition of done

The build is done when the checklist in [00-project-charter.md § 9](00-project-charter.md) is
satisfied. Restated here for emphasis:

1. `docs/` is unchanged in intent — every deviation is recorded in [31](31-decision-records.md)
2. Every `MUST` requirement has a passing test named after its requirement ID
3. The benchmark runs from a single documented command, at a documented seed
4. The benchmark runs over ≥ 20 seeds with paired comparison and CI
5. `M-16 = 0` on every seed
6. The audit hash chain verifies for every run
7. The evaluation report includes limitations and adverse findings
8. No fabricated number appears anywhere
9. The demo executes end to end without manual intervention
10. The traceability matrix has no unresolved `GAP — MUST BE RESOLVED` rows
