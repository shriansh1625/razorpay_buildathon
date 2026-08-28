# 03 · Scope Boundaries and the Scope Firewall

**This document is operational.** It is not background reading. Every time the implementation phase
considers adding, changing, or expanding a capability, it runs the § 4 procedure and records the
result.

---

## 1. In scope

The following are inside PAYVANTA's scope for this build. Each maps to at least one requirement in
[05-functional-requirements.md](05-functional-requirements.md).

### 1.1 Detection (SEE)

| # | Capability | Notes |
|---|---|---|
| IS-01 | Payment-failure risk detection | 4 risk classes total; see [12](12-revenue-leakage-model.md) |
| IS-02 | Checkout-abandonment risk detection | Stage-aware |
| IS-03 | Subscription / recurring-payment failure detection | Includes mandate failure |
| IS-04 | Overdue-receivable risk detection | Ageing-bucket aware |
| IS-05 | Payment-degradation detection at cohort level | Method / issuer / BIN-band failure-rate elevation |
| IS-06 | Value-at-risk estimation per opportunity | Deterministic derivation from the underlying record |
| IS-07 | Deduplication of signals into one opportunity per economic loss | Prevents double-counting a retried failure |

### 1.2 Understanding (UNDERSTAND)

| # | Capability | Notes |
|---|---|---|
| IS-10 | Failure-reason classification into a fixed taxonomy | Deterministic mapping; LLM only for unmapped free text |
| IS-11 | Ranked candidate-cause generation with evidence references | Never asserts proven causation |
| IS-12 | Customer-state and lifecycle context assembly | Tenure, segment, history, prior recovery behaviour |
| IS-13 | Contact-history and fatigue-state assembly | Feeds both the fatigue term and the contact gate |
| IS-14 | Payment-instrument state assembly | Expiry, method, prior success on this instrument |

### 1.3 Simulation (SIMULATE)

| # | Capability | Notes |
|---|---|---|
| IS-20 | Candidate action generation, reason-aware and class-aware | Always includes `NO_ACTION` |
| IS-21 | Recovery-probability estimation per candidate | Calibrated; deterministic model |
| IS-22 | Natural-recovery (no-action) baseline estimation | Required for uplift; the hard part |
| IS-23 | Uplift computation | `p(a) − p(∅)` |
| IS-24 | Cost model per action | Fixed cost, conditional incentive cost, fatigue externality |
| IS-25 | `ENRV` computation with uncertainty | Point estimate plus interval |
| IS-26 | Counterfactual comparison across candidates | The `Decision` explains why the winner won |

### 1.4 Prioritisation (PRIORITIZE)

| # | Capability | Notes |
|---|---|---|
| IS-30 | Multi-constraint allocation across the opportunity portfolio | The central algorithm |
| IS-31 | Explicit deferral with reason for non-selected opportunities | Deferral is a recorded decision, not a gap |
| IS-32 | Shadow-price / binding-constraint reporting | Makes the constraint visible in the UI |
| IS-33 | Deterministic tie-breaking | Reproducibility requirement |
| IS-34 | Exploration allocation within a capped share of budget | Feeds LEARN; see [35](35-learning-engine.md) |

### 1.5 Guarding (GUARD)

| # | Capability | Notes |
|---|---|---|
| IS-40 | Ordered gate evaluation, deterministic | 12 gates; see [13](13-policy-and-guardrails.md) |
| IS-41 | Consent and opt-out enforcement | Hard deny |
| IS-42 | Communication-window / quiet-hours enforcement | Merchant-local time |
| IS-43 | Contact-frequency caps per customer per window | Hard deny |
| IS-44 | Retry caps and cooldowns per instrument | Hard deny |
| IS-45 | Incentive ceiling enforcement, including clamping | `ALLOW_WITH_MODIFICATION` |
| IS-46 | Budget and capacity reservation | Two-phase, race-safe |
| IS-47 | Approval thresholds routing to a human queue | Compliant escalation |
| IS-48 | Risk-flag blocking | e.g. `RISK_BLOCKED` reason, disputed invoices |
| IS-49 | Duplicate-action suppression / idempotency | Financial safety |
| IS-50 | Stopping-rule evaluation | 11 rules; see [14](14-stopping-rules.md) |
| IS-51 | Channel-eligibility checks | e.g. WhatsApp requires channel opt-in |

### 1.6 Acting (ACT)

