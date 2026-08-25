# 31 · Decision Records

Architecture Decision Records (ADRs) document the major decisions that shaped REVIVE. Changing a
frozen convention requires a new ADR in this document.

---

## 1. ADR format

Every ADR uses the following structure:

```
### ADR-NNN · Title

| Field     | Value |
|-----------|-------|
| Status    | ACCEPTED | PROPOSED | SUPERSEDED | DEPRECATED
| Date      | YYYY-MM-DD
| Context   | Why a decision was needed
| Decision  | What was decided
| Alternatives | What was considered and rejected
| Rationale | Why this alternative was chosen
| Consequences | What follows from this decision
| Follow-up | Any actions required
| Reference | Links to source documents
```

### Decision ID format

`ADR-NNN` where `NNN` is a three-digit zero-padded sequential number. IDs are never reused.

### Status definitions

| Status | Meaning |
|---|---|
| `ACCEPTED` | Decision is in effect |
| `PROPOSED` | Under discussion; not yet binding |
| `SUPERSEDED` | Replaced by a later ADR (cite the replacement) |
| `DEPRECATED` | No longer relevant but retained for history |

---

## 2. Seed ADRs

The following ADRs capture the major already-decided REVIVE architecture decisions. They reference
the source documents where the decisions were originally specified.

---

### ADR-001 · Cycle-based batch architecture over event-driven

| Field | Value |
|---|---|
| **Status** | ACCEPTED |
| **Date** | Specification phase |
| **Context** | REVIVE must allocate recovery effort across a portfolio of opportunities under shared resource constraints. The Track 03 bar asks for "measured money recovered across a batch" |
| **Decision** | REVIVE uses a cycle-based batch decision model. Signals are ingested continuously; decisioning is periodic. The entire opportunity pool is priced and solved together per cycle |
| **Alternatives** | (A) Event-driven per-event processing: react to each signal as it arrives. Rejected because it cannot compare opportunities, cannot allocate shared budgets, and cannot produce shadow prices |
| **Rationale** | Allocation requires comparison; budgets are shared; constraints bind across cases. A batch-level solve is the only architecture that can demonstrate the product's differentiator |
| **Consequences** | An urgent opportunity may wait up to one cycle (time decay is priced). Determinism is achievable (a cycle is a pure function of state + policy + strategy + clock + seed) |
| **Follow-up** | Optional: fast-lane cycle for `CHECKOUT_ABANDONMENT` (parked in [41](41-future-ideas.md)) |
| **Reference** | [07-system-architecture.md § 1](07-system-architecture.md), [29-tradeoffs.md § 3](29-tradeoffs.md) |

---

### ADR-002 · ENRV as the frozen objective

| Field | Value |
|---|---|
| **Status** | ACCEPTED |
| **Date** | Specification phase |
| **Context** | REVIVE needs a single optimisation objective that measures incremental value and is not gameable by contacting everyone |
| **Decision** | Maximise expected incremental net recovered revenue (ENRV), defined as `u(i,a) · V(i) · m − c(a) − p(i,a)·d(i,a) − λ_f·F(i,a)` where `u = p(i,a) − p(i,∅)` |
| **Alternatives** | (A) Maximise gross recovered revenue — gameable by ignoring natural recovery. (B) Maximise number of successful actions — rewards activity, not value. (C) Maximise recovery rate — maximised by detecting less |
| **Rationale** | Uplift-based objective is the only one that stops the system from degenerating into a blast-everyone engine. Subtracting costs ensures capital efficiency |
| **Consequences** | REVIVE is scored on `u`, not `p`. Contacting a customer who would have paid anyway earns nothing. `ENRV(i,∅) = 0` by definition, so no-action is always a valid baseline |
| **Follow-up** | None — objective is frozen. Changing it requires a new ADR |
| **Reference** | [README § C-5](README.md), [09-decision-engine.md](09-decision-engine.md), [11-counterfactual-engine.md](11-counterfactual-engine.md) |

---

### ADR-003 · Three agents, eighteen deterministic modules

