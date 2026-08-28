# 01 · Track Alignment

**Purpose.** Prove, clause by clause, that PAYVANTA sits inside Razorpay Buildathon Track 03 and
satisfies its stated bar. This document is the defence against the two most common submission
failures: building something adjacent to the track, and building something inside the track that
cannot be *shown* to satisfy the bar.

---

## 1. Source of truth

`KNOWN` — the following is the Track 03 brief as supplied by the project owner. It is the highest
authority in this package. Where any other document in `docs/` conflicts with it, this text wins.

> **Track 03 — AI Revenue Recovery**
>
> Find revenue that's slipping away and win it back.
>
> Build an agent that detects revenue at risk, determines the right intervention, and executes a
> bounded recovery workflow: from payment failures and checkout abandonment to overdue
> receivables.
>
> **Why now.** Revenue loss rarely happens in one clean step. A payment degrades, a checkout gets
> abandoned, a subscription fails, or an invoice goes overdue. AI can now close the loop from
> detecting the problem, diagnosing it, choosing the right intervention, and recovering the money.
>
> **Example directions.** Payment degradation → root cause → recovery action · Checkout drop-off
> recovery · Failed-subscription recovery · B2B receivables chaser · Mandate retry sequencer ·
> Hinglish voice recovery · Promise-to-pay tracker
>
> **The bar.** Don't just identify the problem. Show measured money recovered across a batch, with
> compliant escalation, stopping rules, and an audit trail.

### 1.1 Source hierarchy

Priority order for resolving any question. Lower priority may never override higher.

| Rank | Source | Notes |
|---|---|---|
| 1 | Track 03 brief above | `KNOWN`. Non-negotiable. |
| 2 | Official Razorpay documentation, **when explicitly verified and cited** | Nothing in this package is currently at this rank — see [36-razorpay-integration-assumptions.md](36-razorpay-integration-assumptions.md) |
| 3 | PAYVANTA project decisions from the owner's brief | Product name, definition, differentiator, loop, objective |
| 4 | Labelled engineering assumptions in this package | `ASSUMPTION` / `PROPOSED` |
| 5 | General technical convention | Last resort |

### 1.2 External-source citation rule

If the implementation phase consults an external source, it must record: source name, URL, date
accessed, the exact claim supported, and whether the claim affects implementation. A blog post is
never a rank-2 source. Only official Razorpay documentation is rank 2, and only for the specific
claim it directly states.

---

## 2. Clause-by-clause alignment