| # | Capability | Notes |
|---|---|---|
| IS-60 | Bounded execution of the approved action, exactly once | Idempotency keys mandatory |
| IS-61 | Adapter abstraction over payment / comms / voice effects | Simulator behind it for this build |
| IS-62 | Human-approval queue with approve / reject / modify | Modification re-enters the gates |
| IS-63 | Execution failure handling with typed outcomes | See [23](23-failure-recovery.md) |

### 1.7 Verifying (VERIFY)

| # | Capability | Notes |
|---|---|---|
| IS-70 | Outcome observation with recovered amount | Including partial recovery |
| IS-71 | Attribution classification | `ATTRIBUTED` / `NATURAL` / `AMBIGUOUS`; see [21](21-evaluation.md) § 5 |
| IS-72 | Opportunity closure and state transition | See [34](34-state-machine.md) |
| IS-73 | Cost reconciliation per intervention | Actual cost, not estimated |

### 1.8 Learning (LEARN)

| # | Capability | Notes |
|---|---|---|
| IS-80 | Posterior updating of recovery/uplift estimates from observed outcomes | Bounded to predictor parameters only |
| IS-81 | Calibration monitoring | Brier score, reliability |
| IS-82 | Strategy versioning with rollback | Every decision records its `strategy_version` |

### 1.9 Proof and operability

| # | Capability | Notes |
|---|---|---|
| IS-90 | Append-only hash-chained audit trail | [16](16-audit-trail.md) |
| IS-91 | Synthetic dataset generator with documented behavioural model | [19](19-synthetic-dataset.md) |
| IS-92 | Batch benchmark with ≥ 4 baselines and an oracle ceiling | [20](20-benchmark.md) |
| IS-93 | Multi-seed evaluation with confidence intervals | [21](21-evaluation.md) |
| IS-94 | Metrics artefact generation | [37](37-metrics-dictionary.md) |
| IS-95 | Seven-screen operator UI | [25](25-ui-ux-spec.md) |
| IS-96 | Observability: metrics, structured logs, traces, alerts | [24](24-observability.md) |
| IS-97 | Deterministic reproducibility from a seed | [21](21-evaluation.md) § 3 |

---

## 2. Out of scope

Hard exclusions. Implementing any of these without an approved ADR is a specification violation.

### 2.1 Financial and safety exclusions

| # | Excluded | Why |
|---|---|---|
| OS-01 | Real-money transactions of any kind | No authorisation, no need, unacceptable risk |
| OS-02 | Live payment execution against any provider | `UNVERIFIED` API surface; simulator only |
| OS-03 | Real merchant credentials or API keys | Not required; would create a secrets-handling burden |
| OS-04 | Unrestricted autonomous financial action | Contradicts "bounded"; every action is gated |
| OS-05 | Uncapped discounts or incentives | Directly contradicts `RR-GUARD-005` |
| OS-06 | Uncapped or unconsented customer communication | Contradicts `RR-GUARD-001`…`004` |
| OS-07 | Autonomous legal or financial commitments (settlements, write-offs, credit terms) | Requires authority REVIVE does not have |
| OS-08 | Payment routing / switching against real rails | Would require verified provider capabilities |
| OS-09 | Unbounded agent loops or open-ended tool use | Contradicts boundedness; see [08](08-agent-architecture.md) § 7 |

### 2.2 Data exclusions

| # | Excluded | Why |
|---|---|---|
| OS-10 | Real customer PII | Synthetic only; see [22](22-security-and-privacy.md) |
| OS-11 | Real transaction data | Synthetic only |
| OS-12 | Any dataset scraped from a third party | Provenance risk |
| OS-13 | Storing raw payment credentials (PAN, CVV, mandate secrets) | Never stored, never logged, not needed |

### 2.3 Adjacent-product exclusions

| # | Excluded | Why |
|---|---|---|
| OS-20 | Fraud detection / chargeback prediction | Different objective; not revenue recovery |
| OS-21 | General cybersecurity functionality | The security work in this package serves the fintech problem only |
| OS-22 | Lending, credit scoring, BNPL | Different track |
| OS-23 | Accounting automation, ledger reconciliation, GST | Adjacent; not recovery |
| OS-24 | E-commerce product recommendation | Unrelated |
| OS-25 | General-purpose voice assistant behaviour | Voice is a bounded action, not an assistant |
| OS-26 | General financial advice | Not the product; regulatory risk |
| OS-27 | Merchant BI / exploratory analytics | UI exposes decisions, not free-form analysis |
| OS-28 | Customer support ticketing / CRM | Not recovery decisioning |
| OS-29 | Marketing campaign management | Superficially similar, structurally different: campaigns target cohorts for acquisition; REVIVE targets specific at-risk revenue for recovery |

