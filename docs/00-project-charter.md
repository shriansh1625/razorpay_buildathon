# 00 · Project Charter

**Project:** PAYVANTA — Autonomous Revenue Recovery Intelligence
**Event:** Razorpay Buildathon, Track 03 — AI Revenue Recovery
**Phase of this document:** Specification. No implementation exists.

---

## 1. Mandate

Build an agent that **detects revenue at risk, determines the right intervention, and executes a
bounded recovery workflow** — and prove, on a batch, that it recovered more money than a sensible
baseline would have, while respecting stopping rules, compliant escalation, and a full audit
trail.

`KNOWN` — this mandate is the Track 03 brief supplied by the project owner and reproduced
verbatim in [01-track-alignment.md](01-track-alignment.md).

---

## 2. Problem statement (exact)

A merchant loses revenue continuously and in small pieces. A card declines for insufficient
funds. A checkout is abandoned at the OTP screen. A subscription mandate fails on its third
renewal. A B2B invoice slips thirty days past due. Individually each loss is small enough to
ignore; collectively they are a material fraction of revenue.

The merchant's response is constrained in ways that make the problem genuinely hard:

1. **Recovery effort is finite.** There is a budget for incentives, a cap on how many SMS or
   WhatsApp messages can be sent, a limited number of voice-call minutes, a small number of
   human operators who can chase receivables, and a hard limit on how many times a payment
   instrument may be retried.
2. **Effort has cost.** Every message costs money. Every discount costs margin. Every unnecessary
   contact costs customer goodwill — a cost that does not appear on any invoice.
3. **Some revenue recovers by itself.** A meaningful share of abandoned checkouts and failed
   payments complete without any intervention. Effort spent on those customers produces zero
   incremental revenue while still incurring full cost.
4. **Actions are irreversible and regulated.** You cannot un-send a message, un-charge a card, or
   un-offer a discount. Communication is subject to consent and timing rules.

So the operationally correct question is **not**:

> "This payment failed — what should I do about it?"

It is:

> "I have 500 opportunities at risk right now, ₹40,000 of recovery budget, 800 SMS credits, 60
> minutes of voice capacity, 4 human review slots, and a policy that forbids a third contact.
> **Where do I spend the next unit of effort so that it produces the most additional net
> revenue?**"

That is a constrained allocation problem over a portfolio of opportunities. It is the problem
PAYVANTA solves.

---

## 3. Product definition (locked)

> PAYVANTA is an autonomous revenue-recovery intelligence platform that continuously identifies revenue at
> risk, diagnoses why it is at risk, evaluates possible recovery actions, allocates limited
> recovery effort toward the highest-value opportunities, executes bounded interventions, measures
> actual recovery outcomes, and learns from those outcomes.

> PAYVANTA does not merely ask what to do when one payment fails. It decides **where the merchant's
> next unit of recovery effort is most likely to create incremental net revenue.**

Both statements are locked by the project owner and may not be reinterpreted by the
implementation phase.

---

## 4. Primary objective

**Maximise expected incremental net recovered revenue (`ENRV`), subject to merchant constraints.**

