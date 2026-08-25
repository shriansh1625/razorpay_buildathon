# REVIVE — Revenue Recovery Autopilot

**Razorpay Buildathon — Track 03: AI Revenue Recovery**
**Document package status: SPECIFICATION COMPLETE — NOT IMPLEMENTED**

---

## What this package is

This is the complete specification for REVIVE. It is the **source of truth** for the
implementation phase. No code exists yet. Nothing in this package describes something that
has been built, measured, or verified against a live system.

> **REVIVE is a bounded agentic decision system that allocates scarce recovery effort toward
> the highest expected incremental revenue and proves the value of its decisions through
> reproducible batch evaluation.**

The implementation phase MUST read [32-implementation-contract.md](32-implementation-contract.md)
before writing a single line of code.

---

## Reading order

**If you are the implementation agent, read in this order and do not skip:**

| # | Read | Why |
|---|------|-----|
| 1 | [32-implementation-contract.md](32-implementation-contract.md) | The rules you are bound by |
| 2 | [00-project-charter.md](00-project-charter.md) | What we are building and why |
| 3 | [03-scope-boundaries.md](03-scope-boundaries.md) | The scope firewall — consult on every feature idea |
| 4 | [05-functional-requirements.md](05-functional-requirements.md) | The numbered requirements you must satisfy |
| 5 | [07-system-architecture.md](07-system-architecture.md) | The shape of the system |
| 6 | [09](09-decision-engine.md) → [10](10-recovery-allocation.md) → [11](11-counterfactual-engine.md) | The intellectual core |
| 7 | [13](13-policy-and-guardrails.md) → [14](14-stopping-rules.md) → [16](16-audit-trail.md) | The safety core |
| 8 | [19](19-synthetic-dataset.md) → [20](20-benchmark.md) → [21](21-evaluation.md) | How value is proven |
| 9 | Everything else | Detail |

**If you are a judge or reviewer, read:**
[02-product-vision.md](02-product-vision.md) → [01-track-alignment.md](01-track-alignment.md) →
[10-recovery-allocation.md](10-recovery-allocation.md) → [20-benchmark.md](20-benchmark.md) →
[27-judging-criteria-mapping.md](27-judging-criteria-mapping.md) → [29-tradeoffs.md](29-tradeoffs.md)

---

## Full document index

### Foundation
- [00-project-charter.md](00-project-charter.md) — Mandate, objective, success criteria, definition of done
- [01-track-alignment.md](01-track-alignment.md) — Clause-by-clause proof of Track 03 alignment
- [02-product-vision.md](02-product-vision.md) — Product definition, thesis, differentiator, positioning
- [03-scope-boundaries.md](03-scope-boundaries.md) — In scope / out of scope / **scope firewall procedure**
- [04-principles-and-non-goals.md](04-principles-and-non-goals.md) — Engineering principles and anti-goals

### Requirements
- [05-functional-requirements.md](05-functional-requirements.md) — `RR-FUNC-*`, `RR-GUARD-*`, `RR-METRIC-*`, `RR-AUDIT-*`, `RR-BENCH-*`
- [06-nonfunctional-requirements.md](06-nonfunctional-requirements.md) — `RR-NFR-*`

### Architecture
- [07-system-architecture.md](07-system-architecture.md) — Components, cycle model, data flow, deployment
- [08-agent-architecture.md](08-agent-architecture.md) — Module/agent roster, permissions, tool grants
- [34-state-machine.md](34-state-machine.md) — Opportunity lifecycle states and legal transitions

### Decision core
- [09-decision-engine.md](09-decision-engine.md) — Objective function, decision pipeline, determinism rules
- [10-recovery-allocation.md](10-recovery-allocation.md) — The constrained allocator (central algorithm)
- [11-counterfactual-engine.md](11-counterfactual-engine.md) — Candidate comparison and ENRV computation
- [12-revenue-leakage-model.md](12-revenue-leakage-model.md) — Formal model of how revenue leaks
- [35-learning-engine.md](35-learning-engine.md) — Outcome-driven model updating, exploration budget

### Control and safety
- [13-policy-and-guardrails.md](13-policy-and-guardrails.md) — Gate architecture, full policy matrix
- [14-stopping-rules.md](14-stopping-rules.md) — Testable stopping criteria
- [15-execution-model.md](15-execution-model.md) — Bounded execution, idempotency, financial safety
- [16-audit-trail.md](16-audit-trail.md) — Hash-chained audit event schema, redaction rules
- [22-security-and-privacy.md](22-security-and-privacy.md) — Threat model and mitigations
- [23-failure-recovery.md](23-failure-recovery.md) — Failure catalogue with containment and escalation