### 2.4 Engineering exclusions (`HACKATHON-SCOPE`)

| # | Excluded | Why | Future doc |
|---|---|---|---|
| OS-30 | Multi-tenancy | One modelled merchant is sufficient to demonstrate the decision problem | [41](41-future-ideas.md) |
| OS-31 | Multi-currency | INR only | [41](41-future-ideas.md) |
| OS-32 | Horizontal scaling, sharding, queue infrastructure | Benchmark runs on one machine | [41](41-future-ideas.md) |
| OS-33 | Full authn/authz with real identity provider | Role simulation is enough for the demo | [41](41-future-ideas.md) |
| OS-34 | Real-time streaming ingestion at scale | Cycle-based batch decisioning is the architecture | [07](07-system-architecture.md) |
| OS-35 | Causal inference / true experimentation | Modelled uplift only, explicitly labelled | [11](11-counterfactual-engine.md) § 8 |
| OS-36 | Deep-learning models | Interpretability and reproducibility matter more here | [ADR-006](31-decision-records.md) |
| OS-37 | i18n beyond message-template language tags | Voice/message language is a template attribute | [41](41-future-ideas.md) |

---

## 3. Scope tiers

Every capability sits in exactly one tier. **Tier 1 is the definition of a passing build.**

| Tier | Meaning | Rule |
|---|---|---|
| **T1 — MVP / Required** | Without it, REVIVE does not satisfy Track 03 | Build first, build completely |
| **T2 — Recommended** | Materially strengthens the submission | Build only after all T1 is done and tested |
| **T3 — Optional** | Nice, demo-friendly, non-structural | Build only if T1 + T2 are done and time remains |
| **T4 — Future** | Explicitly not in this build | Goes to [41-future-ideas.md](41-future-ideas.md) |

The full capability × tier matrix is in
[05-functional-requirements.md § 9](05-functional-requirements.md).

**Tier discipline rule.** If time runs short, cut from T3 then T2. **Never** cut from T1 to
preserve a T3 item, however good the T3 item looks in a demo. The classic fatal version of this
mistake is cutting the benchmark to finish the voice call.

---

## 4. The scope firewall (binding procedure)

Run this whenever a feature idea appears — from a person, from a judge's suggestion, from an LLM's
own enthusiasm, or from the observation "this would be easy to add".

### Step 1 — State the idea in one sentence.

### Step 2 — Answer the gate question.

> **Does this directly improve REVIVE's ability to detect, diagnose, choose, execute, or measure
> bounded revenue recovery?**

- **NO** → Stop. Write it into [41-future-ideas.md](41-future-ideas.md) with one line of rationale.
  Do not build it. Do not build "a small version" of it.
- **YES** → Continue to Step 3.

### Step 3 — Name the requirement it serves.

Cite a specific `RR-*` ID from [05-functional-requirements.md](05-functional-requirements.md).

- **Cannot cite one** → The idea is not currently a requirement. Either propose a new requirement
  via ADR, or park it in [41-future-ideas.md](41-future-ideas.md). Do not build undocumented
  requirements.

### Step 4 — Check the exclusions.

Scan § 2. If the idea matches any `OS-*` row, it is excluded. An ADR is required to un-exclude it,
and the ADR must explain why the original exclusion was wrong.

### Step 5 — Assign a tier and check the discipline rule.

If the idea is T2 or T3 and any T1 item is incomplete, it is deferred. No exceptions.

### Step 6 — Check the objective.

> Does this make REVIVE better at maximising **incremental net recovered revenue**, or does it make
> REVIVE better at *appearing* sophisticated?

If the honest answer is the second, park it.

### Step 7 — Record the outcome.

Every firewall invocation that results in a scope change gets an ADR entry in
[31-decision-records.md](31-decision-records.md). Every rejection gets a line in
[41-future-ideas.md](41-future-ideas.md). Nothing changes scope silently.

---

## 5. Pre-adjudicated firewall cases

These have already been run through the procedure. The implementation phase must not re-open them
without an ADR.

