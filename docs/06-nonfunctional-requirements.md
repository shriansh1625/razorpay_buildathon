# 06 · Non-Functional Requirements

All NFRs are scoped to a hackathon prototype running the benchmark on a single machine. Targets are
`PROPOSED` unless stated otherwise, and several are deliberately modest — see
[29-tradeoffs.md](29-tradeoffs.md) § 6.

---

## 1. Correctness and determinism

| ID | Priority | Requirement | Verification |
|---|---|---|---|
| `RR-NFR-001` | MUST | All monetary arithmetic uses integer paise. No float appears in any computation whose result is stored as money or compared against a budget | Static check: no float→money conversions; type-level separation of `Paise` from `float` |
| `RR-NFR-002` | MUST | Probability arithmetic uses floats; conversion to paise happens exactly once, at persistence, using banker's rounding | Unit test on the rounding boundary; conservation test on cost decomposition |
| `RR-NFR-003` | MUST | Every decision function is pure with respect to `(inputs, strategy_version, policy_pack_version, seed)` | Property test: repeated invocation with identical inputs yields identical output |
| `RR-NFR-004` | MUST | No wall-clock dependence in the benchmark path. All time comes from an injected clock | Static check for direct time calls in decision/benchmark modules |
| `RR-NFR-005` | MUST | No unseeded randomness anywhere in the benchmark path. All PRNGs are constructed from the run seed and a component-specific stream label | Static check; determinism test `RR-NFR-020` |
| `RR-NFR-006` | MUST | Iteration over collections that affects output is order-stable (explicit sort keys, not dict/hash order) | Determinism test across two processes |
| `RR-NFR-020` | MUST | **Two benchmark runs at the same seed produce byte-identical metric artefacts.** Build-blocking | CI-equivalent test comparing artefact hashes |
| `RR-NFR-021` | MUST | Different seeds produce different batches (the generator is genuinely seeded, not fixed) | Distinctness test across 5 seeds |

---

## 2. Performance

Targets sized so the demo and the multi-seed evaluation are practical. `PROPOSED`.

| ID | Priority | Requirement | Target |
|---|---|---|---|
| `RR-NFR-030` | MUST | A single recovery cycle over the benchmark batch completes within a bounded time | ≤ 10 s per cycle for 500 open opportunities on a laptop-class machine |
| `RR-NFR-031` | MUST | The allocator has a hard time budget and returns a feasible solution when it expires | ≤ 3 s; on expiry, fall back to greedy (`RR-FUNC-038`) |
| `RR-NFR-032` | MUST | A full benchmark run (one seed, all baselines + REVIVE) completes within a bounded time | ≤ 3 min per seed |
| `RR-NFR-033` | MUST | The ≥ 20-seed evaluation completes within a single working session | ≤ 60 min total, parallelisable across seeds |
| `RR-NFR-034` | SHOULD | UI screens render from precomputed artefacts, not by recomputing decisions | Any screen loads in ≤ 1 s from the artefact store |
| `RR-NFR-035` | SHOULD | LLM calls, where used, are cached by `(prompt_version, seed, opportunity_id)`; a benchmark run makes zero uncached calls | Cache-miss counter is 0 during benchmark; asserted |

---

## 3. Reliability and safety

| ID | Priority | Requirement | Verification |
|---|---|---|---|
| `RR-NFR-040` | MUST | No single action can execute twice for the same idempotency key, under concurrency | Concurrency test with parallel executors |
| `RR-NFR-041` | MUST | Budget over-consumption is impossible: reservations are atomic and released on failure | Property test: sum of committed + reserved ≤ budget, invariant across injected failures |
| `RR-NFR-042` | MUST | A crash at any point in the execution sequence leaves the system in a recoverable, auditable state — never with an unrecorded side effect | Crash-injection tests at each step boundary ([23](23-failure-recovery.md) § 4) |
| `RR-NFR-043` | MUST | All state transitions are validated against the legal-transition table; illegal transitions raise | [34](34-state-machine.md) transition test suite |
| `RR-NFR-044` | MUST | Every failure mode in [23](23-failure-recovery.md) has a defined containment that does not include "proceed anyway" | Review checklist; fail-closed principle P-11 |
| `RR-NFR-045` | SHOULD | The system tolerates out-of-order and late-arriving signals without corrupting opportunity state | Out-of-order test with shuffled signal delivery |
| `RR-NFR-046` | MUST | The global `HALT` takes effect within one cycle and is durable across restart | Halt-persistence test |

---

## 4. Auditability

| ID | Priority | Requirement | Verification |
|---|---|---|---|
| `RR-NFR-050` | MUST | The audit log is append-only at the data-access layer; no update or delete path exists | Write-path inspection; attempted update raises |
| `RR-NFR-051` | MUST | The audit chain is verifiable: each event stores `prev_hash` and the chain validates for a whole run | Chain-verification test on every benchmark run |
| `RR-NFR-052` | MUST | Every executed intervention is reachable from an audit event to its decision, candidate set, diagnosis, and opportunity | Reachability test over the benchmark run |
| `RR-NFR-053` | MUST | No field on the never-log list ([16](16-audit-trail.md) § 6) appears anywhere in the audit store or application logs | Log-scanning test with synthetic canary values |

---

## 5. Security and privacy

Detailed threat model: [22-security-and-privacy.md](22-security-and-privacy.md).

