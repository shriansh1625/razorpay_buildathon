# 07 · System Architecture

> **Implementation status (this submission).** Sections that name **Claude** or
> unimplemented LLM agents are **HISTORICAL / SPEC CONTEXT** (see [08](08-agent-architecture.md)).
> Shipped sandbox LLM, if any: Groq `openai/gpt-oss-120b` as a **diagnosis overlay**
> with no money-path authority. Official benchmark: `LLM_OFF`.
> Current architecture: [43-operating-architecture.md](43-operating-architecture.md).

---

## 1. Architectural style and the decision that drives it

PAYVANTA is a **cycle-based batch decision system**, not an event-driven per-event workflow engine.

This is the most consequential architectural choice in the package, so it is stated first.

### 1.1 Why not per-event

An event-driven design reacts to each signal as it arrives: payment fails → decide → act. It is the
obvious design, and it makes the product's differentiator **impossible to implement**:

| Problem | Why per-event cannot solve it |
|---|---|
| Allocation requires comparison | You cannot rank an opportunity against opportunities you have not seen yet |
| Budgets are shared | First-arrival consumes budget regardless of value; arrival order is uncorrelated with value |
| Constraints bind across cases | A per-event decision cannot know it is the marginal case that exhausts SMS capacity |
| Shadow prices are portfolio properties | There is no "price of capacity" without contention |
| The Track bar says "across a batch" | A batch number that is a sum of independent local decisions demonstrates nothing about allocation |

### 1.2 The cycle model

Ingestion is continuous. **Decisioning is periodic.** Signals accumulate into an opportunity pool;
at each cycle boundary the whole pool is priced and solved together.

```
signals ──▶ [ ingest, dedupe ] ──▶ Opportunity Pool  (continuous)
                                          │
                          ┌───────────────┴──────────────┐
                          │      RECOVERY CYCLE (tick)   │   (periodic)
                          │  price → allocate → gate →   │
                          │  execute → observe → learn   │
                          └──────────────────────────────┘
```

`PROPOSED` — cycle interval of **15 minutes of virtual time**, configurable. Rationale: short enough
that time-decaying opportunities (checkout abandonment) are not starved; long enough that a cycle
contains genuine contention. Both extremes are degenerate: a 1-second cycle degrades to per-event
decisioning; a 24-hour cycle wastes decayed opportunities.

### 1.3 Consequences of the cycle model

| Consequence | Handling |
|---|---|
| An urgent opportunity may wait up to one cycle | Accepted. Time decay is priced into `p(i,a)`, so the allocator naturally prefers fast-decaying cases. `OPTIONAL`: a fast-lane cycle for `CHECKOUT_ABANDONMENT` — parked in [41](41-future-ideas.md) |
| Opportunity state can change mid-cycle | Stale-decision detection, `RR-FUNC-043` |
| Budgets are per-cycle *and* per-period | Two-level ledger, § 6.3 |
| An opportunity can be reconsidered many times | Deferral is explicit and cheap; stopping rules terminate it, `RR-FUNC-041` |
| Determinism is achievable | A cycle is a pure function of `(pool state, policy pack, strategy version, clock, seed)` — this is what makes `RR-NFR-020` possible at all |

---

## 2. Component inventory

Every component belongs to exactly one loop phase. A component that fits none does not belong in the
system (principle P-9).

