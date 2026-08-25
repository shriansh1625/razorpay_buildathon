# 05 · Functional Requirements

**Convention.** `MUST` = required for a passing build (Tier 1). `SHOULD` = Tier 2. `MAY` = Tier 3.
`WILL NOT` = explicitly excluded. Every `MUST` requires a test named after its ID
([30-test-plan.md](30-test-plan.md)).

**ID blocks.**

| Block | Range | Domain |
|---|---|---|
| `RR-FUNC-001`…`009` | SEE | Detection |
| `RR-FUNC-010`…`019` | UNDERSTAND | Diagnosis and context |
| `RR-FUNC-020`…`029` | SIMULATE | Candidates and pricing |
| `RR-FUNC-030`…`039` | PRIORITIZE | Allocation |
| `RR-FUNC-040`…`049` | Decision semantics | No-action, deferral, explanation |
| `RR-FUNC-050`…`059` | GUARD | Policy integration and stopping |
| `RR-FUNC-060`…`069` | ACT | Execution |
| `RR-FUNC-070`…`079` | VERIFY | Outcomes |
| `RR-FUNC-080`…`089` | LEARN | Model updating |
| `RR-FUNC-090`…`099` | Surface | Reporting and UI behaviour |
| `RR-GUARD-001`…`019` | Gates | One per gate |
| `RR-GUARD-020`…`029` | Architectural guardrails | Structural safety |
| `RR-METRIC-0nn` | Metrics | Maps 1:1 to `M-nn` in [37](37-metrics-dictionary.md) |
| `RR-AUDIT-001`…`010` | Audit | |
| `RR-BENCH-001`…`010` | Benchmark | |
| `RR-DATA-001`…`010` | Dataset | |
| `RR-UI-001`…`010` | Screens | |

---

## 1. SEE — Detection

| ID | Priority | Requirement | Acceptance |
|---|---|---|---|
| `RR-FUNC-001` | MUST | Detect revenue at risk across the four risk classes `PAYMENT_FAILURE`, `CHECKOUT_ABANDONMENT`, `SUBSCRIPTION_FAILURE`, `RECEIVABLE_OVERDUE`, emitting one `RevenueOpportunity` per distinct economic loss | For a generated batch, detection recall ≥ 0.99 per class against generator ground truth; precision ≥ 0.99 |
| `RR-FUNC-002` | MUST | Compute `value_at_risk_paise` for every opportunity by a deterministic rule specific to the risk class | Recomputation from the source record yields the identical integer |
| `RR-FUNC-003` | MUST | Deduplicate signals so that a single economic loss produces exactly one open opportunity, even when multiple signals arrive (e.g. failure → customer self-retry → second failure) | Duplicate-signal test produces one opportunity with `attempt_count` incremented, not two opportunities |
| `RR-FUNC-004` | MUST | Assign each opportunity a `recovery_window_expires_at` derived from its class and merchant policy | Every opportunity has a non-null window; expiry triggers `SR-06` (see [14](14-stopping-rules.md)) |
| `RR-FUNC-005` | MUST | Reject and quarantine malformed or implausible signals without creating an opportunity, and log the rejection | Malformed-signal test: zero opportunities created, one structured rejection log, one audit event |
| `RR-FUNC-006` | SHOULD | Detect cohort-level payment degradation (elevated failure rate for a method / issuer / BIN band over a rolling window) and attach a `degradation_flag` to affected opportunities | Injected degradation window is detected; flag present on ≥ 90% of affected opportunities inside the window |
| `RR-FUNC-007` | MUST | Classify every opportunity's `addressable` boolean — whether any action class is even applicable | Non-addressable opportunities (e.g. `RISK_BLOCKED`) are excluded from candidate generation but still counted in `M-01` |
| `RR-FUNC-008` | SHOULD | Support ageing buckets for receivables (`0-15`, `16-30`, `31-60`, `61-90`, `90+` days) as a first-class attribute | Bucket recomputed each cycle from virtual clock; drives candidate set and escalation |
| `RR-FUNC-009` | MAY | Detect subscription pre-failure risk (instrument expiring before next renewal) | Opportunity created before the failure occurs, with class `SUBSCRIPTION_FAILURE` and subtype `PRE_FAILURE` |

