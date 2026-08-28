# 04 · Principles and Non-Goals

Principles are load-bearing. Each one below is written so that a reviewer can point at code and say
"this violates P-*n*". Vague principles are useless, so every principle has a **test**: an
observable condition that reveals a violation.

---

## 1. Engineering principles

### P-1 · Value over activity

PAYVANTA optimises incremental net recovered revenue, never the volume of things it did.

**Test.** Any metric that counts actions, messages, retries, or tool calls appears only as a *cost*
in reports, never as a success measure. If a report headline is a count of interventions, this
principle is violated.

---

### P-2 · Uplift over conversion

Credit is only taken for the difference an action made.

**Test.** No report or screen displays a recovery rate without the corresponding
natural-recovery baseline next to it. `M-10 Incremental Net Recovery` is always the headline;
`M-06 Gross Recovered` is never presented alone.

---

### P-3 · Determinism owns money

Every monetary amount, probability, budget verdict, and allow/deny decision is produced by
deterministic code. LLMs produce categories, hypotheses, evidence references, and prose.

**Test.** Grep the codebase for LLM invocations. Every call site must be traceable to a field that
is (a) a categorical label from a closed set, (b) a ranked list of enum values, (c) a reference to
existing evidence rows, or (d) human-readable text with no downstream numeric use. Any other use is
a violation. This is `RR-GUARD-020`.

**Rationale.** Not distrust of LLMs — a reproducibility and accountability requirement. A number
that cannot be re-derived cannot be audited, and a number that varies between runs cannot be
benchmarked.

---

### P-4 · Bounded by construction, not by convention

Limits are enforced by a component with authority, not by every component remembering to check.

**Test.** There is exactly one code path through which an action can reach an adapter, and it
passes through the policy engine. Attempting to execute an action outside that path fails a test
named `RR-GUARD-*`.

---

### P-5 · Reversibility awareness

The system treats irreversible effects (money moved, message sent, incentive offered) as
categorically different from reversible ones (a record written, a score computed).

**Test.** Every action code in [11-counterfactual-engine.md § 3](11-counterfactual-engine.md)
declares `reversible: false` where applicable, and every irreversible action requires an
idempotency key, a budget reservation, and an audit event **before** the adapter is invoked, not
after.

---

### P-6 · Explainability is a data structure, not a paragraph

Every decision is reconstructible from stored rows: the candidates considered, their prices, the
binding constraint, the gate verdicts, the chosen action. The natural-language explanation is a
*rendering* of that structure and is never the only record.

**Test.** Delete every LLM-generated text field from the database. Every screen in
[25-ui-ux-spec.md](25-ui-ux-spec.md) must still be able to explain every decision.

---

### P-7 · Honest measurement

The evaluation is designed to be able to show REVIVE losing.

**Test.** The evaluation report contains: wasted interventions, negative-uplift actions taken,
missed profitable opportunities, the oracle gap, and per-seed results including the worst seed. A
report that shows only aggregate wins violates this principle. See
[21-evaluation.md § 8](21-evaluation.md).

---

### P-8 · Reproducibility is a design constraint

Reproducibility is not a testing nicety; it dictates architecture. No wall-clock dependence, no
unseeded randomness, no non-deterministic iteration order, no dependence on external services in
the benchmark path.

**Test.** Two benchmark runs at the same seed produce byte-identical metric artefacts. This is
`RR-NFR-020` and it is a build-blocking test.

**Consequence.** LLM calls cannot appear in the benchmark's decision path unless their outputs are
cached and seed-keyed, because LLM outputs are not reproducible. See
[09-decision-engine.md § 6](09-decision-engine.md) for how this is resolved.

---

### P-9 · Smallest sufficient implementation

Prefer the simplest mechanism that satisfies the specification and its tests. Sophistication that
does not improve `ENRV` or provability is cost.

**Test.** Every module in the codebase maps to a row in
[08-agent-architecture.md](08-agent-architecture.md). Every table maps to a row in
[17-data-model.md](17-data-model.md). Anything else is unjustified.

---

### P-10 · Traceability