| Field | Value |
|---|---|
| **Status** | ACCEPTED |
| **Date** | Specification phase |
| **Context** | Multi-agent architectures are easy to proliferate. REVIVE needs LLMs where they add genuine value, and deterministic logic where reproducibility and safety require it |
| **Decision** | Two LLM-invoking agents (C-05 Root Cause Analyst, C-10 Copy Composer), one orchestrating agent (C-23 Cycle Orchestrator), eighteen deterministic modules. Every module must pass the anti-proliferation test |
| **Alternatives** | Six rejected agents: Negotiation Agent (violates `RR-GUARD-020`), Strategy Agent (duplicates allocator), Critic Agent (unverifiable), Planner Agent (cycle is fixed), Customer Persona Agent (must be calibrated), Router Agent (channel is an action attribute) |
| **Rationale** | The ratio of deterministic to LLM modules is intentional. It is the direct consequence of `RR-GUARD-020` (no LLM output becomes a number that moves money) |
| **Consequences** | LLMs cannot influence pricing, allocation, or policy. Novel failure codes fall back to `UNCLASSIFIED`. Copy generation can be fully disabled with no functional loss |
| **Follow-up** | None |
| **Reference** | [08-agent-architecture.md](08-agent-architecture.md) |

---

### ADR-004 · No LLM output may become a number that moves money

| Field | Value |
|---|---|
| **Status** | ACCEPTED |
| **Date** | Specification phase |
| **Context** | LLMs produce useful reasoning but are nondeterministic, hallucination-prone, and not auditable for numeric accuracy. Financial actions require verifiable computation |
| **Decision** | `RR-GUARD-020`: LLMs produce categorical labels, ranked hypotheses, structured evidence references, and human-readable text. Deterministic code produces every probability, monetary amount, budget decision, and allow/deny verdict |
| **Alternatives** | (A) Allow LLM-generated probabilities with human review — still nondeterministic; review overhead defeats autonomy. (B) Use LLM for everything with a guardrail layer — guardrail layer would need to re-derive everything the LLM produced, making the LLM redundant |
| **Rationale** | The boundary between LLM and deterministic code is the single most important safety property in the system. It is enforced by static check, not by convention |
| **Consequences** | LLM call sites must be schema-constrained. Any value outside the expected closed set is rejected and the deterministic fallback is used. Copy Composer cannot populate monetary slots |
| **Follow-up** | If verifiable LLM pricing emerges in the future, this ADR must be explicitly superseded with a new ADR |
| **Reference** | [README § C-7](README.md), [08-agent-architecture.md § 1](08-agent-architecture.md), [22-security-and-privacy.md § 2](22-security-and-privacy.md) |

---

### ADR-005 · Hash-chained audit trail as system of record

| Field | Value |
|---|---|
| **Status** | ACCEPTED |
| **Date** | Specification phase |
| **Context** | The Track 03 bar requires an audit trail. REVIVE needs to prove that every action was authorised, that no guardrail was bypassed, and that results are traceable |
| **Decision** | The audit trail is append-only, hash-chained, and the system of record. Application tables are projections of it. Where the two disagree, the audit chain wins. If the audit store is unwritable, execution halts |
| **Alternatives** | (A) Separate logging layer — losable, not authoritative. (B) Application tables as the record — no tampering detection, no ordering proof |
| **Rationale** | A log you can lose is not an audit trail. A hash chain you depend on cannot be lost silently. `RR-AUDIT-010` makes this explicit |
| **Consequences** | Audit store availability is on the critical path. Every state can be reconstructed from the chain. Privacy canaries verify PII exclusion |
| **Follow-up** | None |
| **Reference** | [16-audit-trail.md](16-audit-trail.md) |

---

### ADR-006 · Bayesian cell model for recovery prediction

| Field | Value |
|---|---|
| **Status** | ACCEPTED |
| **Date** | Specification phase |
| **Context** | REVIVE needs `p(i,a)` and `p(i,∅)` estimates. No real historical data exists for training |
| **Decision** | Cell-based Bayesian model with priors from the generator's behavioural model, updated by observed outcomes via the Learning Engine (C-21). Cells defined by `(risk_class, cause, action, segment)` |
| **Alternatives** | (A) Full ML model — no real training data. (B) Fixed heuristic table — cannot learn from outcomes |
| **Rationale** | Bayesian updating is transparent, calibration-auditable, deterministic, and works with synthetic priors. Shrinkage to parent cells handles unseen combinations |
| **Consequences** | Cell granularity limits resolution. Prior quality depends on the generator (`UNVERIFIED`). `M-24` calibration is the key quality metric |
| **Follow-up** | With real data, consider gradient-boosted trees or calibrated neural networks (predictor interface unchanged) |
| **Reference** | [29-tradeoffs.md § 2](29-tradeoffs.md), [08-agent-architecture.md C-07](08-agent-architecture.md) |

---

### ADR-007 · Lagrangian relaxation with greedy fallback for allocation