---

## 2. UNDERSTAND — Diagnosis and context

| ID | Priority | Requirement | Acceptance |
|---|---|---|---|
| `RR-FUNC-010` | MUST | Produce a `Diagnosis` for every opportunity entering candidate generation, containing a ranked list of ≥ 1 candidate causes, each with a confidence in `[0,1]` and ≥ 1 evidence reference | 100% of acted opportunities have a persisted diagnosis with non-empty evidence refs |
| `RR-FUNC-011` | MUST | Map raw failure reasons to the closed `FailureReason` taxonomy deterministically; route unmapped values to `UNCLASSIFIED` | Taxonomy mapping is a pure function; unmapped inputs never produce a new reason code |
| `RR-FUNC-012` | MUST | Never label a candidate cause as proven. All diagnosis output uses `candidate_cause` semantics with confidence | Vocabulary test over diagnosis fields and rendered text: no occurrence of "caused by", "proven", "root cause is" without a confidence qualifier |
| `RR-FUNC-013` | MUST | Assemble customer context: segment, tenure, historical spend band, prior recovery behaviour, engagement indicators | Context object schema-validated; all fields present or explicitly `null` with a reason |
| `RR-FUNC-014` | MUST | Assemble contact history and current fatigue state for the customer within the active window | Fatigue state matches an independent recomputation from `Intervention` rows |
| `RR-FUNC-015` | MUST | Assemble payment-instrument state (method, expiry status, prior success rate on this instrument) | Present for all `PAYMENT_FAILURE` and `SUBSCRIPTION_FAILURE` opportunities |
| `RR-FUNC-016` | SHOULD | Where the LLM contributes to diagnosis, it MUST return a ranked selection from the closed cause taxonomy plus evidence row IDs, never free-form causes | Schema-constrained output; any value outside the enum is rejected and the deterministic fallback is used |
| `RR-FUNC-017` | SHOULD | Attach a `timing_context` (merchant-local hour, day of month, business-day flag) used by the salary-cycle and quiet-hours logic | Present on every opportunity |

---

## 3. SIMULATE — Candidate generation and pricing