| Track clause | PAYVANTA response | Where specified | Evidence in demo | Evidence in benchmark |
|---|---|---|---|---|
| "detects revenue at risk" | Revenue Sentinel converts signals into typed `RevenueOpportunity` records across 4 risk classes with a value-at-risk estimate | [05](05-functional-requirements.md) `RR-FUNC-001`…`004`, [12](12-revenue-leakage-model.md) | Demo beat 2 | `M-01 Value at Risk`, detection recall per class |
| "determines the right intervention" | Candidate generation → per-candidate uplift and cost → `ENRV` ranking → allocator selects | [09](09-decision-engine.md), [10](10-recovery-allocation.md), [11](11-counterfactual-engine.md) | Demo beats 3–5 | `M-09 Net Recovered`, `M-10 Incremental Net Recovery` |
| "executes a bounded recovery workflow" | Every action passes 12 ordered gates, carries an idempotency key, consumes a reserved budget unit, and is capped by attempt/contact limits | [13](13-policy-and-guardrails.md), [15](15-execution-model.md) | Demo beat 7 | `M-16 Policy Violations` = 0, `M-17 Stopping-rule violations` = 0 |
| "payment failures" | Risk class `PAYMENT_FAILURE`, with a failure-reason taxonomy driving reason-specific action fit | [12](12-revenue-leakage-model.md) § 4, [19](19-synthetic-dataset.md) § 6 | Demo beat 3 | Per-class recovery breakdown |
| "checkout abandonment" | Risk class `CHECKOUT_ABANDONMENT`, with stage-of-abandonment and fast time decay | [12](12-revenue-leakage-model.md) § 5 | Demo beat 2 | Per-class recovery breakdown |
| "overdue receivables" | Risk class `RECEIVABLE_OVERDUE`, with ageing buckets, promise-to-pay capture and human escalation | [12](12-revenue-leakage-model.md) § 7 | Demo beat 7 | Per-class recovery breakdown |
| "a subscription fails" (Why-now clause) | Risk class `SUBSCRIPTION_FAILURE`, incl. mandate failure and dunning/retry sequencing | [12](12-revenue-leakage-model.md) § 6 | Demo beat 3 | Per-class recovery breakdown |
| "a payment degrades" (Why-now clause) | Degradation is modelled as a **portfolio-level** signal: an elevated failure rate on a method/issuer/BIN cohort, which shifts action fit away from retry-on-same-rail | [12](12-revenue-leakage-model.md) § 4.4, [19](19-synthetic-dataset.md) § 6.4 | Demo beat 3 | Degradation-window sub-analysis |
| "diagnosing it" | Root Cause Analyst produces ranked, evidence-linked candidate causes with explicit confidence, and never asserts proven causation | [08](08-agent-architecture.md) § 4.2, [12](12-revenue-leakage-model.md) § 9 | Demo beat 3 | Diagnosis→action-fit consistency check |
| "closing the loop" | The frozen loop SEE → UNDERSTAND → SIMULATE → PRIORITIZE → GUARD → ACT → VERIFY → LEARN, with LEARN wired back into the predictor | [07](07-system-architecture.md), [35](35-learning-engine.md) | Demo beat 8 | Learning-on vs learning-off ablation |
| **"measured money recovered across a batch"** | Batch benchmark over ≥ 500 opportunities × ≥ 20 seeds, paired against 4 baselines, with bootstrap CI and an oracle ceiling | [20](20-benchmark.md), [21](21-evaluation.md) | Demo beat 10 | The entire evaluation report |
| **"compliant escalation"** | Approval thresholds route high-value/high-risk actions to a human queue; consent, quiet-hours and channel-eligibility gates precede every contact | [13](13-policy-and-guardrails.md) § 5, § 6 | Demo beat 6 | `M-18 Approval-required rate`, escalation audit trail |
| **"stopping rules"** | 11 named, individually testable stopping rules with reason codes, evaluated before every action | [14](14-stopping-rules.md) | Demo beat 6 | Stopping-rule coverage table |
| **"audit trail"** | Append-only, hash-chained `AuditEvent` log; every decision reconstructible; explicit never-log list | [16](16-audit-trail.md) | Demo beat 9 | Chain verification + replay of one case |

No row in this table is empty. Rows that would be empty are tracked as
`GAP — MUST BE RESOLVED` in [38-traceability-matrix.md](38-traceability-matrix.md).

---

## 3. How PAYVANTA relates to the seven "example directions"

The brief lists seven example directions. A common failure is to pick one and build only that — a
narrow point solution. A second failure is to claim all seven and implement none properly.

PAYVANTA's position: **the example directions are action patterns inside one allocation problem, not
seven separate products.** PAYVANTA implements a subset properly and is explicit about the rest.

| Example direction | PAYVANTA treatment | Tier |
|---|---|---|
| Payment degradation → root cause → recovery action | Core path. Degradation is a cohort-level feature that changes action fit. | **MVP** |
| Checkout drop-off recovery | Core path. Risk class with stage-aware candidate set. | **MVP** |
| Failed-subscription recovery | Core path. Risk class with dunning sequence action. | **MVP** |
| B2B receivables chaser | Core path, reduced depth: ageing-aware reminders + human escalation. | **MVP** |
| Mandate retry sequencer | Implemented as the `MANDATE_RETRY_SEQUENCE` action with cooldown and attempt caps. | **Recommended** |
| Promise-to-pay tracker | Implemented as `PROMISE_TO_PAY_CAPTURE` — a state on a receivable opportunity that suppresses further contact until the promised date, then re-opens. | **Recommended** |
| Hinglish voice recovery | Implemented as a **bounded channel** (`VOICE_CALL`) that the allocator may select when it wins on `ENRV` under a voice-minute constraint. It is a channel, **not the product's identity.** See [28](28-risk-register.md) R-07 and § 4 below. | **Optional** |