| Field | Value |
|---|---|
| **Status** | ACCEPTED |
| **Date** | Specification phase |
| **Context** | The allocator must solve a constrained portfolio optimisation with ≥ 4 simultaneous resource constraints within a time budget |
| **Decision** | Primary allocator uses Lagrangian relaxation. If it exceeds the time budget, a greedy fallback is used. Fallback is recorded as `allocator_mode = FALLBACK_GREEDY` |
| **Alternatives** | (A) Greedy-only — ignores constraint interactions; no shadow prices. (B) Exact ILP — may be too slow for cycle time budget |
| **Rationale** | Lagrangian relaxation gives near-optimal solutions with shadow prices. The fallback ensures the system always produces a feasible solution. `M-34` makes fallback usage visible |
| **Consequences** | Shadow prices are approximate. Optimality gap reported only where exact ILP was also run (`M-31`) |
| **Follow-up** | None for hackathon |
| **Reference** | [10-recovery-allocation.md](10-recovery-allocation.md), [29-tradeoffs.md § 3](29-tradeoffs.md) |

---

### ADR-008 · Synthetic data only for evaluation

| Field | Value |
|---|---|
| **Status** | ACCEPTED |
| **Date** | Specification phase |
| **Context** | No access to real merchant or customer data. Hackathon ethics and data protection require synthetic data |
| **Decision** | All evaluation data is generated by a documented, seeded, deterministic generator. Generator fidelity is `UNVERIFIED`. No result is evidence about the real world |
| **Alternatives** | None feasible for a hackathon |
| **Rationale** | Synthetic data enables reproducibility, adversarial injection, and full coverage engineering. The generator is itself a threat surface and is documented as such |
| **Consequences** | Results are conditional on generator fidelity. The `ABUNDANT` profile is included precisely because it may be unflattering |
| **Follow-up** | Real data with anonymisation and consent for production validation (`FUTURE`) |
| **Reference** | [19-synthetic-dataset.md](19-synthetic-dataset.md), [29-tradeoffs.md § 4](29-tradeoffs.md) |

---

### ADR-009 · Gates are constraints, not penalty terms

| Field | Value |
|---|---|
| **Status** | ACCEPTED |
| **Date** | Specification phase |
| **Context** | Policy enforcement could be implemented as hard constraints (binary allow/deny) or as penalty terms in the optimisation objective |
| **Decision** | Gates are hard constraints. A gate verdict is final within its cycle. No component may override a `DENY`. If gates were penalty terms, a sufficiently large ENRV would purchase a violation |
| **Alternatives** | (A) Soft constraints (penalties) — a high-ENRV action could override a guardrail. Rejected because it makes guardrails negotiable |
| **Rationale** | The entire value proposition of guardrails depends on them being non-negotiable. A system that can be argued with will be argued with |
| **Consequences** | Capacity is sometimes left unused when a gate denies the chosen action. This capacity appears next cycle. No in-cycle re-optimisation after denial |
| **Follow-up** | None |
| **Reference** | [13-policy-and-guardrails.md § 5](13-policy-and-guardrails.md) |

---

### ADR-010 · Eleven stopping rules with fail-closed semantics

| Field | Value |
|---|---|
| **Status** | ACCEPTED |
| **Date** | Specification phase |
| **Context** | Track 03 explicitly requires stopping rules. The system must be provably bounded |
| **Decision** | Eleven stopping rules, evaluated twice per cycle (at start and before execution). Terminal rules are permanent. Re-openable rules require external evidence. Unknown state → treat as stopped |
| **Alternatives** | (A) Fewer rules — insufficient coverage. (B) Configurable-only rules — no guaranteed minimum protection |
| **Rationale** | Stopping rules are one of five independent bounding mechanisms. Removing any one makes the system unbounded in some dimension. Fail-closed prevents a stopped opportunity from leaking through |
| **Consequences** | Some recoverable revenue will be stopped. This is measured (`M-39` stopped value by reason) and reported honestly |
| **Follow-up** | Values for `N` (SR-07), recovery-window lengths, and approval validity periods must be decided during implementation |
| **Reference** | [14-stopping-rules.md](14-stopping-rules.md) |

---

## 3. Adding new ADRs

During implementation, new ADRs are required when:

1. A frozen convention ([README § C-1](README.md)…[C-8](README.md)) is changed
2. A MUST requirement is relaxed or reinterpreted
3. A new component is added (must pass the anti-proliferation test)
4. The scope boundary ([03](03-scope-boundaries.md)) is extended
5. The optimisation objective is modified
6. A new agent is introduced

New ADRs must:
- Use the next available `ADR-NNN` ID
- Cite the specification document being modified
- State the status explicitly
- Record the alternatives considered
- Be approved by the product owner for scope-affecting decisions