### Data and interfaces
- [17-data-model.md](17-data-model.md) — Entities, keys, indexes, constraints, retention
- [18-api-contracts.md](18-api-contracts.md) — Service contracts, schemas, errors, idempotency
- [19-synthetic-dataset.md](19-synthetic-dataset.md) — Generator spec with explicit behavioural model
- [36-razorpay-integration-assumptions.md](36-razorpay-integration-assumptions.md) — **All Razorpay claims are UNVERIFIED**

### Proof of value
- [20-benchmark.md](20-benchmark.md) — Baselines, batch design, hidden outcome mechanism
- [21-evaluation.md](21-evaluation.md) — Methodology, statistics, honesty rules
- [37-metrics-dictionary.md](37-metrics-dictionary.md) — Every metric with an exact formula
- [24-observability.md](24-observability.md) — Metrics, logs, traces, alerts

### Experience and delivery
- [25-ui-ux-spec.md](25-ui-ux-spec.md) — Screen inventory with data bindings
- [26-demo-script.md](26-demo-script.md) — Five-minute demo contract
- [27-judging-criteria-mapping.md](27-judging-criteria-mapping.md) — Requirement → evidence matrix

### Engineering governance
- [28-risk-register.md](28-risk-register.md) — Risks, likelihood, impact, mitigation, owner
- [29-tradeoffs.md](29-tradeoffs.md) — Chosen vs rejected, with consequences
- [30-test-plan.md](30-test-plan.md) — Functional, edge, safety, evaluation tests
- [31-decision-records.md](31-decision-records.md) — `ADR-001` … architecture decision records
- [32-implementation-contract.md](32-implementation-contract.md) — Binding rules for the build phase
- [33-not-a-clone.md](33-not-a-clone.md) — Architectural differentiation analysis
- [38-traceability-matrix.md](38-traceability-matrix.md) — Requirement → component → contract → test → demo
- [39-glossary.md](39-glossary.md) — Frozen vocabulary
- [40-open-questions.md](40-open-questions.md) — `UNKNOWN` items requiring a decision
- [41-future-ideas.md](41-future-ideas.md) — Parked ideas — **not part of this build**

---

## Frozen conventions

Every document in this package obeys the following. The implementation phase MUST obey them too.
Changing any of these requires a new ADR in [31-decision-records.md](31-decision-records.md).

### C-1 · Certainty labels

Every non-trivial claim in this package carries one of these labels. Absence of a label means
the statement is a definition internal to REVIVE (i.e. `KNOWN` by construction).

| Label | Meaning |
|-------|---------|
| `KNOWN` | Stated by the challenge brief, stated by the project owner, or verified from an authoritative source |
| `ASSUMPTION` | Needed to proceed, not verified, may be wrong |
| `PROPOSED` | An engineering choice made by this specification; may be changed with an ADR |
| `OPTIONAL` | Adds value, not required for a passing submission |
| `HACKATHON-SCOPE` | Deliberately simplified because this is a prototype |
| `FUTURE / NOT IMPLEMENTED` | Explicitly excluded from this build |
| `UNVERIFIED` | An external-system claim that must be checked against official docs before code depends on it |
| `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION` | No decision has been made; see [40-open-questions.md](40-open-questions.md) |

**Never silently promote a label upward.** `ASSUMPTION` does not become `KNOWN` because it was
convenient. `UNVERIFIED` does not become `KNOWN` because an implementation compiled.

### C-2 · Money

- Currency: **INR only** (`HACKATHON-SCOPE`; multi-currency is `FUTURE / NOT IMPLEMENTED`).
- All monetary values are **integer paise** (1 INR = 100 paise). No floats anywhere in storage,
  transport, or arithmetic that determines an action.
- Field naming: `*_paise` suffix is mandatory on every monetary field.
- Probabilities and rates are floats in `[0, 1]`.
- Rounding rule: monetary results of probability arithmetic use **banker's rounding to integer
  paise**, applied once, at the boundary where a value is persisted.

### C-3 · Time

- All persisted timestamps are **ISO-8601 with explicit UTC offset**, e.g. `2026-03-05T14:30:00Z`.
- Merchant-local reasoning (quiet hours, business days, salary-cycle effects) uses
  `Asia/Kolkata` (`ASSUMPTION`: the modelled merchant is India-domiciled).
- The benchmark runs on **simulated time**. A run has a virtual clock; there is no dependence on
  wall-clock time. See [20-benchmark.md](20-benchmark.md).
- Durations are integer seconds unless a field name says otherwise (`*_hours`, `*_days`).

### C-4 · Identifiers

Format: `<prefix>_<26-char ULID>`. ULIDs are lexicographically sortable by creation time.

