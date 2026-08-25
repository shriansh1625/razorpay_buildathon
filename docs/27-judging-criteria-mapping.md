# 27 · Judging Criteria Mapping

A strict traceability matrix from Track 03 requirements to REVIVE capabilities, implementation
evidence, demo evidence, and benchmark evidence. Every row must have evidence. Gaps are named,
not hidden.

---

## 1. Source

Track 03 brief (reproduced verbatim in [01-track-alignment.md § 1](01-track-alignment.md)):

> Build an agent that detects revenue at risk, determines the right intervention, and executes a
> bounded recovery workflow: from payment failures and checkout abandonment to overdue
> receivables.

> The bar: Don't just identify the problem. Show measured money recovered across a batch, with
> compliant escalation, stopping rules, and an audit trail.

---

## 2. Traceability matrix

| # | Track Requirement | REVIVE Capability | Requirement IDs | Implementation Evidence | Demo Evidence | Benchmark Evidence | Status |
|---|---|---|---|---|---|---|---|
| JC-01 | **Detects revenue at risk** | Revenue Sentinel (C-02) converts signals into typed `RevenueOpportunity` records across 4 risk classes with value-at-risk estimate | `RR-FUNC-001`…`007` | Detection module with recall ≥ 0.99, precision ≥ 0.99 per class against generator ground truth | Beat 2: Revenue Leakage Explorer shows detected value by class | `M-01` value at risk; detection recall/precision per class | **COVERED** |
| JC-02 | **Revenue-risk detection: payment failures** | `risk_class = PAYMENT_FAILURE` detected from payment-failure signals | `RR-FUNC-001` | Candidate set includes `RETRY_NOW`, `RETRY_SCHEDULED`, `PAYMENT_LINK`, `ALT_METHOD_PROMPT` | Beat 2: Payment failures visible in leakage breakdown | Opportunities with class `PAYMENT_FAILURE` in batch | **COVERED** |
| JC-03 | **Revenue-risk detection: checkout abandonment** | `risk_class = CHECKOUT_ABANDONMENT` detected from abandoned checkout sessions | `RR-FUNC-001` | Candidate set includes `PAYMENT_LINK`, `MSG_*` reminders | Beat 2: Checkout abandonment visible in leakage breakdown | Opportunities with class `CHECKOUT_ABANDONMENT` in batch | **COVERED** |
| JC-04 | **Revenue-risk detection: subscription/mandate failure** | `risk_class = SUBSCRIPTION_FAILURE` detected from mandate/subscription failures | `RR-FUNC-001` | Candidate set includes `MANDATE_RETRY_SEQUENCE`, instrument-update prompts | Beat 2: Subscription failures visible in leakage breakdown | Opportunities with class `SUBSCRIPTION_FAILURE` in batch | **COVERED** |
| JC-05 | **Revenue-risk detection: overdue receivables** | `risk_class = RECEIVABLE_OVERDUE` detected from invoice ageing, with buckets | `RR-FUNC-001`, `008` | Ageing buckets (`0-15`, `16-30`, `31-60`, `61-90`, `90+`) drive candidate set and escalation | Beat 2: Receivables visible in leakage breakdown with ageing | Opportunities with class `RECEIVABLE_OVERDUE` in batch | **COVERED** |
| JC-06 | **Determines the right intervention (root cause / context)** | Root Cause Analyst (C-05) produces ranked candidate causes with confidence. Context Enricher (C-04) assembles customer, instrument, contact, and timing context | `RR-FUNC-010`…`017` | Diagnosis with closed-set causes, confidence bands, evidence refs. LLM-assisted for residual cases, deterministic for known codes | Beat 3: Decision Detail shows candidate causes, confidence, evidence | `M-27` diagnosis agreement; `M-51` unclassified rate | **COVERED** |
| JC-07 | **Determines the right intervention (action selection)** | Candidate Generator (C-06) → Recovery Predictor (C-07) → Cost Model (C-08) → Counterfactual Evaluator (C-09) → Recovery Allocator (C-12). Selects by ENRV under constraints | `RR-FUNC-020`…`039` | ≥ 3 candidates per opportunity; ENRV computed per frozen formula; allocator solves under ≥ 4 constraints | Beat 3: Full candidate set with ENRV comparison. Beat 4: Portfolio allocation | `M-10` incremental recovery; `M-28` wrong-action value loss | **COVERED** |
| JC-08 | **Bounded recovery workflow** | Fixed 23-step cycle; step budget; 12 gates with final authority; 11 stopping rules; finite action catalogue; hard resource ceilings | `RR-GUARD-001`…`027`, `RR-FUNC-050`…`051` | Five independent bounding mechanisms ([14 § 9](14-stopping-rules.md)) | Beat 5: Gate denial, stopping rule fire, approval queue | `M-16 = 0`; all 11 stopping rules fire at least once | **COVERED** |
| JC-09 | **Measured money recovered across a batch** | Benchmark with pre-registered claim, ≥ 20 seeds, paired comparison with CI, baselines B0–B6 | `RR-BENCH-001`…`010` | Benchmark harness; metrics artefact; evaluation report | Beat 6: Comparison table, seed matrix, CI | `M-10` with CI across seeds; falsification conditions F-1…F-6 | **COVERED** |
| JC-10 | **Compliant escalation** | G7 Approval Threshold routes high-value/uncertain actions to human approval. Approved actions re-enter all gates. Expired approvals are voided | `RR-GUARD-007`, `RR-FUNC-066`, `SR-06` | Approval queue implementation; re-gating on modification; expiry | Beat 5: Approval queue shown | `M-37` approval load; `M-38` expiry rate; `M-18 = 0` | **COVERED** |
| JC-11 | **Stopping rules** | 11 stopping rules evaluated twice per cycle (at cycle start and before execution). Terminal and re-openable categories. Coverage required | `RR-FUNC-050`, `051` | All 11 rules implemented and individually testable | Beat 5: Stopping rule firing shown | `M-17 = 0`; coverage table showing all rules fired | **COVERED** |
| JC-12 | **Audit trail** | Hash-chained, append-only, PII-free audit trail. Written before effect. Complete for money and permissions. Sufficient for state reconstruction | `RR-AUDIT-001`…`010` | Audit store with hash chain; verification checks V-1…V-12 | Beat 5: Audit Trail screen; chain verification | `M-58` verification pass; `M-54` event volume | **COVERED** |
| JC-13 | **"Don't just identify the problem"** | REVIVE goes beyond detection: diagnoses, evaluates alternatives, allocates under constraints, executes bounded actions, measures outcomes, learns | Full `RR-FUNC-*` set | Complete SEE → UNDERSTAND → SIMULATE → PRIORITIZE → GUARD → ACT → VERIFY → LEARN loop | Beats 2–7 demonstrate the full loop | `M-10` proves incremental value beyond identification | **COVERED** |
| JC-14 | **Payment degradation → root cause → recovery action** (example direction) | Degradation Monitor (C-03) detects cohort-level failure rate elevation. Diagnosis ranks causes. Recovery action selected | `RR-FUNC-006`, `010`…`012` | Degradation flag on affected opportunities; diagnosis with degradation evidence | Beat 2: Degradation visible in leakage graph (if exercised) | Opportunities with `degradation_flag` in batch | **COVERED** (SHOULD tier for C-03) |
| JC-15 | **Checkout drop-off recovery** (example direction) | `CHECKOUT_ABANDONMENT` class with `PAYMENT_LINK`, messaging actions | `RR-FUNC-001` | Checkout opportunities in candidate generation | Beat 2: Checkout class visible | Checkout-class opportunities in batch | **COVERED** |
| JC-16 | **Failed-subscription recovery** (example direction) | `SUBSCRIPTION_FAILURE` class with mandate retry and instrument-update actions | `RR-FUNC-001` | Subscription opportunities in candidate generation | Beat 2: Subscription class visible | Subscription-class opportunities in batch | **COVERED** |
| JC-17 | **B2B receivables chaser** (example direction) | `RECEIVABLE_OVERDUE` class with ageing buckets, dunning sequence, receivable reminders | `RR-FUNC-001`, `008` | Receivable opportunities with ageing-driven candidate sets | Beat 2: Receivables with ageing visible | Receivable-class opportunities in batch | **COVERED** |
| JC-18 | **Mandate retry sequencer** (example direction) | `MANDATE_RETRY_SEQUENCE` action code with retry caps and cooldowns | `RR-FUNC-021`, `022` | Mandate retry as a candidate action for subscription failures | Part of Beat 3 if example uses subscription | Mandate retry actions in batch | **COVERED** (SHOULD tier) |
| JC-19 | **Hinglish voice recovery** (example direction) | `VOICE_CALL` action with Hinglish template | `RR-FUNC-022` | Voice adapter with voice-minute constraint | Not shown unless built (MAY tier) | Voice actions in batch if implemented | **GAP — MAY TIER** |
| JC-20 | **Promise-to-pay tracker** (example direction) | `PROMISE_TO_PAY_CAPTURE` action code | — | Promise-to-pay as a candidate action for receivables | Not shown unless built (SHOULD tier) | Promise-to-pay actions in batch if implemented | **GAP — SHOULD TIER** |