| ID | Priority | Requirement | Verification |
|---|---|---|---|
| `RR-NFR-060` | MUST | No real credentials exist in the repository, environment files, or artefacts | Secret-scan of the tree |
| `RR-NFR-061` | MUST | Customer identifiers in stores and logs are pseudonymous; no raw contact details are persisted beyond the adapter boundary | Schema review; log scan |
| `RR-NFR-062` | MUST | LLM prompts contain no field on the LLM deny-list; enforced by a serialiser | Serialiser test with canary values |
| `RR-NFR-063` | MUST | All external/untrusted text (failure reason strings, merchant notes, invoice descriptions) is treated as data, never as instructions, and is delimited and escaped before entering a prompt | Prompt-injection test corpus ([22](22-security-and-privacy.md) § 4) |
| `RR-NFR-064` | MUST | LLM outputs are schema-validated against a closed set before use; validation failure falls back to deterministic default, never to raw output | Malformed-output test |
| `RR-NFR-065` | SHOULD | Role separation exists for operator vs reviewer vs admin actions in the UI | Role simulation test; `HACKATHON-SCOPE` — no real identity provider (`OS-33`) |

---

## 6. Observability

| ID | Priority | Requirement |
|---|---|---|
| `RR-NFR-070` | MUST | All logs are structured (one JSON object per line) with a stable field set |
| `RR-NFR-071` | MUST | Every log line in a decision or execution path carries the correlation quad `(cycle_id, opportunity_id, decision_id, intervention_id)` where applicable |
| `RR-NFR-072` | MUST | Every cap, truncation, sample, or top-N is logged with what was dropped and why (principle P-15) |
| `RR-NFR-073` | SHOULD | The metric set in [24](24-observability.md) § 2 is emitted per cycle and per run |
| `RR-NFR-074` | SHOULD | The alert conditions in [24](24-observability.md) § 5 are implemented as assertions on the run artefact |

---

## 7. Maintainability and testability

| ID | Priority | Requirement | Verification |
|---|---|---|---|
| `RR-NFR-080` | MUST | Every module maps to a row in [08-agent-architecture.md](08-agent-architecture.md); every table maps to a row in [17-data-model.md](17-data-model.md) | Structural review |
| `RR-NFR-081` | MUST | Every `MUST` requirement has at least one test whose name contains the requirement ID | Test-name coverage report |
| `RR-NFR-082` | MUST | The pricing layer, the allocator, and the gate engine are each independently testable with fixtures, without the LLM, adapters, or the generator | Unit-test suites exist for all three in isolation |
| `RR-NFR-083` | MUST | The simulator adapter and any future real adapter satisfy the same interface and the same test suite | Shared adapter contract tests |
| `RR-NFR-084` | SHOULD | Configuration (budgets, limits, thresholds, `ε`, `λ_f`, horizons) is declarative and versioned, not hard-coded | Config file present; policy pack versioned |
| `RR-NFR-085` | MUST | No test is skipped or deleted to make a suite pass; a failing test is a finding, not an obstacle | Review; skip-count assertion |

---

## 8. Reproducibility and portability

| ID | Priority | Requirement |
|---|---|---|
| `RR-NFR-090` | MUST | The benchmark runs from a single documented command with an explicit seed argument |
| `RR-NFR-091` | MUST | All seeds, config versions, policy pack version, strategy version, and generator version are recorded in the run artefact |
| `RR-NFR-092` | MUST | The benchmark requires no network access and no external service |
| `RR-NFR-093` | MUST | Dependency versions are pinned |
| `RR-NFR-094` | SHOULD | The benchmark runs on a clean machine following only the documented steps, with no undocumented prerequisites |

---

## 9. Usability

| ID | Priority | Requirement |
|---|---|---|
| `RR-NFR-100` | MUST | Every screen distinguishes an estimate from an observed outcome, visually and in wording |
| `RR-NFR-101` | MUST | Every monetary figure states its unit and whether it is gross, net, or incremental |
| `RR-NFR-102` | MUST | Every screen showing synthetic-derived figures carries a synthetic-data marker |
| `RR-NFR-103` | SHOULD | A reviewer can complete all eight tasks in [04-principles-and-non-goals.md § 5](04-principles-and-non-goals.md) in under 15 minutes without guidance |
| `RR-NFR-104` | SHOULD | No screen requires horizontal scrolling at 1440 px width |

---

## 10. Explicitly relaxed NFRs (`HACKATHON-SCOPE`)

Stating these prevents the implementation phase from spending time on them, and prevents the
submission from implying they were met.

| Area | Relaxed to | Rationale |
|---|---|---|
| Availability / uptime | None. Single-process, run-on-demand | The benchmark is a batch job, not a service |
| Horizontal scalability | None. Single machine | `OS-32` |
| Throughput at production volume | Not evaluated | The decision problem is demonstrated at 500–5,000 opportunities |
| Disaster recovery / backup | None beyond a file on disk | No real data |
| Multi-region, latency SLOs | None | Not applicable |
| Real authentication / SSO | Role simulation only | `OS-33` |
| Encryption at rest | Not implemented | No real PII or secrets exist to protect; stated rather than implied |
| Penetration testing | Not performed | The threat model in [22](22-security-and-privacy.md) is a design artefact, not an assessment |
| Accessibility conformance | Sensible defaults only, not audited | Timebox |
| Localisation | Language tags on templates only | `OS-37` |

**Reporting rule.** None of the relaxed items may be described in the submission as "handled",
"designed for", or "production-grade". They are relaxed, and the submission says so.
