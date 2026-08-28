# 08 · Agent and Module Architecture

> **Implementation status (this submission).** The table below is the original
> specification. It is **not** a description of the running binary.
>
> Shipped diagnosis always records `llm_used=False` (`revive/recovery/diagnosis/diagnose.py`;
> `allow_llm=False`). Official cells use `llm_mode=LLM_OFF`. **Copy Composer (C-10) is not
> implemented.** There is no chatbot and no live model call.
>
> What shipped: deterministic diagnosis, deterministic ENRV and allocation,
> deterministic guardrails, bounded execution, measurement, audit.
> See [why-ai.md](why-ai.md) and [43-operating-architecture.md](43-operating-architecture.md).

---

## 1. The anti-proliferation rule

Multi-agent architectures are easy to draw and hard to justify. PAYVANTA applies a hard test before
any module is granted "agent" status:

> A module exists only if it has (a) a distinct responsibility, (b) a typed output another module
> consumes, (c) an evaluation criterion that can fail independently, and (d) a requirement ID it
> serves.

A module that fails any of the four is merged into its caller.

Furthermore, **most modules in PAYVANTA are not agents.** They are deterministic functions. The word
"agent" is reserved for components that (i) invoke an LLM, or (ii) orchestrate a bounded sequence of
tool calls. By that definition PAYVANTA has **three agents and eighteen deterministic modules**, and
that ratio is intentional — it is the direct consequence of
[README § C-7](README.md#c-7--the-deterministic-authority-rule).

| Kind | Count | Members |
|---|---|---|
| **Agent (LLM-invoking)** | 2 | Root Cause Analyst (C-05), Copy Composer (C-10) |
| **Agent (orchestrating)** | 1 | Cycle Orchestrator (C-23) |
| **Deterministic module** | 18 | Everything else in [07 § 2](07-system-architecture.md) |
| **Human-in-the-loop** | 1 | Approver (via C-15) |

Rejected agents, and why — recorded so they are not reinvented:

| Rejected "agent" | Verdict |
|---|---|
| "Negotiation Agent" that decides discount levels | Violates `RR-GUARD-020`. Discount is a priced action variable, clamped by G5. |
| "Strategy Agent" that picks the overall recovery approach | That *is* the allocator. An LLM wrapper on top adds nondeterminism and no information. |
| "Critic Agent" that reviews the other agents | The deterministic policy engine already constrains them, verifiably. A critic adds cost and a second unverifiable opinion. |
| "Planner Agent" that decomposes the cycle | The cycle is a fixed 23-step sequence ([07 § 4](07-system-architecture.md)). Planning it is not a decision problem. |
| "Customer Persona Agent" that predicts behaviour | That is the Recovery Predictor, and it must be calibrated and deterministic. |
| "Router Agent" for channel selection | Channel is an action attribute chosen by `ENRV` and gated by G11. |

---

## 2. Module specification format

Every module below is specified against the same eleven fields. Where a field says **none**, that is
a positive assertion, not an omission.

---

## 3. SEE modules

### C-01 · Signal Ingestor

| Field | Value |
|---|---|
| **Phase** | SEE |
| **Kind** | Deterministic |
| **Responsibility** | Accept raw signals, validate against schema, normalise, quarantine the invalid |
| **Inputs** | Raw signal records (payment event, checkout event, subscription event, invoice event) |
| **Outputs** | Validated `Signal` rows; quarantine rows with a rejection reason |
| **Tools allowed** | Read signal source; write `Signal`, `SignalQuarantine`, `AuditEvent` |
| **Tools forbidden** | Any adapter; any LLM; write to `RevenueOpportunity` |
| **Decision authority** | Accept / quarantine only. No economic judgement. |
| **Failure modes** | Malformed payload; unknown event type; impossible values (negative amount, future timestamp beyond clock) |
| **Escalation** | Quarantine + structured log + audit; never fabricate a default |
| **Observability** | `signals_ingested`, `signals_quarantined{reason}` |
| **Evaluation** | Quarantine precision/recall against generator-injected malformed records |
| **Requirements** | `RR-FUNC-005` |

### C-02 · Revenue Sentinel

| Field | Value |
|---|---|
| **Phase** | SEE |
| **Kind** | Deterministic |
| **Responsibility** | Turn signals into typed `RevenueOpportunity` records with a value at risk, deduplicated to one per economic loss |
| **Inputs** | `Signal` rows; existing open opportunities; policy pack (window lengths) |
| **Outputs** | `RevenueOpportunity` (created or updated), with `risk_class`, `value_at_risk_paise`, `addressable`, `recovery_window_expires_at`, `ageing_bucket` |
| **Tools allowed** | Read `Signal`, `Transaction`, `Subscription`, `CheckoutSession`, `Invoice`, `Customer`; write `RevenueOpportunity`, `AuditEvent` |
| **Tools forbidden** | Any adapter; any LLM; any write to candidates, decisions, or ledger |
| **Decision authority** | Detection and valuation only. **Cannot decide any action.** |
| **Failure modes** | Duplicate opportunity creation; missed detection; wrong value at risk; wrong class |
| **Escalation** | On ambiguous class, prefer the class with the more conservative action set and flag `class_ambiguous` |
| **Observability** | `opportunities_detected{class}`, `dedupe_merges`, `value_at_risk_total` |
| **Evaluation** | Recall ≥ 0.99, precision ≥ 0.99 per class vs generator ground truth; value-at-risk exact-match rate |
| **Requirements** | `RR-FUNC-001`…`004`, `007`, `008` |

### C-03 · Degradation Monitor

| Field | Value |
|---|---|
| **Phase** | SEE |
| **Kind** | Deterministic (statistical) |
| **Responsibility** | Detect elevated failure rates for a method / issuer / BIN-band cohort over a rolling window and flag affected opportunities |
| **Inputs** | Recent payment attempt outcomes by cohort; rolling-window config |
| **Outputs** | `degradation_flag` + cohort id + severity band on affected opportunities |
| **Tools allowed** | Read attempt history; write the flag; write `AuditEvent` |
| **Tools forbidden** | Adapters; LLM; any action selection |
| **Decision authority** | Flagging only. The flag **shifts action fit**; it does not choose an action. |
| **Failure modes** | False positives on low-volume cohorts; lag in detection; flag persisting after recovery |
| **Escalation** | Minimum-volume threshold before flagging; flag auto-expires |
| **Observability** | `degradation_windows_open`, `opportunities_flagged_degraded` |
| **Evaluation** | Detection rate within injected degradation windows; false-positive rate outside them |
| **Requirements** | `RR-FUNC-006` |

---

## 4. UNDERSTAND modules

### C-04 · Context Enricher

| Field | Value |
|---|---|
| **Phase** | UNDERSTAND |
| **Kind** | Deterministic |
| **Responsibility** | Assemble the full, pseudonymised context object for an opportunity |
| **Inputs** | Opportunity; customer record; instrument state; contact history; timing context |
| **Outputs** | `ContextObject` — schema-validated, every field present or explicitly null with a reason |
| **Tools allowed** | Read domain tables; write nothing except a cached context blob |
| **Tools forbidden** | Adapters; LLM; write to domain tables |
| **Decision authority** | None |
| **Failure modes** | Missing customer record; stale contact history; incomplete instrument state |
| **Escalation** | Mark fields null with a reason; set `context_degraded = true`, which raises the uncertainty term downstream |
| **Observability** | `context_degraded_rate`, `context_field_null_rate{field}` |
| **Evaluation** | Field-completeness rate; fatigue-state agreement with independent recomputation from `Intervention` rows |
| **Requirements** | `RR-FUNC-013`…`015`, `017` |

### C-05 · Root Cause Analyst  🤖 AGENT

| Field | Value |
|---|---|
| **Phase** | UNDERSTAND |
| **Kind** | Deterministic mapping + **LLM-assisted ranking** |
| **Responsibility** | Produce a ranked set of *candidate causes* with confidence bands and evidence references. Never asserts proven causation. |
| **Inputs** | `ContextObject`; raw failure-reason string (as **untrusted data**); degradation flag; instrument state; cohort statistics |
| **Outputs** | `Diagnosis { ranked_causes: [{cause_code ∈ closed set, confidence_band ∈ {LOW, MED, HIGH}, evidence_refs: [row ids]}], unclassified: bool }` |
| **Tools allowed** | Read `ContextObject` and evidence rows; **one** LLM call per opportunity, schema-constrained, cached; write `Diagnosis`, `AuditEvent` |
| **Tools forbidden** | **Any numeric output.** Any adapter. Any write outside `Diagnosis`. Any free-form cause not in the taxonomy. Multi-turn or self-directed tool use. |
| **Decision authority** | Ranks causes. **Cannot** set a probability, a cost, an amount, or an action. The confidence *band* is mapped to a numeric prior by a versioned deterministic table the analyst cannot see or change. |
| **Failure modes** | Hallucinated cause outside the taxonomy; over-confident band; prompt injection via the failure-reason string; LLM unavailable; nondeterministic output |
| **Escalation** | Schema validation failure → discard, use deterministic-only mapping, log `llm_output_rejected`. LLM unavailable → deterministic-only path (the cycle still completes). |
| **Observability** | `llm_calls{cached,uncached}`, `llm_output_rejected{reason}`, `diagnosis_unclassified_rate`, band distribution |
| **Evaluation** | (i) Agreement with generator ground-truth cause on the eval split; (ii) band calibration — HIGH-band diagnoses must be right more often than MED; (iii) zero out-of-taxonomy outputs; (iv) zero injection successes on the test corpus |
| **Requirements** | `RR-FUNC-010`…`012`, `016`; constrained by `RR-GUARD-020`, `RR-NFR-063`, `RR-NFR-064` |

> **Why an LLM here at all.** The deterministic taxonomy map handles known reason codes perfectly and
> cheaply. The LLM earns its place on the residual: unmapped or free-text reasons, and cases where
> several signals conflict (e.g. `DO_NOT_HONOUR` on a customer with a good instrument during a
> degradation window — is this an issuer problem or a customer problem?). Ranking that residual is a
> genuine reasoning task. Pricing it is not, so the LLM does not price it.

---

## 5. SIMULATE modules

### C-06 · Candidate Generator

| Field | Value |
|---|---|
| **Phase** | SIMULATE |
| **Kind** | Deterministic (rule table) |
| **Responsibility** | Produce the feasible action set for an opportunity, always including `NO_ACTION` |
| **Inputs** | Opportunity; `Diagnosis`; `ContextObject`; action catalogue; channel eligibility |
| **Outputs** | ≥ 3 `ActionCandidate` rows (≥ 2 real + `NO_ACTION`) with action parameters (delay, channel, incentive tier) |
| **Tools allowed** | Read the action catalogue and context; write `ActionCandidate` |
| **Tools forbidden** | Adapters; LLM; pricing; selection |
| **Decision authority** | Feasibility only. Does not rank. |
| **Failure modes** | Empty candidate set; candidate for an ineligible channel; missing `NO_ACTION` |
| **Escalation** | Empty set → class-default candidate set + `candidate_fallback` flag |
| **Observability** | `candidates_per_opportunity` distribution, `candidate_fallback_rate` |
| **Evaluation** | ≥ 3 candidates on 100% of addressable opportunities; candidate sets provably differ across `FailureReason` values |
| **Requirements** | `RR-FUNC-020`…`022` |

### C-07 · Recovery Predictor

| Field | Value |
|---|---|
| **Phase** | SIMULATE |
| **Kind** | Deterministic statistical model |
| **Responsibility** | Estimate `p(i,a)` for each candidate, `p(i,∅)` for no-action, and an uncertainty measure |
| **Inputs** | Feature vector from `ContextObject` + `Diagnosis` + candidate parameters; `StrategyVersion` parameters |
| **Outputs** | `{p_action, p_natural, sigma}` per candidate — floats in `[0,1]` |
| **Tools allowed** | Read features and strategy parameters |
| **Tools forbidden** | **LLM (absolutely).** Adapters. Writing strategy parameters (only C-21 may). Reading the hidden oracle. |
| **Decision authority** | Estimation only |
| **Failure modes** | Miscalibration; unseen feature combination; parameter file missing/corrupt; over-confident `sigma` |
| **Escalation** | Parameter load failure → **fail closed: the entire cycle defers with no actions** (step 9 in [07 § 4](07-system-architecture.md)). Unseen cell → shrink to the parent cell's prior and inflate `sigma`. |
| **Observability** | `prediction_calls`, `unseen_cell_rate`, `mean_sigma`, calibration metrics |
| **Evaluation** | Brier score and ECE on the eval split (`M-24`); reliability curve; **calibration matters more than discrimination** because `ENRV` is a linear function of `p` |
| **Requirements** | `RR-FUNC-023`, `028`; `RR-NFR-003` |

### C-08 · Cost Model

| Field | Value |
|---|---|
| **Phase** | SIMULATE |
| **Kind** | Deterministic |
| **Responsibility** | Compute `c(a)`, `d(i,a)`, and `F(i,a)` in integer paise |
| **Inputs** | Action catalogue costs; incentive tier; fatigue state; `λ_f`; customer value band |
| **Outputs** | Cost components per candidate |
| **Tools allowed** | Read catalogue and context |
| **Tools forbidden** | LLM; adapters |
| **Decision authority** | None beyond arithmetic |
| **Failure modes** | Cost drift vs actual; fatigue term mis-specified; double-counting incentive cost |
| **Escalation** | Actual-vs-estimated variance is reconciled in VERIFY and reported |
| **Observability** | `cost_estimate_total`, `cost_variance_pct` |
| **Evaluation** | Component-sum reconstruction test; variance vs actual reported, not hidden |
| **Requirements** | `RR-FUNC-026` |

### C-09 · Counterfactual Evaluator

| Field | Value |
|---|---|
| **Phase** | SIMULATE |
| **Kind** | Deterministic |
| **Responsibility** | Compute uplift and `ENRV` per candidate with an interval, and record the comparison |
| **Inputs** | Predictor output; cost components; `V(i)`; `m`; `λ_f` |
| **Outputs** | `ENRV` (paise), `uplift`, `enrv_interval`, and the component breakdown for rendering |
| **Tools allowed** | Read the above; write `ActionCandidate` pricing fields |
| **Tools forbidden** | LLM; adapters; selection |
| **Decision authority** | Pricing only. Does not select. |
| **Failure modes** | Sign errors; conditional/unconditional cost confusion; rounding drift |
| **Escalation** | Assertion failure aborts the cycle rather than pricing wrongly (fail closed) |
| **Observability** | `enrv_distribution`, `negative_uplift_candidate_rate` |
| **Evaluation** | Hand-computed fixtures; component-sum reconstruction; monotonicity properties ([11 § 6](11-counterfactual-engine.md)) |
| **Requirements** | `RR-FUNC-025`, `027`, `029` |

### C-10 · Copy Composer  🤖 AGENT

| Field | Value |
|---|---|
| **Phase** | SIMULATE |
| **Kind** | **LLM-assisted**, template-bound |
| **Responsibility** | Fill the text slots of an approved message template |
| **Inputs** | Template id; a fixed, whitelisted variable set (pseudonymous name token, product token, language tag); tone parameter |
| **Outputs** | Rendered text for text-only slots |
| **Tools allowed** | One cached LLM call per (template, variable-set) combination |
| **Tools forbidden** | Populating any `*_paise`, `*_pct`, date, or URL slot — **the renderer rejects such output**. Choosing a channel. Choosing an incentive. Adding claims or offers not present in the template. |
| **Decision authority** | Wording only |
| **Failure modes** | Inventing an offer; injecting a number; unsafe or non-compliant phrasing; prompt injection from customer-derived tokens |
| **Escalation** | Renderer rejection → fall back to the static template text. This fallback is always available, so copy generation can be disabled entirely with no functional loss. |
| **Observability** | `copy_generated`, `copy_rejected{reason}`, `copy_fallback_rate` |
| **Evaluation** | Zero numeric-slot violations; zero offers absent from the template; injection corpus pass rate 100% |
| **Requirements** | `RR-FUNC-024`; constrained by `RR-GUARD-020` |

---

## 6. PRIORITIZE, GUARD, ACT, VERIFY, LEARN modules

### C-11 · Policy Pre-Filter

| Field | Value |
|---|---|
| **Phase** | GUARD (early) | 
| **Responsibility** | Remove candidates that no gate could ever allow, before allocation, so infeasible options do not consume allocation capacity |
| **Inputs** | Candidates; policy pack; customer consent and fatigue state |
| **Outputs** | Filtered candidate set + a `prefilter_reason` on every removal |
| **Decision authority** | Removal only. **Pre-filter passing does not authorise anything** — full gates still run after allocation (`RR-FUNC-037`) |
| **Failure modes** | Over-filtering (removes a viable candidate); under-filtering (wasted allocation capacity) |
| **Escalation** | On uncertainty, do **not** filter — let the full gate decide (this direction of error is safe) |
| **Observability** | `prefilter_removed{reason}` |
| **Evaluation** | No candidate removed by pre-filter is later shown to be allowable by full gates (over-filter test) |
| **Requirements** | `RR-FUNC-037` |

### C-12 · Recovery Allocator — *the central module*

| Field | Value |
|---|---|
| **Phase** | PRIORITIZE |
| **Kind** | Deterministic optimisation |
| **Responsibility** | Choose the feasible bundle of (opportunity, action) pairs maximising total `ENRV` under all resource constraints |
| **Inputs** | Priced, pre-filtered candidates; ledger capacities; `ε`; exploration share; time budget |
| **Outputs** | `Decision` per considered opportunity: `SELECTED(action)` / `DEFERRED(reason)` / `REJECTED(reason)` / `NO_ACTION(reason)`; shadow prices; `allocator_mode` |
| **Tools allowed** | Read candidates and ledger capacities; write `Decision` |
| **Tools forbidden** | **LLM.** Adapters. Writing to the ledger (only reserve, via C-16, and only after gates). Overriding a gate verdict. |
| **Decision authority** | Selection under constraints. **Selection is a proposal, not an authorisation** — C-13 can still deny. |
| **Failure modes** | Infeasibility; timeout; degenerate all-`NO_ACTION`; nondeterministic tie-breaking; over-allocation of a resource |
| **Escalation** | Timeout → greedy fallback with `allocator_mode = FALLBACK_GREEDY`. Infeasible → return all-defer with the binding constraint recorded. |
| **Observability** | `allocation_runtime_ms`, `binding_constraints`, `shadow_price{resource}`, `selected/deferred/rejected/no_action` counts, `allocator_mode` |
| **Evaluation** | (i) Optimality gap vs exact ILP on small batches; (ii) constraint satisfaction always; (iii) determinism across runs; (iv) beats greedy-by-value baseline on `ENRV` achieved; (v) set-completeness (`AI-8`) |
| **Requirements** | `RR-FUNC-030`…`039` |

### C-13 · Policy / Guardrail Engine — *the authority*

| Field | Value |
|---|---|
| **Phase** | GUARD |
| **Kind** | Deterministic, ordered rule evaluation |
| **Responsibility** | Return a final verdict for every proposed action |
| **Inputs** | Proposed action; policy pack (versioned, immutable); consent, contact, retry, risk, budget, idempotency, stopping state |
| **Outputs** | `ALLOW` / `ALLOW_WITH_MODIFICATION(params)` / `DEFER(reason)` / `DENY(reason)` / `REQUIRE_APPROVAL(reason)` + the full per-gate trace |
| **Tools allowed** | Read state; write `GateVerdict`, `AuditEvent`; request `RESERVE` from C-16 |
| **Tools forbidden** | **LLM.** Adapters. Any write to policy tables. Any economic re-ranking. |
| **Decision authority** | **Final.** No component may override a verdict within the cycle (`RR-GUARD-023`) |
| **Failure modes** | Missing policy pack; contradictory rules; state staleness; a gate silently skipped |
| **Escalation** | Missing/corrupt policy pack → **deny everything** for the cycle (fail closed). Contradiction → the more restrictive rule wins, and the contradiction is logged as a defect. |
| **Observability** | `gate_verdicts{gate,verdict}`, `gate_evaluation_ms`, `policy_pack_version` |
| **Evaluation** | Every gate fires at least once across the benchmark; `M-16` = 0; policy replay reproduces historical verdicts |
| **Requirements** | `RR-GUARD-001`…`012`, `023`, `026` |

### C-14 · Stopping-Rule Evaluator

| Field | Value |
|---|---|
| **Phase** | GUARD |
| **Responsibility** | Evaluate `SR-01`…`SR-11` and produce a stop reason where satisfied |
| **Inputs** | Opportunity state; attempt/contact history; outcomes; budget state; clock |
| **Outputs** | `{stopped: bool, stop_reason_code}` |
| **Decision authority** | Can terminate an opportunity. Cannot start anything. |
| **Failure modes** | Rule evaluated only at cycle start and not before the action (`RR-FUNC-051`); rule never fires |
| **Escalation** | Unknown/indeterminate state → treat as stopped (fail closed) |
| **Observability** | `stops{rule}`, coverage table |
| **Evaluation** | All 11 rules fire at least once across the benchmark; `M-17` = 0 |
| **Requirements** | `RR-FUNC-050`, `051`; `RR-GUARD-010` |

### C-15 · Approval Queue

| Field | Value |
|---|---|
| **Phase** | GUARD |
| **Responsibility** | Hold `REQUIRE_APPROVAL` actions for human decision; support approve / reject / modify |
| **Inputs** | Proposed action + its full decision context |
| **Outputs** | `APPROVED` / `REJECTED` / `MODIFIED(params)`, with approver identity and timestamp |
| **Decision authority** | The human's decision is authoritative — **but a modification re-enters all gates** (`RR-FUNC-066`), so a human cannot approve a policy violation |
| **Failure modes** | Queue starvation; approval after the recovery window closed; approver acting outside role |
| **Escalation** | Expired approvals are voided by `SR-06`; queue depth is an alert condition |
| **Observability** | `approval_queue_depth`, `approval_latency`, `approval_outcomes{outcome}` |
| **Evaluation** | `M-18`; zero executions of an unapproved `REQUIRE_APPROVAL` action; modification-re-gating test |
| **Requirements** | `RR-GUARD-007`, `RR-FUNC-066` |
| **Benchmark note** | In benchmark runs the approver is a **simulated policy** with a documented response model and latency, drawn from `stream(seed,"approver")`, and is labelled as such in every artefact ([20 § 7](20-benchmark.md)) |

### C-16 · Resource Ledger

| Field | Value |
|---|---|
| **Phase** | GUARD / ACT |
| **Responsibility** | The single owner of capacity. Two-phase `RESERVE` → `COMMIT`/`RELEASE` |
| **Inputs** | Reservation requests; commit/release instructions |
| **Outputs** | Reservation handles; capacity state; shadow-price inputs |
| **Tools allowed** | Transactional writes to ledger tables only |
| **Tools forbidden** | LLM; adapters; any economic decision |
| **Decision authority** | Grant or refuse a reservation. Nothing else. |
| **Failure modes** | Over-commit; leaked reservations from crashed actions; double-release |
| **Escalation** | Invariant assertion `committed + reserved ≤ limit` checked continuously; violation aborts the cycle. Orphaned reservations reclaimed at cycle open. |
| **Observability** | `budget_utilisation{resource}`, `reservations_open`, `reservations_leaked` |
| **Evaluation** | `RR-NFR-041` property test under injected concurrency and crashes |
| **Requirements** | `RR-GUARD-006`, `RR-FUNC-062` |

### C-17 · Execution Agent

| Field | Value |
|---|---|
| **Phase** | ACT |
| **Kind** | Deterministic orchestration (not LLM) |
| **Responsibility** | Execute exactly the approved action, exactly once, with audit before effect |
| **Inputs** | `ALLOW`-verdicted action with reservation handle and idempotency key |
| **Outputs** | `Intervention` row with a typed outcome |
| **Tools allowed** | Exactly one adapter call for the approved action code; write `Intervention`, `AuditEvent`; commit/release the reservation |
| **Tools forbidden** | Choosing or substituting an action. Retrying a financial action without a fresh gate pass. Calling an adapter for an action code other than the approved one. Any LLM. |
| **Decision authority** | **None.** It is a hand, not a brain. |
| **Failure modes** | Adapter timeout with unknown effect; duplicate submission; partial execution of a multi-step action; crash between audit and adapter |
| **Escalation** | `TIMEOUT_UNKNOWN` → `RECONCILING`, no further action on that opportunity until resolved (`RR-FUNC-065`) |
| **Observability** | `interventions{action,outcome}`, `execution_latency`, `idempotency_hits` |
| **Evaluation** | Zero duplicate effects under the concurrency and crash suites; zero executions without a preceding audit event |
| **Requirements** | `RR-FUNC-060`…`062`, `064`, `065`; `RR-GUARD-021` |

### C-18 · Action Adapters

| Field | Value |
|---|---|
| **Phase** | ACT |
| **Responsibility** | Translate an action into an effect, behind one interface, with typed results |
| **Implementations** | `SimulatedPaymentAdapter`, `SimulatedMessageAdapter`, `SimulatedVoiceAdapter`, `HumanTaskAdapter`. **No real provider adapter exists in this build** (`OS-02`) |
| **Outputs** | `SUCCESS` / `FAILED_RETRYABLE` / `FAILED_TERMINAL` / `TIMEOUT_UNKNOWN` / `REJECTED_BY_PROVIDER` |
| **Decision authority** | None |
| **Failure modes** | Untyped result leaking upward; simulator differing from the interface contract |
| **Escalation** | Any unmapped result becomes `TIMEOUT_UNKNOWN` (the most conservative class) |
| **Observability** | `adapter_calls{adapter,result}`, `adapter_latency` |
| **Evaluation** | Shared adapter contract test suite passes for every implementation (`RR-NFR-083`) |
| **Requirements** | `RR-FUNC-063`, `064` |
| **Note** | The simulated adapters consult the hidden oracle (C-25). This is the **only** point in the system where the oracle is reachable, and C-17 receives only the typed result — never the oracle's parameters (`AI-6`) |

### C-19 · Outcome Observer · C-20 · Attribution Classifier

| Field | C-19 | C-20 |
|---|---|---|
| **Phase** | VERIFY | VERIFY |
| **Responsibility** | Record whether money arrived, how much, and when | Classify each recovery as `ATTRIBUTED` / `NATURAL` / `AMBIGUOUS` |
| **Inputs** | Post-action state; payment/invoice records; horizon `H` | Outcome; whether an action was taken; timing; control information available in-sim |
| **Outputs** | `Outcome` with `recovered_amount_paise`, partial support, actual cost | Attribution class + rationale |
| **Decision authority** | None | None — and critically, **attribution never inflates `M-10`**, which is computed by paired policy comparison, not by attribution (`RR-FUNC-071`, [21 § 5](21-evaluation.md)) |
| **Failure modes** | Outcome not observable within `H`; partial payment; late payment after window | Post-hoc credit-taking; ambiguity treated as success |
| **Escalation** | Unobservable → `AMBIGUOUS`, excluded from attributed totals, counted in a disclosed bucket | Ambiguity always resolves *against* REVIVE |
| **Observability** | `outcomes{class}`, `partial_recovery_rate`, `unobservable_rate` | `attribution{class}` |
| **Evaluation** | Recovered-amount reconciliation; `M-21` | Attribution never exceeds paired-comparison incremental value |
| **Requirements** | `RR-FUNC-070`, `072`, `073` | `RR-FUNC-071` |

### C-21 · Learning Engine

| Field | Value |
|---|---|
| **Phase** | LEARN |
| **Kind** | Deterministic Bayesian updating |
| **Responsibility** | Update predictor parameters from observed outcomes; emit a new `StrategyVersion` |
| **Inputs** | Outcomes; the decisions that produced them; prior `StrategyVersion` |
| **Outputs** | New `StrategyVersion` with updated posteriors; calibration report |
| **Tools allowed** | Read outcomes and decisions; write `StrategyVersion` and predictor parameter rows |
| **Tools forbidden** | **Writing any policy, budget, threshold, limit, or gate table** (`RR-GUARD-022`, enforced at the data-access layer). Adapters. LLM. |
| **Decision authority** | Changes beliefs. **Never changes permissions.** |
| **Failure modes** | Feedback loop (only acted-on cells get data); overfitting to a seed; drift; poisoning via manipulated outcomes |
| **Escalation** | Capped exploration budget supplies data for unacted cells; shrinkage toward parent cells; a version that degrades calibration is rolled back |
| **Observability** | `strategy_version`, `calibration{brier,ece}`, `cells_updated`, `exploration_spend` |
| **Evaluation** | Learning-on vs learning-off ablation, both reported; calibration must not degrade |
| **Requirements** | `RR-FUNC-080`…`083`; principle P-12 |

### C-23 · Cycle Orchestrator  🤖 AGENT (orchestrating, not LLM)

| Field | Value |
|---|---|
| **Responsibility** | Execute the fixed 23-step cycle in order, within a step budget |
| **Tools forbidden** | Deviating from the sequence; skipping GUARD; retrying a failed financial action without re-gating; **any LLM call**; any self-directed planning |
| **Decision authority** | Sequencing and abort only |
| **Failure modes** | Step budget exceeded; partial cycle; orphaned reservations |
| **Escalation** | Clean termination with a recorded reason; reservations reclaimed at next cycle open |
| **Observability** | `cycle_duration_ms`, `cycle_steps_completed`, `cycle_aborts{reason}` |
| **Requirements** | `RR-GUARD-025` |

---

## 7. Permission model

No module has unrestricted capability. Read this table as the authoritative grant list — a
capability not granted here is forbidden.

| Module | Read | Write | Simulate | Execute | Approve | Deny | LLM |
|---|---|---|---|---|---|---|---|
| C-01 Ingestor | signals | signals, quarantine, audit | — | — | — | — | ✗ |
| C-02 Sentinel | domain | opportunities, audit | — | — | — | — | ✗ |
| C-03 Degradation Monitor | attempts | flags, audit | — | — | — | — | ✗ |
| C-04 Enricher | domain | context cache | — | — | — | — | ✗ |
| C-05 Root Cause Analyst | context, evidence | diagnosis, audit | — | — | — | — | **✓** (closed-set, cached) |
| C-06 Candidate Generator | catalogue, context | candidates | — | — | — | — | ✗ |
| C-07 Predictor | features, strategy | — | **✓** | — | — | — | ✗ |
| C-08 Cost Model | catalogue, context | — | **✓** | — | — | — | ✗ |
| C-09 Counterfactual Evaluator | predictions, costs | candidate pricing | **✓** | — | — | — | ✗ |
| C-10 Copy Composer | template, whitelist vars | copy field | — | — | — | — | **✓** (text slots only) |
| C-11 Pre-Filter | policy, state | prefilter reasons | — | — | — | soft | ✗ |
| C-12 **Allocator** | candidates, capacities | decisions | **✓** | — | — | — | ✗ |
| C-13 **Policy Engine** | all state, policy pack | verdicts, audit | — | — | — | **✓ final** | ✗ |
| C-14 Stopping Evaluator | state, history | stop reasons | — | — | — | **✓** | ✗ |
| C-15 Approval Queue | decision context | approvals, audit | — | — | **✓ (human)** | ✓ | ✗ |
| C-16 Ledger | ledger | ledger (transactional) | — | — | — | ✓ (reservation refusal) | ✗ |
| C-17 Execution Agent | approved action | interventions, audit | — | **✓ approved action only** | — | — | ✗ |
| C-18 Adapters | action payload | — | — | **✓ effect** | — | — | ✗ |
| C-19 Outcome Observer | post-state | outcomes | — | — | — | — | ✗ |
| C-20 Attribution | outcomes | attribution | — | — | — | — | ✗ |
| C-21 Learning Engine | outcomes, decisions | **strategy params only** | — | — | — | — | ✗ |
| C-22 Audit Store | — | append-only | — | — | — | — | ✗ |
| C-23 Orchestrator | cycle state | cycle rows, audit | — | — | — | — | ✗ |
| Human operator | everything in the UI | approvals, `HALT` | — | — | **✓** | **✓** | — |

### 7.1 Capability rules

1. **Only C-17 can execute**, and only the action C-13 allowed.
2. **Only C-13 can allow.** C-12 proposes; C-13 authorises.
3. **Only C-16 can move capacity.**
4. **Only C-21 can change predictor parameters**, and it can change nothing else.
5. **Only C-22 receives audit writes**, and only as appends.
6. **Only C-05 and C-10 may call an LLM**, both schema-closed and cached.
7. **The human can always deny and always halt** (`RR-GUARD-024`).
8. **No module may grant itself a capability at runtime.** There is no dynamic tool discovery, no
   tool registry the model can extend, and no reflection-based dispatch on model output.

---

## 8. Bounded reasoning

The word "agent" often implies open-ended loops. REVIVE's agents are bounded in four ways:

| Bound | Value |
|---|---|
| **Turns per LLM call site** | 1. No multi-turn agent loops. No self-reflection cycles. |
| **Tool access from within an LLM call** | **None.** The LLM receives a prepared context object and returns a structured value. It cannot call tools, fetch data, or trigger effects. |
| **Output space** | Closed sets, validated. Invalid output is discarded, not repaired by another model call. |
| **Cycle step budget** | Fixed 23 steps; exceeding the budget terminates the cycle (`RR-GUARD-025`) |

This is what "bounded recovery workflow" means structurally: the system's autonomy lives in *which
priced action it selects under constraints*, not in an open-ended reasoning loop that could
discover new things to do.

---

## 9. Failure isolation summary

| If this fails | The system | Because |
|---|---|---|
| LLM unavailable | Runs deterministic-only diagnosis and static copy; cycle completes | Both agents have a complete fallback path |
| Predictor parameters corrupt | Defers the entire cycle; takes no action | Pricing without calibration is worse than not acting (P-11) |
| Allocator times out | Uses greedy fallback; records the mode | A feasible suboptimal bundle beats no decision |
| Policy pack missing | Denies everything | Fail closed |
| Ledger invariant violated | Aborts the cycle | Over-commitment is unrecoverable |
| Adapter times out | Marks `TIMEOUT_UNKNOWN`, enters `RECONCILING`, blocks further action on that opportunity | Never assume success, never blind-retry money |
| Audit store unwritable | **Halts execution** | An unauditable action is forbidden (`AI-4`) |
| Learning update fails | Keeps the prior `StrategyVersion` | Learning is optional; correctness is not |
| Human approver absent | Actions expire via `SR-06`; nothing executes | Silence is not consent |