| # | Component | Phase | Kind | Requirement |
|---|---|---|---|---|
| C-01 | Signal Ingestor | SEE | Deterministic | `RR-FUNC-005` |
| C-02 | Revenue Sentinel | SEE | Deterministic | `RR-FUNC-001`…`004`, `007`, `008` |
| C-03 | Degradation Monitor | SEE | Deterministic (statistical) | `RR-FUNC-006` |
| C-04 | Context Enricher | UNDERSTAND | Deterministic | `RR-FUNC-013`…`015`, `017` |
| C-05 | Root Cause Analyst | UNDERSTAND | **HISTORICAL spec: LLM-assisted. SHIPPED: deterministic `rank_causes`; optional Groq overlay is not this module** | `RR-FUNC-010`…`012`, `016` |
| C-06 | Candidate Generator | SIMULATE | Deterministic (rule table) | `RR-FUNC-020`…`022` |
| C-07 | Recovery Predictor | SIMULATE | Deterministic (statistical model) | `RR-FUNC-023`, `028` |
| C-08 | Cost Model | SIMULATE | Deterministic | `RR-FUNC-026` |
| C-09 | Counterfactual Evaluator | SIMULATE | Deterministic | `RR-FUNC-025`, `027`, `029` |
| C-10 | Copy Composer | SIMULATE | **HISTORICAL SPECIFICATION — not implemented** | `RR-FUNC-024` |
| C-11 | Policy Pre-Filter | GUARD (early) | Deterministic | `RR-FUNC-037` |
| C-12 | **Recovery Allocator** | PRIORITIZE | Deterministic (optimisation) | `RR-FUNC-030`…`039` |
| C-13 | Policy / Guardrail Engine | GUARD | Deterministic | `RR-GUARD-001`…`012`, `026` |
| C-14 | Stopping-Rule Evaluator | GUARD | Deterministic | `RR-FUNC-050`, `051` |
| C-15 | Approval Queue | GUARD | Deterministic + human | `RR-GUARD-007`, `RR-FUNC-066` |
| C-16 | Resource Ledger | GUARD / ACT | Deterministic, transactional | `RR-GUARD-006`, `RR-FUNC-062` |
| C-17 | Execution Agent | ACT | Deterministic orchestration | `RR-FUNC-060`…`062`, `064`, `065` |
| C-18 | Action Adapters (payment / message / voice / human-task) | ACT | Interface + simulator | `RR-FUNC-063` |
| C-19 | Outcome Observer | VERIFY | Deterministic | `RR-FUNC-070`…`073` |
| C-20 | Attribution Classifier | VERIFY | Deterministic | `RR-FUNC-071` |
| C-21 | Learning Engine | LEARN | Deterministic (Bayesian updating) | `RR-FUNC-080`…`083` |
| C-22 | Audit Store | cross-cutting | Append-only, hash-chained | `RR-AUDIT-*` |
| C-23 | Cycle Orchestrator | cross-cutting | Deterministic | `RR-GUARD-025` |
| C-24 | Benchmark Harness | outside the loop | Deterministic | `RR-BENCH-*` |
| C-25 | Synthetic Generator + Hidden Outcome Oracle | outside the loop | Deterministic, seeded | `RR-DATA-*` |
| C-26 | Metrics / Report Builder | outside the loop | Deterministic | `RR-FUNC-090`, `091` |
| C-27 | API Layer | surface | — | `RR-API-*` |
| C-28 | Operator UI | surface | — | `RR-UI-*` |