| ID | Priority | Requirement | Acceptance |
|---|---|---|---|
| `RR-FUNC-020` | MUST | Generate ≥ 2 non-null candidate actions plus `NO_ACTION` for every addressable opportunity | Count of `ActionCandidate` rows per addressable opportunity ≥ 3 |
| `RR-FUNC-021` | MUST | Candidate generation is class-aware and reason-aware: the candidate set differs by risk class and by `FailureReason` | Test asserts distinct candidate sets for `INSUFFICIENT_FUNDS` vs `CARD_EXPIRED` vs `NETWORK_TIMEOUT` |
| `RR-FUNC-022` | MAY | Support `VOICE_CALL` as a candidate action subject to a voice-minute capacity constraint | Voice appears in candidate sets only where channel-eligible; consumes `voice_minutes` resource |
| `RR-FUNC-023` | MUST | Estimate `p(i,a)` for every candidate and `p(i,∅)` for the no-action baseline, from a deterministic calibrated model | Model is a pure function of the feature vector and `strategy_version`; identical inputs give identical outputs |
| `RR-FUNC-024` | SHOULD | Generate message copy for communication actions from a template with a fixed variable set; the LLM may fill text slots but never numeric or monetary slots | Template renderer rejects any LLM output attempting to populate a `*_paise` or `*_pct` slot |
| `RR-FUNC-025` | MUST | Compute `uplift = p(i,a) − p(i,∅)` and retain it; negative uplift is retained, not clipped | Candidates with negative uplift exist in the store and are never selected unless `ENRV > ε`, which is impossible for negative uplift with non-negative costs |
| `RR-FUNC-026` | MUST | Compute action cost as unconditional direct cost `c(a)` plus success-conditional incentive cost `p(i,a)·d(i,a)` plus fatigue externality `λ_f·F(i,a)` | Cost recomputation from stored components reproduces the stored total exactly |
| `RR-FUNC-027` | MUST | Compute `ENRV(i,a)` per [README § C-5](README.md#c-5--the-frozen-objective), in integer paise | Deterministic; unit-tested against hand-computed fixtures |
| `RR-FUNC-028` | MUST | Attach an uncertainty measure to every `ENRV` (interval or variance) derived from predictor posterior spread | Non-null on every candidate; used by the approval-threshold gate |
| `RR-FUNC-029` | SHOULD | Record, per candidate, which evidence and features drove the estimate, sufficient to render a counterfactual comparison in the UI | Decision Detail screen renders without any LLM text |

---

## 4. PRIORITIZE — Allocation

| ID | Priority | Requirement | Acceptance |
|---|---|---|---|
| `RR-FUNC-030` | MUST | Allocate actions across the whole candidate opportunity portfolio in a single cycle-level solve, under **≥ 4 simultaneous resource constraints** | Allocation report lists all active constraints with consumption and at least one binding constraint on the benchmark batch |
| `RR-FUNC-031` | MUST | Enforce **at most one action per opportunity per cycle** | No cycle contains two selected candidates for the same `opportunity_id` |
| `RR-FUNC-032` | MUST | Only select candidates with `ENRV > ε` where `ε ≥ 0` is merchant policy | Zero selected candidates with `ENRV ≤ ε` |
| `RR-FUNC-033` | MUST | Produce, for every considered opportunity, one of: `SELECTED(action)`, `DEFERRED(reason)`, `REJECTED(reason)`, `NO_ACTION(reason)` — with no opportunity left unaccounted | Set-completeness test: selected ∪ deferred ∪ rejected ∪ no-action = considered, and the sets are disjoint |
| `RR-FUNC-034` | MUST | Break ties deterministically by `(−ENRV, −value_at_risk_paise, opportunity_id)` | Same-seed runs produce identical allocations |
| `RR-FUNC-035` | SHOULD | Report a shadow price (or a documented proxy) for each binding constraint | Present in the allocation artefact and rendered on the Recovery Allocation View |
| `RR-FUNC-036` | SHOULD | Reserve a capped share of budget for exploration, never exceeding `exploration_budget_share` | Exploration spend ≤ cap on every cycle; exploration-selected candidates are flagged |
| `RR-FUNC-037` | MUST | Run a policy pre-filter before allocation so that infeasible candidates never consume allocation capacity, and re-run full gates after allocation | Pre-filter and post-gate verdicts are both persisted; no action executes on a pre-filter-only pass |
| `RR-FUNC-038` | SHOULD | Provide a fallback greedy allocator that is used if the primary allocator fails or exceeds its time budget, with the fallback recorded on the decision | Fault-injection test forces fallback; run completes; `allocator_mode` = `FALLBACK_GREEDY` on affected decisions |
| `RR-FUNC-039` | MUST | Bound allocator runtime to a configured limit per cycle | Timeout test: allocator returns a feasible (possibly suboptimal) solution within the limit |

---

## 5. Decision semantics

| ID | Priority | Requirement | Acceptance |
|---|---|---|---|
| `RR-FUNC-040` | MUST | `NO_ACTION` is a valid, recorded, reasoned decision with a reason code from a closed set | `NO_ACTION` share > 0 on the benchmark batch; every instance has a reason code |
| `RR-FUNC-041` | MUST | Deferral carries a reason and the opportunity is reconsidered in a later cycle unless a stopping rule fires | Deferred opportunities reappear in the next cycle's candidate pool |
| `RR-FUNC-042` | MUST | Every `Decision` persists: the full candidate set considered, each candidate's `ENRV` components, the winner, the binding constraint (if any), the gate verdicts, and `strategy_version` | Decision replay test reconstructs the decision from stored rows alone |
| `RR-FUNC-043` | MUST | A decision is invalidated if the underlying opportunity state changed after the decision was computed (stale-decision detection) | Stale-decision test: action is not executed; opportunity re-enters the pipeline |
| `RR-FUNC-044` | SHOULD | Provide a natural-language explanation per decision, generated from the stored structure, clearly marked as generated | Explanation is absent-safe: deleting it breaks no screen (P-6) |

---

## 6. GUARD — Gates

Each gate is a separate requirement so that each has its own test. Full matrix and evaluation order:
[13-policy-and-guardrails.md](13-policy-and-guardrails.md).

| ID | Gate | Priority | Requirement | Verdicts |
|---|---|---|---|---|
| `RR-GUARD-001` | G1 Consent / opt-out | MUST | Deny any communication action to a customer with an active opt-out for that channel or globally | `DENY` |
| `RR-GUARD-002` | G2 Communication window | MUST | Deny communication actions outside the merchant-configured window in merchant-local time | `DEFER` |
| `RR-GUARD-003` | G3 Contact frequency cap | MUST | Deny when the customer's contact count in the rolling window would exceed `max_contacts_per_window` | `DENY` |
| `RR-GUARD-004` | G4 Retry cap and cooldown | MUST | Deny retry actions exceeding `max_retries_per_instrument` or inside `retry_cooldown_seconds` | `DENY` or `DEFER` |
| `RR-GUARD-005` | G5 Incentive ceiling | MUST | Clamp any incentive above `max_discount_pct` / `max_discount_paise` to the ceiling, or deny if the clamped value makes `ENRV ≤ ε` | `ALLOW_WITH_MODIFICATION` or `DENY` |
| `RR-GUARD-006` | G6 Budget / capacity | MUST | Deny or defer when the required resource units are unavailable; reservations are atomic | `DEFER` |
| `RR-GUARD-007` | G7 Approval threshold | MUST | Route to human approval when value, incentive, uncertainty, or action class crosses the configured threshold | `REQUIRE_APPROVAL` |
| `RR-GUARD-008` | G8 Risk block | MUST | Deny all actions where a risk flag is set (`RISK_BLOCKED` reason, disputed invoice, fraud hold) | `DENY` |
| `RR-GUARD-009` | G9 Duplicate suppression | MUST | Deny any action whose idempotency key already exists in a non-terminal or successful state | `DENY` |
| `RR-GUARD-010` | G10 Stopping rules | MUST | Deny when any of the 11 stopping rules in [14](14-stopping-rules.md) is satisfied | `DENY` |
| `RR-GUARD-011` | G11 Channel eligibility | MUST | Deny actions on channels the customer is not eligible for (no channel identifier, no channel opt-in where required) | `DENY` |
| `RR-GUARD-012` | G12 Amount sanity | MUST | Deny actions where the derived monetary amount is non-positive, exceeds the underlying value at risk, or fails a magnitude sanity check | `DENY` |

### 6.1 Architectural guardrails

| ID | Priority | Requirement | Acceptance |
|---|---|---|---|
| `RR-GUARD-020` | MUST | **No LLM output may become a number that moves money.** Every monetary value, probability, and allow/deny verdict is produced by deterministic code | Static check over LLM call sites; every output field is a closed-set label, a ranked enum list, an evidence reference, or non-numeric text |
| `RR-GUARD-021` | MUST | Exactly one code path reaches an execution adapter, and it passes through the policy engine | Attempting adapter invocation outside the path raises and fails a test |
| `RR-GUARD-022` | MUST | The Learning Engine has no write access to policy, budget, threshold, or limit tables | Write attempt raises; enforced at the data-access layer, not by convention |
| `RR-GUARD-023` | MUST | A gate verdict is final within its cycle; no component may override it | No code path re-evaluates a `DENY` into an `ALLOW` |
| `RR-GUARD-024` | MUST | A global `HALT` control suspends all execution within one cycle and is audited | Halt test: no interventions after halt; audit records the halt |
| `RR-GUARD-025` | MUST | Every cycle has a bounded step budget; no unbounded loops, no self-directed tool discovery | Cycle exceeding the step budget terminates cleanly with a recorded reason |
| `RR-GUARD-026` | MUST | Policy packs are versioned and immutable; a decision records the `policy_pack_version` it was evaluated against | Policy replay test reproduces the original verdict |
| `RR-GUARD-027` | SHOULD | Merchant-authored policy text (if natural-language policy interpretation is implemented) is compiled to deterministic rules in a reviewable, versioned form; the compiled rules — not the text — are enforced at runtime | Compiled rule set is diffable and testable; runtime never consults free text |

---

## 7. Stopping, execution, verification, learning

| ID | Priority | Requirement | Acceptance |
|---|---|---|---|
| `RR-FUNC-050` | MUST | Implement all 11 stopping rules `SR-01`…`SR-11` from [14](14-stopping-rules.md), each individually testable and each emitting a stop reason code | Coverage report shows every rule fired at least once across the benchmark; `M-17` = 0 |
| `RR-FUNC-051` | MUST | Evaluate stopping rules before every action, not only at cycle start | Stale-stop test: a rule satisfied mid-cycle prevents the action |
| `RR-FUNC-060` | MUST | Execute exactly the approved action, exactly once, with a mandatory idempotency key | Duplicate-execution test: second attempt returns the stored result and creates no new effect |
| `RR-FUNC-061` | MUST | Write the audit event **before** invoking the adapter, and the outcome event after | Crash-injection between the two leaves an auditable `EXECUTING` record, never a silent effect |
| `RR-FUNC-062` | MUST | Reserve resource units before execution (two-phase reserve → commit/release) | Concurrency test: two cycles cannot over-consume a budget |
| `RR-FUNC-063` | MUST | Provide adapters for payment-effect, message, voice, and human-task actions behind one interface, with a simulator implementation | Adapter interface has ≥ 1 simulator implementation; no real provider is contacted |
| `RR-FUNC-064` | MUST | Map every adapter result to a typed outcome (`SUCCESS`, `FAILED_RETRYABLE`, `FAILED_TERMINAL`, `TIMEOUT_UNKNOWN`, `REJECTED_BY_PROVIDER`) | No untyped adapter result reaches the state machine |
| `RR-FUNC-065` | MUST | Handle `TIMEOUT_UNKNOWN` without assuming either success or failure; reconcile before any further action on that opportunity | Timeout test: no duplicate action; opportunity enters `RECONCILING` |
| `RR-FUNC-066` | MUST | Provide a human-approval queue supporting approve / reject / modify; a modification re-enters all gates | Modified action is re-gated; an approved-then-modified action that now violates a gate is denied |
| `RR-FUNC-070` | MUST | Observe and record outcomes with `recovered_amount_paise`, supporting partial recovery | Partial-recovery test: outcome records the partial amount; opportunity state is `PARTIALLY_RECOVERED` |
| `RR-FUNC-071` | MUST | Classify attribution as `ATTRIBUTED`, `NATURAL`, or `AMBIGUOUS` per the rules in [21](21-evaluation.md) § 5 | Every outcome has an attribution class; the class is never used to inflate `M-10` |
| `RR-FUNC-072` | MUST | Reconcile actual intervention cost against estimated cost | `M-08` uses actual cost; variance is reported |
| `RR-FUNC-073` | MUST | Transition opportunity state only along legal transitions in [34](34-state-machine.md) | Illegal-transition attempt raises and is tested |
| `RR-FUNC-080` | SHOULD | Update predictor parameters from observed outcomes, versioned as a new `StrategyVersion`, with the prior version retained | Ablation test: learning-on vs learning-off both run; both results reported |
| `RR-FUNC-081` | SHOULD | Monitor calibration (`M-24`) and surface drift | Calibration reported per run; drift alert defined in [24](24-observability.md) |
| `RR-FUNC-082` | MUST | Every decision records the `strategy_version` used, enabling rollback and attribution of performance to a version | Version present on 100% of decisions |
| `RR-FUNC-083` | MUST | Learning never modifies a policy limit (see `RR-GUARD-022`) | Enforced structurally |

---

## 8. Surface — reporting and UI behaviour

| ID | Priority | Requirement | Screen |
|---|---|---|---|
| `RR-UI-001` | MUST | Executive Revenue Command Center: value at risk, expected recoverable, recovered, incremental vs baseline, active interventions, policy alerts | [25](25-ui-ux-spec.md) § 3 |
| `RR-UI-002` | MUST | Revenue Leakage Explorer: leakage by class and cause, drill-down to opportunities | § 4 |
| `RR-UI-003` | MUST | Recovery Opportunities: ranked list with `ENRV`, selected action, reason, policy state; includes the approval queue | § 5 |
| `RR-UI-004` | MUST | Decision Detail: context, full candidate set with counterfactual comparison, chosen action, gate verdicts, outcome | § 6 |
| `RR-UI-005` | MUST | Recovery Allocation View: resources, consumption, binding constraint, deferred and rejected cases | § 7 |
| `RR-UI-006` | MUST | Audit Trail: chronological events, decision trace, execution trace, chain verification status | § 8 |
| `RR-UI-007` | MUST | Benchmark / Evaluation Lab: baseline vs REVIVE across seeds, incremental recovery with CI, failures, cost, single-case replay | § 9 |
| `RR-UI-008` | MUST | Every screen states when a figure is derived from synthetic data | § 2.4 |
| `RR-FUNC-090` | MUST | Emit a machine-readable metrics artefact per benchmark run containing every metric in [37](37-metrics-dictionary.md) | Artefact schema-validated; no hand-entered values |
| `RR-FUNC-091` | MUST | Emit an evaluation report that includes a mandatory limitations section and a mandatory adverse-findings section | Report generation fails if either section is empty |

---

## 9. Capability × tier matrix

| Capability | MVP (T1) | Recommended (T2) | Optional (T3) | Future (T4) |
|---|---|---|---|---|
| Payment-failure detection | ● | | | |
| Checkout-abandonment detection | ● | | | |
| Subscription/mandate-failure detection | ● | | | |
| Receivable-overdue detection | ● | | | |
| Cohort payment-degradation signal | | ● | | |
| Subscription pre-failure detection | | | ● | |
| Deterministic reason taxonomy | ● | | | |
| Ranked candidate-cause diagnosis | ● | | | |
| LLM-assisted diagnosis (closed-set) | | ● | | |
| Recovery-probability model | ● | | | |
| Natural-recovery baseline model | ● | | | |
| Uplift + `ENRV` pricing | ● | | | |
| Uncertainty on `ENRV` | ● | | | |
| Multi-constraint allocator (≥ 4 constraints) | ● | | | |
| Shadow prices | | ● | | |
| Fallback greedy allocator | ● | | | |
| Exploration budget | | ● | | |
| All 12 gates | ● | | | |
| All 11 stopping rules | ● | | | |
| Human approval queue | ● | | | |
| Natural-language policy compilation | | | ● | |
| `NO_ACTION` / `RETRY_NOW` / `RETRY_SCHEDULED` | ● | | | |
| `PAYMENT_LINK` / `ALT_METHOD_PROMPT` | ● | | | |
| `MSG_EMAIL` / `MSG_SMS` | ● | | | |
| `MSG_WHATSAPP` | | ● | | |
| `INCENTIVE_DISCOUNT` (capped) | ● | | | |
| `DUNNING_SEQUENCE` | | ● | | |
| `MANDATE_RETRY_SEQUENCE` | | ● | | |
| `RECEIVABLE_REMINDER` | ● | | | |
| `PROMISE_TO_PAY_CAPTURE` | | ● | | |
| `ESCALATE_HUMAN` | ● | | | |
| `VOICE_CALL` (incl. Hinglish template) | | | ● | |
| LLM message copy generation | | ● | | |
| Idempotent bounded execution | ● | | | |
| Two-phase budget reservation | ● | | | |
| Typed adapter outcomes + reconciliation | ● | | | |
| Outcome attribution classification | ● | | | |
| Hash-chained audit trail | ● | | | |
| Synthetic generator with behavioural model | ● | | | |
| Baselines B0–B3 + oracle | ● | | | |
| Multi-seed evaluation with CI | ● | | | |
| Learning engine (posterior updating) | | ● | | |
| Calibration monitoring | | ● | | |
| 7 UI screens | ● | | | |
| Observability (metrics/logs/traces/alerts) | | ● | | |
| Multi-tenancy, multi-currency, scaling, real integration | | | | ● |

---

## 10. Requirement counts

| Block | MUST | SHOULD | MAY |
|---|---|---|---|
| `RR-FUNC-*` | 41 | 12 | 3 |
| `RR-GUARD-*` | 17 | 1 | 0 |
| `RR-UI-*` | 8 | 0 | 0 |

Metric, audit, benchmark, dataset and NFR requirements are enumerated in
[37](37-metrics-dictionary.md), [16](16-audit-trail.md), [20](20-benchmark.md),
[19](19-synthetic-dataset.md) and [06](06-nonfunctional-requirements.md) respectively, and are
consolidated in [38-traceability-matrix.md](38-traceability-matrix.md).