---

## 3. Gap analysis

| # | Gap | Severity | Rationale | Mitigation |
|---|---|---|---|---|
| JC-19 | Hinglish voice recovery is MAY-tier | LOW | Track lists it as an "example direction", not a requirement. Voice is MAY in [05 § 9](05-functional-requirements.md) | Document as optional. Build only after all P0 stable |
| JC-20 | Promise-to-pay tracker is SHOULD-tier | LOW | Track lists it as an "example direction". Action code exists in the catalogue but implementation is SHOULD | Document as SHOULD. Build if time permits |

No P0/MUST requirement has a gap.

---

## 4. Evidence completeness check

| Evidence type | Coverage |
|---|---|
| Implementation evidence | Every MUST requirement has a specified acceptance criterion in [05](05-functional-requirements.md) |
| Demo evidence | All 10 demo claims (Beat 1–7) are mapped to specific screen content and metrics |
| Benchmark evidence | `M-10` (primary), `M-11`, `M-12`, `M-13`, `M-23` (secondary), `M-16`/`M-17`/`M-18`/`M-22` (guardrail) all mapped |
| Test evidence | [30-test-plan.md](30-test-plan.md) maps tests to requirements |

---

## 5. Requirement mapping

| Requirement | Where |
|---|---|
| Track 03 brief | [01-track-alignment.md](01-track-alignment.md) § 1 |
| `RR-FUNC-*`, `RR-GUARD-*` | [05-functional-requirements.md](05-functional-requirements.md) |
| `RR-BENCH-*` | [20-benchmark.md](20-benchmark.md) |
| `RR-AUDIT-*` | [16-audit-trail.md](16-audit-trail.md) |
| `RR-METRIC-*` | [37-metrics-dictionary.md](37-metrics-dictionary.md) |
| Demo script | [26-demo-script.md](26-demo-script.md) |