Tier definitions and the full capability matrix: [05-functional-requirements.md § 9](05-functional-requirements.md).

---

## 4. Explicit guard against the "voice demo" trap

Voice recovery is the most demo-friendly item on the example list and therefore the most dangerous.
A submission that opens with a Hinglish voice call is memorable and *loses the track*, because the
bar asks for measured money across a batch, not a convincing phone call.

Frozen position:

- Voice is one action code among fifteen.
- It is subject to the same `ENRV` test, the same gates, the same budget, and the same audit
  requirements as an SMS.
- It appears in the demo **only after** allocation and guardrails have been shown, and only as an
  illustration that the allocator chose an expensive channel because the expected uplift on a
  high-value receivable justified it.
- If voice cannot be built within the timebox, PAYVANTA loses nothing structural. If the allocator
  cannot be built, PAYVANTA has no product.

See [03-scope-boundaries.md](03-scope-boundaries.md) § 5 for the firewall entry.

---

## 5. Where PAYVANTA goes beyond the literal brief (and why that is allowed)

The brief asks for "an agent". PAYVANTA is specified as a portfolio decision system. This is a
deliberate reading, justified as follows:

1. The brief's bar says "across a **batch**". A per-event agent cannot demonstrate a batch result
   in any interesting way — its batch number is just a sum of independent decisions, and it has no
   mechanism to prefer one opportunity over another when resources run out.
2. The brief says "**bounded** recovery workflow". Boundedness implies limits. Limits imply
   contention. Contention implies allocation. Allocation is therefore *implied by* the brief, not
   an extension of it.
3. The brief says "the **right** intervention". Right is comparative, which requires evaluating
   alternatives — including doing nothing.

`ASSUMPTION` — this reading of "batch" and "bounded" is the project's interpretation. It is
defensible but it is an interpretation, and it is recorded as [ADR-001](31-decision-records.md).

---

## 6. What would put PAYVANTA *outside* the track

Recorded here so the implementation phase can self-check. If any of these becomes true, scope has
drifted and must be corrected:

| Drift symptom | Why it exits the track |
|---|---|
| The centrepiece is a conversational assistant | Track 03 asks for recovery, not chat |
| The centrepiece is a voice bot | Voice is a listed channel, not the objective |
| The system detects fraud, chargebacks, or account takeover | Different problem; not revenue recovery |
| The system recommends but never executes | Brief explicitly requires executing a bounded workflow |
| The system executes but has no budget/cap/stop semantics | "Bounded" is unmet |
| Results are shown for a handful of hand-picked cases | "Across a batch" is unmet |
| There is no baseline | "Measured" recovery is unfalsifiable without one |
| Audit is a log file with no decision reconstruction | "Audit trail" is unmet in substance |
| The system does merchant analytics / BI | Adjacent product; no recovery loop |
| The system does lending, accounting, or reconciliation | Different track entirely |

---

## 7. The bar, restated as a falsifiable claim

PAYVANTA's submission claim will be exactly this sentence, and nothing stronger:

> On a pre-registered synthetic batch of *N* revenue-at-risk opportunities, replicated across *K*
> seeds, under identical budgets and identical policy constraints, REVIVE's allocation policy
> produced **X paise more net recovered revenue** than the strongest baseline (95% bootstrap CI
> `[lo, hi]`), committed **zero** policy or stopping-rule violations, and emitted a verifiable
> audit chain for every one of its *Y* interventions. All figures are produced by a synthetic
> outcome model, not by real payment rails.

Every variable in that sentence is filled from the benchmark artefact. None is filled by hand.
The final clause is mandatory and may not be dropped from any slide, README, or verbal pitch —
see [21-evaluation.md § 8](21-evaluation.md) on honesty in reporting.