| Idea | Verdict | Rationale |
|---|---|---|
| Hinglish voice recovery | **T3 — in scope as a bounded action** | Serves `RR-FUNC-022` as one action code. Must not become the product's identity. See [01](01-track-alignment.md) § 4 |
| Conversational merchant assistant ("ask REVIVE about my revenue") | **Rejected → T4** | Fails Step 2. Does not improve detection, choice, execution, or measurement |
| LLM writes the recovery message copy | **T2 — in scope, bounded** | Serves `RR-FUNC-024`. Copy is generated inside a template with a fixed variable set; the LLM never sets the incentive value. See `RR-GUARD-020` |
| LLM decides the discount percentage | **Rejected — hard violation** | Violates `RR-GUARD-020` and [README § C-7](README.md#c-7--the-deterministic-authority-rule) |
| Graph database for the leakage model | **Rejected → T4** | The relationships are shallow and fixed; a relational model is sufficient and reproducible. See [ADR-008](31-decision-records.md) |
| Reinforcement-learning policy trained end to end | **Rejected → T4** | Unreproducible in the timebox, uninterpretable, and would obscure the allocation logic that is the differentiator. See [29](29-tradeoffs.md) § 3 |
| Real Razorpay test-mode integration | **T3, conditional** | Only after the API surface is verified against official docs and only behind the existing adapter. See [36](36-razorpay-integration-assumptions.md) |
| Live webhook ingestion from a real provider | **Rejected → T4** | Unverifiable in the timebox; the cycle architecture does not need it |
| Chargeback / dispute prediction | **Rejected → T4** | Matches `OS-20` |
| Email deliverability optimisation | **Rejected → T4** | Fails Step 6 — sophistication without incremental recovery value |
| Multi-merchant tenancy | **Rejected → T4** | Matches `OS-30` |
| Slack / Teams notification integration | **Rejected → T4** | Fails Step 2; the approval queue already serves escalation |
| A second LLM to critique the first LLM | **Rejected → T4** | Fails Step 6; the deterministic policy engine already constrains the LLM, and does so verifiably |
| Predicting *future* churn / LTV | **Rejected → T4** | Different problem (retention, not recovery of specific at-risk revenue) |
| Dunning-sequence A/B testing framework | **Folded into T2 exploration budget** | The capped exploration allocation in [35](35-learning-engine.md) already covers the useful part |

---

## 6. Boundary cases worth stating explicitly

Some things sit close to the line. Frozen rulings:

| Boundary case | Ruling |
|---|---|
| Is contact-fatigue modelling in scope? | **Yes.** It is a cost term in the objective (`F(i,a)`) and a gate. Without it the system over-contacts. |
| Is customer LTV in scope? | **Only as a static input attribute** used in the fatigue term and value weighting. Predicting LTV is out. |
| Is the payment-degradation signal fraud detection? | **No.** It is a cohort failure-rate feature used to shift action fit. It makes no fraud claim about any customer. |
| Is the approval queue a workflow product? | **No.** It is one screen and one state; it exists to satisfy "compliant escalation". |
| Is the promise-to-pay tracker a CRM feature? | **No**, as scoped: it is a state on a receivable opportunity that suppresses contact until a date, then re-opens. No relationship management. |
| Is the LLM allowed to read raw customer records? | **No.** It receives a redacted, pseudonymised context object. See [22](22-security-and-privacy.md) § 6. |
| Can the Learning Engine change a policy limit? | **Never.** It may only update predictor parameters. Hard architectural boundary; see [35](35-learning-engine.md) § 7. |
| Can the allocator override a gate? | **Never.** Gates run after allocation *and* pre-filter before it; a gate verdict is final. |

---

## 7. Scope drift tripwires

If the implementation phase observes any of these, scope has drifted and must be corrected before
further work:

1. A new top-level module appears that is not in [08-agent-architecture.md](08-agent-architecture.md).
2. An LLM call appears in a code path that produces a monetary value or an allow/deny verdict.
3. The benchmark is reduced to fewer than the specified baselines or seeds.
4. `NO_ACTION` disappears from the candidate set.
5. A constraint is removed to make the allocator "work".
6. An action executes without an idempotency key.
7. A test is deleted or skipped to make a suite pass.
8. A metric is added that makes REVIVE look better without appearing in
   [37-metrics-dictionary.md](37-metrics-dictionary.md).
9. Any hard-coded value appears in a report that the harness did not compute.
10. The demo requires a manual step that the benchmark does not perform.