Every feature traces to a requirement; every requirement traces to a test and to demo or benchmark
evidence.

**Test.** [38-traceability-matrix.md](38-traceability-matrix.md) has no orphan rows in either
direction — no requirement without evidence, no code without a requirement.

---

### P-11 · Fail closed

When the system is uncertain, degraded, or inconsistent, it does less, not more. An unavailable
predictor, a stale state, an ambiguous outcome, or an exhausted budget results in deferral or
no-action — never in an unbounded or unverified action.

**Test.** For every failure mode in [23-failure-recovery.md](23-failure-recovery.md), the specified
containment is deferral, denial, or escalation. No failure mode's containment is "proceed anyway".

---

### P-12 · Separation of learning from authority

The learning system may change what REVIVE *believes*. It may never change what REVIVE is
*allowed to do*.

**Test.** The `PolicyPack` and budget tables have no write path from the Learning Engine. Attempting
one fails a test. See [35-learning-engine.md § 7](35-learning-engine.md).

**Rationale.** A learner that can relax its own constraints will, given a reward signal, learn to
relax them. This is the highest-severity architectural risk in the system (`R-03` in
[28-risk-register.md](28-risk-register.md)).

---

### P-13 · Pseudonymity by default

No component receives more identity than it needs. The LLM layer receives pseudonymous identifiers
and derived attributes, never raw contact details.

**Test.** The context object passed to any LLM call contains no field on the deny-list in
[22-security-and-privacy.md § 6](22-security-and-privacy.md). Enforced by a serialiser, not by
convention.

---

### P-14 · The audit trail is append-only and tamper-evident

Audit events are never updated or deleted, and the chain can be verified.

**Test.** The audit table has no `UPDATE` or `DELETE` path. Chain verification is a test that runs
on every benchmark run.

---

### P-15 · Constraints are visible

If a constraint bound, the system says so, in the UI and in the report. Hidden truncation is
forbidden.

**Test.** Any code path that caps, samples, top-N's, or truncates emits a structured log line and a
report field naming what was dropped and why. A silent `[:100]` is a violation.

---

## 2. Product principles

### PP-1 · "Do nothing" is a decision, and it is measured

Restated from [02-product-vision.md § 6](02-product-vision.md) because it is frequently the
correct answer and frequently forgotten. `NO_ACTION` is priced, chosen, recorded with a reason,
and counted — and the cost of choosing it wrongly is reported as `M-19 Missed Opportunity Value`.

---

### PP-2 · The merchant is always able to see and stop

Every autonomous decision is inspectable before and after the fact, and a global stop exists.

**Test.** The UI exposes, for any opportunity, the full candidate set with prices and gate verdicts.
A `HALT` control suspends all execution and is honoured within one cycle.

---

### PP-3 · Customer tolerance is a resource on the balance sheet

Contact fatigue is priced (`λ_f · F(i,a)`), capped (`RR-GUARD-003`), and reported
(`M-13 Contact Rate`, `M-13b Fatigue Index`). It is not an afterthought or a compliance checkbox.

---

### PP-4 · The system never claims more than it has proven

Language discipline: "modelled", "estimated", "candidate cause", "on synthetic data" are used
where they apply. "Proven", "causal", "production-ready", "guaranteed" are not used at all.

**Test.** A vocabulary check over all user-facing strings, slide text, and README content.

---

### PP-5 · Escalation is a feature, not a failure

Routing a case to a human is a correct outcome for high-value, high-uncertainty, or
policy-sensitive cases. It is counted and surfaced, not hidden.

---

## 3. Anti-goals

These are the behaviours REVIVE is designed to make structurally difficult. Each has a named
structural defence.