**Only three components touch an LLM: C-05, C-10, and (optionally) the policy compiler in
`RR-GUARD-027`.** Everything that produces a number is deterministic. This is
[README § C-7](README.md#c-7--the-deterministic-authority-rule).

---

## 3. Data flow

```
                    ┌──────────────────────────────────────────────┐
                    │  C-25 Synthetic Generator (seeded)           │
                    │  ─ emits signals                             │
                    │  ─ holds HIDDEN outcome oracle ──────┐       │
                    └───────────────┬──────────────────────┼───────┘
                                    │ signals              │ (never readable
                                    ▼                      │  by the policy)
     ╔══════════════════════════════════════════════════╗  │
     ║ SEE                                              ║  │
     ║  C-01 Ingestor ─▶ C-02 Sentinel ─▶ Opportunity   ║  │
     ║                   ▲                    Pool      ║  │
     ║          C-03 Degradation Monitor                ║  │
     ╚═══════════════════════╤══════════════════════════╝  │
                             ▼                             │
     ╔══════════════════════════════════════════════════╗  │
     ║ UNDERSTAND                                       ║  │
     ║  C-04 Enricher ─▶ C-05 Root Cause Analyst  [LLM] ║  │
     ╚═══════════════════════╤══════════════════════════╝  │
                             ▼                             │
     ╔══════════════════════════════════════════════════╗  │
     ║ SIMULATE                                         ║  │
     ║  C-06 Candidates ─▶ C-07 Predictor               ║  │
     ║        │              (p(a), p(∅), σ)            ║  │
     ║        ▼                    │                    ║  │
     ║  C-10 Copy [LLM]      C-08 Cost Model            ║  │
     ║                             │                    ║  │
     ║                    C-09 Counterfactual Evaluator ║  │
     ║                        → ENRV per candidate      ║  │
     ╚═══════════════════════╤══════════════════════════╝  │
                             ▼                             │
                   C-11 Policy Pre-Filter                  │
                             ▼                             │
     ╔══════════════════════════════════════════════════╗  │
     ║ PRIORITIZE                                       ║  │
     ║  C-12 RECOVERY ALLOCATOR                         ║  │
     ║   ← C-16 Resource Ledger (capacities)            ║  │
     ║   → selected / deferred / rejected + shadow px   ║  │
     ╚═══════════════════════╤══════════════════════════╝  │
                             ▼                             │
     ╔══════════════════════════════════════════════════╗  │
     ║ GUARD  (authority layer — verdict is final)      ║  │
     ║  C-13 Gates G1…G12 ─┬─ C-14 Stopping Rules       ║  │
     ║                     ├─ C-15 Approval Queue ─▶ 👤 ║  │
     ║                     └─ C-16 Ledger RESERVE       ║  │
     ╚═══════════════════════╤══════════════════════════╝  │
                             ▼ (ALLOW only)                │
     ╔══════════════════════════════════════════════════╗  │
     ║ ACT                                              ║  │
     ║  C-22 audit BEFORE effect                        ║  │
     ║  C-17 Execution Agent ─▶ C-18 Adapters ──────────╫──┘
     ║  C-16 Ledger COMMIT / RELEASE                    ║   (adapter asks
     ╚═══════════════════════╤══════════════════════════╝    the oracle for
                             ▼                               the outcome)
     ╔══════════════════════════════════════════════════╗
     ║ VERIFY                                           ║
     ║  C-19 Outcome Observer ─▶ C-20 Attribution       ║
     ╚═══════════════════════╤══════════════════════════╝
                             ▼
     ╔══════════════════════════════════════════════════╗
     ║ LEARN                                            ║
     ║  C-21 Learning Engine ─▶ new StrategyVersion     ║
     ║  (writes predictor params ONLY — never policy)   ║
     ╚═══════════════════════╤══════════════════════════╝
                             │
              ┌──────────────┴───────────────┐
              ▼                              ▼
   C-26 Metrics / Report            C-27 API ─▶ C-28 UI

   C-22 Audit Store: written by every phase, read by nobody in the decision path
```

The critical structural facts visible in this diagram:

1. **The oracle is on the far right and connects only to the adapter.** The decision path never
   reads it. This is what makes the benchmark honest (`RR-BENCH-005`).
2. **GUARD sits between PRIORITIZE and ACT, and nothing bypasses it.** One path to the adapters
   (`RR-GUARD-021`).
3. **LEARN writes back only to the predictor**, never to the gate layer (`RR-GUARD-022`).
4. **Audit is written before the effect**, not after (`RR-FUNC-061`).

---

## 4. The recovery cycle, step by step

The orchestrator (C-23) executes exactly this sequence. Every step has a bounded step budget
(`RR-GUARD-025`).

| Step | Action | On failure |
|---|---|---|
| 1 | Open cycle: allocate `cycle_id`, snapshot virtual clock, snapshot policy pack + strategy version | Abort cycle; audit |
| 2 | Drain the signal queue: ingest, validate, dedupe, create/update opportunities | Quarantine bad signals; continue |
| 3 | Refresh derived state: ageing buckets, degradation flags, window expiry, fatigue state | Log; continue with stale flag |
| 4 | Apply stopping rules to the whole pool; close terminal opportunities | Fail closed: treat unknown as stop |
| 5 | Select the *considered set*: open, addressable, not stopped, within window | — |
| 6 | Enrich context for the considered set | Omit optional fields; mark degraded |
| 7 | Diagnose (deterministic map; LLM-assisted where enabled and cached) | Fall back to deterministic-only diagnosis |
| 8 | Generate candidates (always including `NO_ACTION`) | Fall back to the class-default candidate set |
| 9 | Predict `p(a)`, `p(∅)`, uncertainty | **Fail closed:** predictor unavailable → whole cycle defers, no actions |
| 10 | Price: cost model + `ENRV` + interval | Abort cycle; audit |
| 11 | Policy pre-filter: drop infeasible candidates | — |
| 12 | Allocate under all constraints (with time budget and greedy fallback) | Fallback greedy; record `allocator_mode` |
| 13 | For each selected candidate, run gates G1…G12 in order | Verdict is final |
| 14 | Route `REQUIRE_APPROVAL` to the queue; do not execute this cycle | — |
| 15 | `RESERVE` resources for `ALLOW` / `ALLOW_WITH_MODIFICATION` | Reservation failure → `DEFER` |
| 16 | Write audit event `INTERVENTION_INITIATED` | Abort this action; release reservation |
| 17 | Execute via adapter with idempotency key | Typed outcome; see [23](23-failure-recovery.md) |
| 18 | `COMMIT` or `RELEASE` reservation based on typed outcome | Reconciliation path for `TIMEOUT_UNKNOWN` |
| 19 | Write audit event `INTERVENTION_COMPLETED` with the typed result | Recovery scan on next cycle |
| 20 | Observe outcomes that matured this cycle; classify attribution | Mark `AMBIGUOUS` |
| 21 | Reconcile actual costs | Log variance |
| 22 | Learning update (if enabled) → new `StrategyVersion` | Skip; keep prior version |
| 23 | Emit per-cycle metrics; close cycle; audit `CYCLE_CLOSED` | — |

**Note on step 14.** Approval-required actions do not execute in the cycle that proposed them. This
is deliberate: it makes the human a real gate rather than a rubber stamp, and it means the
"compliant escalation" claim in [01-track-alignment.md](01-track-alignment.md) is structural. In the
benchmark, the approver is a **simulated policy** with a documented response model and latency —
labelled clearly, never presented as a real human decision (see [20](20-benchmark.md) § 7).

---

## 5. Technology (all `PROPOSED`; frozen by [ADR-010](31-decision-records.md) at build start)

| Layer | Proposal | Why |
|---|---|---|
| Language (engine) | Python 3.11+ | Fast to write; good numeric/optimisation ecosystem; the timebox dominates |
| Storage | SQLite for a run, schema portable to Postgres | Single-file, deterministic, zero setup, trivially reproducible; `OS-32` means no scaling need |
| Optimisation | Lagrangian-relaxation greedy as primary; exact ILP via an off-the-shelf solver as an `OPTIONAL` cross-check on small batches | See [10](10-recovery-allocation.md) § 5 |
| Statistics | Explicit logistic / Beta-Binomial models implemented directly | Interpretability and determinism (`OS-36`, [ADR-006](31-decision-records.md)) |
| API | HTTP/JSON | Neutral; contracts in [18](18-api-contracts.md) |
| UI | Single-page app reading precomputed artefacts | `RR-NFR-034` |
| LLM | **HISTORICAL SPEC:** Claude models were proposed. **SHIPPED:** engine `llm_used=False`; official `LLM_OFF`; optional sandbox Groq `openai/gpt-oss-120b` for diagnosis/proposal only (`revive/product/intelligence/`) | Overlay is not on the official experiment |

Storage note: monetary columns are `INTEGER` paise (`RR-NFR-001`). SQLite's lack of a decimal type is
irrelevant because PAYVANTA never uses decimals for money.

---

## 6. Cross-cutting mechanics

### 6.1 The virtual clock

One injected clock service. Benchmark mode advances it in fixed cycle increments; demo mode may
advance faster. **No component reads system time** (`RR-NFR-004`). Consequences: quiet hours,
salary-cycle effects, ageing buckets, cooldowns, and window expiry are all reproducible.

### 6.2 Seeded randomness

A single run seed derives independent PRNG streams by label:
`stream(seed, "generator")`, `stream(seed, "oracle")`, `stream(seed, "exploration")`,
`stream(seed, "approver")`. Streams are never shared, so adding a component does not perturb
another component's draws — which is what makes cross-run comparisons at a fixed seed meaningful
(`RR-NFR-005`).

### 6.3 The Resource Ledger (C-16)

Two-level, transactional, and the only component that may mutate capacity.

```
Budget/capacity per resource r:
   period_limit[r]      (e.g. per simulated day)
   cycle_limit[r]       (optional per-cycle cap)
   committed[r]         (consumed, terminal)
   reserved[r]          (held for in-flight actions)

Invariant (asserted continuously, RR-NFR-041):
   committed[r] + reserved[r] ≤ min(period_limit[r], cycle_limit[r] within cycle)
```

Two-phase protocol: `RESERVE` (atomic, before audit+execute) → `COMMIT` (terminal success or
terminal cost incurred) or `RELEASE` (action never took effect). This is what makes the budget
race condition in [23-failure-recovery.md](23-failure-recovery.md) `F-08` unreachable rather than
merely unlikely.

Resources tracked (`RR-FUNC-030` requires ≥ 4 binding; six are modelled):

| Resource | Unit | Consumed by |
|---|---|---|
| `incentive_budget` | paise | `INCENTIVE_DISCOUNT` (on success — reserved at expected value, committed at actual) |
| `message_capacity_<channel>` | messages | `MSG_*` actions |
| `voice_minutes` | minutes | `VOICE_CALL` |
| `retry_slots` | attempts | `RETRY_*`, `MANDATE_RETRY_SEQUENCE` |
| `human_review_slots` | slots | `REQUIRE_APPROVAL`, `ESCALATE_HUMAN` |
| `contact_allowance_<customer>` | contacts | every customer-facing action (per-customer, not merchant-pooled) |

### 6.4 Concurrency

`PROPOSED` — the cycle is single-threaded by default. Reason: determinism is worth more than
throughput at this scale (P-8 over P-9's efficiency reading). Where parallelism is introduced
(seeds in the multi-seed evaluation, or adapter I/O), it must be at a boundary where results are
merged in a deterministic order. The ledger is transactional regardless, because
`RR-NFR-040`/`041` must hold even for a future concurrent executor, and because the concurrency
tests are required either way.

### 6.5 Idempotency

```
idempotency_key = H( opportunity_id, action_code, attempt_seq, cycle_id )
```

Stored with its terminal result. G9 (`RR-GUARD-009`) denies any action whose key exists in a
successful or non-terminal state. Full semantics: [15-execution-model.md](15-execution-model.md).

---

## 7. The LLM boundary

Three rules, all structural:

1. **Schema-closed output.** Every LLM call declares an output schema over closed sets. Output that
   fails validation is discarded and the deterministic fallback is used (`RR-NFR-064`). There is no
   "parse the prose" path.
2. **No numbers.** No LLM output field is a probability, an amount, a percentage, or a verdict
   (`RR-GUARD-020`). Diagnosis returns *ranked cause labels with a coarse confidence band* that the
   deterministic layer maps to numeric priors — the mapping table is versioned and reviewable.
3. **Cached and seed-keyed.** Cache key `(prompt_version, model_id, seed, opportunity_id, input_hash)`.
   A benchmark run makes **zero** uncached calls (`RR-NFR-035`), which is the only way an LLM can
   coexist with `RR-NFR-020`. Cache population is a separate, explicitly non-benchmark step.

Untrusted text (failure-reason strings, invoice descriptions, merchant notes) is delimited, escaped,
and labelled as data before entering a prompt (`RR-NFR-063`). See
[22-security-and-privacy.md § 4](22-security-and-privacy.md).

---

## 8. Deployment view

```
┌─────────────────────────────── single machine ───────────────────────────────┐
│                                                                             │
│  revive-engine (one process)          artefacts/                            │
│   ├── C-01…C-23  cycle pipeline        ├── run_<bench_id>/metrics.json      │
│   ├── C-25 generator + oracle          ├── run_<bench_id>/audit_chain.jsonl │
│   └── C-24 benchmark harness           ├── run_<bench_id>/decisions.jsonl   │
│                                        └── run_<bench_id>/report.md          │
│  revive.db (SQLite)                                                          │
│                                        llm_cache/  (populated out of band)   │
│  revive-api  ─────────▶  revive-ui (SPA, reads artefacts + API)              │
└─────────────────────────────────────────────────────────────────────────────┘
   No network required for the benchmark path (RR-NFR-092).
```

---

## 9. What is deliberately absent

Stating absences prevents the implementation phase from inventing them and prevents the submission
from implying them.

| Absent | Why |
|---|---|
| Message broker / queue infrastructure | The signal queue is a table; cycle-based decisioning needs no broker (`OS-32`) |
| Microservices | One process; module boundaries are enforced by tests and permissions, not by network hops |
| Cache layer (beyond the LLM cache) | No latency requirement to justify it |
| Real payment / comms providers | `OS-02`; adapters + simulator only ([36](36-razorpay-integration-assumptions.md)) |
| Feature store | The feature vector is assembled per cycle from the relational store; ~500–5,000 rows |
| Model registry | `StrategyVersion` rows are the registry |
| Container orchestration | Runs on a laptop (`RR-NFR-092`) |
| Retry middleware / circuit breakers as infrastructure | Failure handling is explicit per action type in [23](23-failure-recovery.md), because financial actions must not be blind-retried |

---

## 10. Architectural invariants

Each is testable, and each maps to a named test. Violating any of these is a build failure, not a
finding.

| # | Invariant | Enforced by |
|---|---|---|
| AI-1 | Exactly one code path reaches an adapter, and it traverses C-13 | `RR-GUARD-021` |
| AI-2 | No LLM output becomes a number that moves money | `RR-GUARD-020` |
| AI-3 | `committed + reserved ≤ limit` for every resource, always | `RR-NFR-041` |
| AI-4 | An audit event precedes every irreversible effect | `RR-FUNC-061` |
| AI-5 | The audit log is append-only and its chain verifies | `RR-NFR-050`, `051` |
| AI-6 | The decision path never reads the hidden oracle | `RR-BENCH-005` |
| AI-7 | The Learning Engine cannot write policy, budget, or threshold tables | `RR-GUARD-022` |
| AI-8 | Every opportunity in a cycle's considered set receives exactly one of SELECTED / DEFERRED / REJECTED / NO_ACTION | `RR-FUNC-033` |
| AI-9 | State changes follow the legal-transition table only | `RR-FUNC-073` |
| AI-10 | Same seed ⇒ byte-identical metric artefact | `RR-NFR-020` |
| AI-11 | A gate verdict is never overridden within its cycle | `RR-GUARD-023` |
| AI-12 | Every cycle terminates within its step budget | `RR-GUARD-025` |

---

## 11. Product, engine, official evidence

Three layers. Mixing them is a documentation defect.

```
PAYVANTA Sandbox  ──▶  demonstrates the recovery workflow
        │
        │  same engine
        ▼
Official benchmark  ──▶  evaluates the engine (20 × 6 × 5 = 600 cells)
        │
        ▼
artefacts/benchmark/official-cloud-final/  ──▶  frozen, read-only
```

The Control Room is not a benchmark cell. M-10 of the experiment is
`NetRecovered(policy) − NetRecovered(B0)` on the same seed and profile, defined
in [21-evaluation.md](21-evaluation.md) § 2.1. Design: [20-benchmark.md](20-benchmark.md).
Evidence journey, hashes, and evaluator map: [42-official-benchmark.md](42-official-benchmark.md).

The product never writes the official tree. Parallel dispatch, checkpoint
reconciliation, ABUNDANT forensics, and the metrics-tail rescue are
infrastructure around the engine; they are not M-10 improvements.