The formal statement is frozen in [README.md § C-5](README.md#c-5--the-frozen-objective) and
derived in [09-decision-engine.md](09-decision-engine.md).

### 4.1 Explicitly rejected objectives

The following are **not** the objective, and optimising for them is a defect:

| Rejected objective | Why it is wrong |
|---|---|
| Number of retries executed | Rewards churn on the payment rails, not revenue |
| Number of customers contacted | Rewards spam; ignores fatigue cost and consent |
| Raw recovery conversion % | Counts natural recoveries as wins; a do-nothing policy can score well |
| Model probability accuracy alone | A perfectly calibrated model that drives bad allocation is worthless |
| Number of agent actions / tool calls | Rewards activity theatre |
| LLM confidence | Not a measurement of anything financial |
| Gross recovered revenue alone | Ignores intervention cost, incentive cost and fatigue |

### 4.2 The one-sentence success test

> On a fixed, pre-registered batch of synthetic opportunities, under identical resource budgets
> and identical policy constraints, the REVIVE recovery policy produces **more net recovered revenue than the
> strongest non-trivial baseline**, with **zero policy violations**, a **complete audit trail for
> every action**, and results **reproducible from a seed**.

If that sentence is not true at the end of the build, the build has failed, regardless of how the
UI looks.

---

## 5. Success criteria

Each criterion is measurable and maps to a requirement ID.

| # | Criterion | Measured by | Requirement |
|---|---|---|---|
| SC-1 | Detects all four risk classes (payment failure, checkout abandonment, subscription/mandate failure, overdue receivable) | Detection recall against generator ground truth, per class | `RR-FUNC-001` |
| SC-2 | Produces a ranked, reasoned diagnosis for every opportunity it acts on | 100% of acted opportunities have a persisted `Diagnosis` with evidence refs | `RR-FUNC-010` |
| SC-3 | Evaluates ≥ 2 candidate actions plus `NO_ACTION` for every opportunity considered | Count of `ActionCandidate` rows per considered opportunity ≥ 3 | `RR-FUNC-020` |
| SC-4 | Allocates under **at least four** simultaneous binding constraints | Allocation run report shows ≥ 4 constraints with non-zero shadow price or exhaustion | `RR-FUNC-030` |
| SC-5 | Chooses `NO_ACTION` where it is economically correct, and can defend it | `NO_ACTION` share > 0 on the benchmark batch, with per-case reason codes | `RR-FUNC-040` |
| SC-6 | Zero policy violations across the benchmark | `M-16 Policy Violation Count` = 0 | `RR-GUARD-001` … `RR-GUARD-020` |
| SC-7 | Every stopping rule demonstrably fires at least once and is honoured | Stopping-rule coverage report; all 11 rules exercised | `RR-FUNC-050` |
| SC-8 | Beats the strongest non-trivial baseline on net recovered revenue | Paired multi-seed comparison with confidence interval | `RR-BENCH-001` … `RR-BENCH-006` |
| SC-9 | Beats it on capital efficiency, not just gross | `M-11 Recovery ROI` and `M-12 Cost per Recovered Rupee` | `RR-METRIC-011`, `RR-METRIC-012` |
| SC-10 | Complete tamper-evident audit trail | Hash chain verifies; every `Intervention` traceable to a `Decision` and an `AuditEvent` | `RR-AUDIT-001` … `RR-AUDIT-008` |
| SC-11 | Reproducible end to end from a seed | Two runs at the same seed produce byte-identical metric output | `RR-NFR-020` |
| SC-12 | Honest reporting, including its own failures | Evaluation report includes wasted interventions, negative-uplift actions, and oracle gap | `RR-METRIC-014`, `RR-METRIC-020` |

---

## 6. Deliverables

| Deliverable | Description | Status |
|---|---|---|
| D-1 | This specification package | **Complete** |
| D-2 | Synthetic data generator | Not started |
| D-3 | PAYVANTA decision engine (SEE → LEARN) | Not started |
| D-4 | Policy / guardrail engine | Not started |
| D-5 | Bounded execution layer with simulated adapters | Not started |
| D-6 | Audit store | Not started |
| D-7 | Benchmark harness with baselines | Not started |
| D-8 | Evaluation report generator | Not started |
| D-9 | Operator UI (7 screens) | Not started |
| D-10 | Demo script + recorded run | Not started |

---

## 7. Constraints

| Constraint | Detail |
|---|---|
| No real money | Every money-moving action executes against a simulator. See [15-execution-model.md](15-execution-model.md). `HACKATHON-SCOPE` |
| No real customer data | Synthetic only. See [19-synthetic-dataset.md](19-synthetic-dataset.md). |
| No verified Razorpay integration | Razorpay API surface is `UNVERIFIED`. Adapter interface only. See [36-razorpay-integration-assumptions.md](36-razorpay-integration-assumptions.md). |
| Hackathon timebox | Favour the smallest implementation that satisfies the spec. See [29-tradeoffs.md](29-tradeoffs.md). |
| Deterministic reproducibility | Required, and it constrains the design (no wall-clock, no unseeded randomness). |
| Demo runs on a laptop | No cloud dependency for the core benchmark. `PROPOSED` |

---

## 8. Non-goals

Restated in full in [04-principles-and-non-goals.md](04-principles-and-non-goals.md). Headline
non-goals:

- PAYVANTA is not a chatbot, a dashboard, a CRM, a fraud system, or a generic multi-agent demo.
- PAYVANTA does not take unbounded autonomous financial action.
- PAYVANTA does not claim causal inference it has not implemented.
- PAYVANTA does not claim production readiness.

---

## 9. Definition of done

The build is done when **all** of the following hold. This is a checklist, not a spirit.

1. `docs/` is unchanged in intent — every deviation is recorded in
   [31-decision-records.md](31-decision-records.md) with rationale.
2. Every `MUST` requirement in [05-functional-requirements.md](05-functional-requirements.md) has
   a passing test named after its requirement ID.
3. The benchmark runs from a single documented command, at a documented seed, and emits a metrics
   artefact.
4. The benchmark runs over **≥ 20 seeds** and reports a paired comparison with a confidence
   interval, not a single lucky run. See [21-evaluation.md](21-evaluation.md).
5. `M-16 Policy Violation Count` is `0` on every seed. A non-zero value is a build failure, not a
   finding.
6. The audit hash chain verifies for every run.
7. The evaluation report includes at least one section describing where the REVIVE policy performed **worse**
   than a baseline or wasted effort.
8. No fabricated number appears in any artefact, slide, or README.
9. The demo executes end to end without manual intervention or hidden steps.
10. [38-traceability-matrix.md](38-traceability-matrix.md) has no `GAP — MUST BE RESOLVED` rows,
    or each remaining gap is explicitly acknowledged in the submission.

---

## 10. Governance

| Role | Held by | Authority |
|---|---|---|
| Product owner | Project owner | Scope, product definition, final submission |
| Specification | This package | Source of truth for the build |
| Implementation phase | Coding agent / developer | May not change scope; must record deviations |
| Scope arbitration | [03-scope-boundaries.md](03-scope-boundaries.md) § Scope firewall | Binding procedure for every feature idea |
| Architecture change control | [31-decision-records.md](31-decision-records.md) | An ADR is required to change a frozen convention |

### 10.1 Escalation

If the implementation phase finds this specification **ambiguous**, it must stop and ask, and log
the question in [40-open-questions.md](40-open-questions.md). If it finds this specification
**wrong**, it must say so explicitly and propose an ADR — not silently work around it.

Silently diverging from this specification is the single failure mode this charter most wants to
prevent.