| # | Anti-goal | Structural defence |
|---|---|---|
| AG-01 | An LLM deciding a financial amount | `RR-GUARD-020`; deterministic pricing layer; P-3 test |
| AG-02 | Unbounded agent loops | Fixed cycle with a step budget; no self-directed tool discovery; [08](08-agent-architecture.md) § 7 |
| AG-03 | Acting on everything because acting looks productive | Uplift-based objective; `ε` threshold; fatigue cost; contact caps |
| AG-04 | Double-charging or double-messaging | Mandatory idempotency keys; two-phase budget reservation; duplicate-suppression gate |
| AG-05 | Metric theatre / cherry-picked wins | Pre-registered batch; ≥ 4 baselines; ≥ 20 seeds; CI; mandatory failure reporting; [21](21-evaluation.md) § 8 |
| AG-06 | Fabricated results | No number in this package; every reported figure traces to a benchmark artefact; `RR-BENCH-007` |
| AG-07 | Unsupported Razorpay claims | [36](36-razorpay-integration-assumptions.md); every claim labelled `UNVERIFIED`; adapter isolation |
| AG-08 | Agents for the sake of agents | Every module must have a measurable output and cite a requirement; P-9 test |
| AG-09 | A pretty dashboard with no engine behind it | Every screen binds to decision artefacts; P-6 test (delete the prose, screens still work) |
| AG-10 | Guardrails that can be bypassed for convenience | Single execution path; gate verdicts final; policy tables not writable by the learner |
| AG-11 | Losing the audit trail under load or on failure | Audit event written before adapter invocation; append-only; chain verified per run |
| AG-12 | Scope creep into adjacent fintech products | [03-scope-boundaries.md § 4](03-scope-boundaries.md) firewall; pre-adjudicated cases |
| AG-13 | Claiming causal inference | [11](11-counterfactual-engine.md) § 8 limits section; vocabulary discipline PP-4 |
| AG-14 | A benchmark the model can see through | Hidden outcome mechanism; train/eval split; generator parameters withheld from the policy; [20](20-benchmark.md) § 5 |
| AG-15 | Silent truncation making coverage look complete | P-15; every cap logged and reported |
| AG-16 | Cutting the benchmark to finish a demo feature | Tier discipline rule; `SC-8` is build-blocking |

---

## 4. Principle conflicts and their resolution

Principles conflict. Frozen resolutions, so the implementation phase does not have to improvise:

| Conflict | Resolution |
|---|---|
| P-8 reproducibility vs. LLM reasoning quality | Reproducibility wins in the benchmark path. LLM outputs are cached and keyed by `(seed, opportunity_id, prompt_version)`; a benchmark run may not make uncached LLM calls. See [09](09-decision-engine.md) § 6. |
| P-9 smallest implementation vs. P-7 honest measurement | Honest measurement wins. The evaluation harness is allowed to be the most elaborate part of the system. |
| P-11 fail closed vs. `SC-8` beating the baseline | Fail closed wins. A run that defers because of a degraded predictor and therefore scores lower is correct behaviour, and the report says so. |
| P-3 determinism vs. handling novel failure reasons | Determinism wins for pricing. Novel free-text reasons are classified by the LLM into the **existing closed taxonomy**, or into `UNCLASSIFIED`, which routes to a conservative default action set. The LLM never invents a new reason code that pricing depends on. |
| P-6 explainability vs. model sophistication | Explainability wins. This is the stated reason for rejecting deep models (`OS-36`, [ADR-006](31-decision-records.md)). |
| PP-2 human visibility vs. autonomy | Both hold: REVIVE acts autonomously within thresholds and escalates above them. The threshold is merchant policy, not a system preference. |
| P-15 visible constraints vs. clean UI | Visibility wins, but it may be secondary-level UI (a badge, an expandable panel) rather than a modal. |

---

## 5. What "good" looks like at review time

A reviewer should be able to do all of the following in under fifteen minutes:

1. Pick any executed intervention and see the full candidate set it beat, with prices.
2. Find the binding constraint for that cycle and its shadow price.
3. Find a case where REVIVE chose `NO_ACTION` and read why.
4. Find a case where a gate denied an action the ranker wanted, and confirm no action was taken.
5. Find a case where a human approval was required, and see the queue entry.
6. Verify the audit hash chain.
7. Re-run the benchmark at the published seed and get identical numbers.
8. Read a section of the report that describes REVIVE performing badly.

If any of those is not possible, the build has a principle violation, not a missing feature.