| Prefix | Entity |
|--------|--------|
| `opp_` | RevenueOpportunity |
| `sig_` | Signal (ingested event) |
| `dg_` | Diagnosis |
| `cand_` | ActionCandidate |
| `dec_` | Decision |
| `iv_` | Intervention (an executed action instance) |
| `out_` | Outcome |
| `aud_` | AuditEvent |
| `cyc_` | RecoveryCycle |
| `cust_` | Customer (pseudonymous) |
| `txn_` | Transaction |
| `sub_` | Subscription |
| `chk_` | CheckoutSession |
| `inv_` | Invoice / receivable |
| `pol_` | PolicyPack |
| `bud_` | Budget / resource pool |
| `strat_` | StrategyVersion |
| `bench_` | BenchmarkRun |

In the benchmark, ULIDs are generated from the run's seeded PRNG so that identifiers are
reproducible across runs (`PROPOSED`; see [34-state-machine.md](34-state-machine.md) note on
determinism).

### C-5 · The frozen objective

REVIVE maximises **expected incremental net recovered revenue**, written `ENRV`.

For opportunity `i` and candidate action `a`:

```
ENRV(i, a) =   u(i, a) · V(i) · m
             − c(a)
             − p(i, a) · d(i, a)
             − λ_f · F(i, a)
```

| Term | Meaning |
|------|---------|
| `V(i)` | Recoverable value at risk, paise |
| `p(i, a)` | P(recovered within horizon H \| action `a` applied) |
| `p(i, ∅)` | P(recovered within horizon H \| **no action**) — the natural-recovery baseline |
| `u(i, a)` | **Uplift** = `p(i, a) − p(i, ∅)`. Can be negative. |
| `m` | Merchant net-retention factor on recovered gross (default `1.0`, `ASSUMPTION`) |
| `c(a)` | Unconditional direct cost of attempting `a`, paise (SMS fee, call cost, human minutes) |
| `d(i, a)` | Incentive cost if `a` includes an incentive, paise — **charged only on success**, hence `p(i,a) · d(i,a)` |
| `F(i, a)` | Modelled contact-fatigue externality (future value destroyed), paise |
| `λ_f` | Fatigue aversion weight, merchant-configurable (default `1.0`, `PROPOSED`) |

`ENRV(i, ∅) = 0` by definition. An action is only worth taking if `ENRV(i, a) > ε` where `ε` is
the merchant's minimum-justification threshold.

**The single most important consequence:** REVIVE is scored on `u`, not `p`. Contacting a
customer who would have paid anyway earns REVIVE nothing. This is what stops the system from
degenerating into a blast-everyone engine, and it is enforced in the metrics
([37-metrics-dictionary.md](37-metrics-dictionary.md), `M-14 Wasted Intervention Rate`).

Full derivation, assumptions and limits: [09-decision-engine.md](09-decision-engine.md) and
[11-counterfactual-engine.md](11-counterfactual-engine.md).

### C-6 · The frozen loop

```
SEE → UNDERSTAND → SIMULATE → PRIORITIZE → GUARD → ACT → VERIFY → LEARN
```

Every component in this specification belongs to exactly one phase of this loop and says which.
See [07-system-architecture.md](07-system-architecture.md).

### C-7 · The deterministic-authority rule

> **No LLM output may become a number that moves money.**

LLMs produce categorical labels, ranked hypotheses, structured evidence references, and
human-readable text. Deterministic code produces every probability, every monetary amount, every
budget decision, and every allow/deny verdict. This is `RR-GUARD-020` and it is not negotiable.
Rationale in [22-model-boundary](09-decision-engine.md#5-the-deterministic-authority-boundary)
and [ADR-004](31-decision-records.md).

### C-8 · Honesty rules for this package

1. No performance number appears anywhere in this package. Not one. Every metric is defined by
   formula, with no illustrative value that could be mistaken for a result.
2. Where an example is needed, it is labelled `ILLUSTRATIVE — NOT A RESULT` and uses obviously
   synthetic round numbers.
3. No Razorpay endpoint, parameter, field name, error code, or product behaviour is asserted as
   fact. See [36-razorpay-integration-assumptions.md](36-razorpay-integration-assumptions.md).
4. The word "production" is never used to describe what this build achieves.

---

## Status of this package

| Aspect | Status |
|--------|--------|
| Specification | Complete for the defined MVP scope |
| Source code | **None. Not started.** |
| Benchmark results | **None. No run has occurred.** |
| Razorpay integration | **None. API surface unverified.** |
| Open decisions | See [40-open-questions.md](40-open-questions.md) |

---

*Last structural change: initial authoring. Package owner: project owner. Change control:
material changes require an ADR entry in [31-decision-records.md](31-decision-records.md).*
