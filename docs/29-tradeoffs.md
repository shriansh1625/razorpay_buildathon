# 29 · Trade-offs

Every architecture choice has a cost. This document records the major decisions, the alternatives
considered, and why the chosen approach is appropriate for this hackathon — without claiming it
is universally best.

---

## 1. LLM vs deterministic logic

### Context

REVIVE must diagnose failure causes, generate message copy, price actions, enforce policies, and
allocate resources. LLMs are capable general-purpose reasoners. Deterministic logic is verifiable
and reproducible.

### Alternatives

| Alternative | Description |
|---|---|
| **A. LLM-first** | Use an LLM for diagnosis, pricing, policy evaluation, allocation, and copy generation |
| **B. Deterministic-first** | Use deterministic logic for everything; no LLM |
| **C. Hybrid (chosen)** | LLMs for residual diagnosis and copy generation only; everything else deterministic |

### Chosen approach

**C. Hybrid.** Two LLM agents (C-05 Root Cause Analyst, C-10 Copy Composer) handle tasks where
reasoning adds genuine value. Eighteen deterministic modules handle everything involving money,
probabilities, policy, and execution.

### Rationale

- `RR-GUARD-020` forbids LLM output from becoming a number that moves money
- Pricing, allocation, and policy evaluation must be reproducible (`RR-NFR-020`)
- An LLM that controls monetary values is a financial safety risk ([22 § 3](22-security-and-privacy.md))
- The LLM earns its place on the diagnostic residual — unmapped failure codes, conflicting signals
- Copy generation is a genuine language task where LLMs add value without financial risk

### Downside

- Deterministic diagnosis handles only known failure codes; novel codes fall back to `UNCLASSIFIED`
- Copy generation fallback (static templates) is less engaging
- More code to write than an LLM-orchestrated approach

### Future alternative

If calibrated LLM-based pricing becomes verifiable and reproducible, it could supplement the
statistical predictor. This would require `RR-GUARD-020` to be relaxed via ADR.

---

## 2. ML vs heuristics for recovery prediction

### Context

REVIVE needs `p(i,a)` and `p(i,∅)` — the probability of recovery with and without action.

### Alternatives

| Alternative | Description |
|---|---|
| **A. Full ML model** | Train a model on historical outcomes |
| **B. Heuristic lookup** | Fixed probability table by risk class × cause × action |
| **C. Bayesian cell model (chosen)** | Cell-based estimates with priors from the generator, updated by outcomes |

### Chosen approach

**C. Bayesian cell model.** Cells defined by `(risk_class, cause, action, segment)`. Initial priors from
the generator's behavioural model. Posteriors updated by observed outcomes via the Learning Engine
(C-21).

### Rationale

- No real historical data exists → full ML training is impossible (`HACKATHON-SCOPE`)
- Heuristics are fixed and cannot learn from outcomes
- Cell-based Bayesian updating is transparent, calibration-auditable (`M-24`), and deterministic
- Shrinkage to parent cells handles unseen combinations
- Generator priors are disclosed as `PROPOSED`, not presented as trained models

### Downside

- Cell granularity limits resolution — interactions between features within a cell are lost
- Prior quality depends on the generator, which is `UNVERIFIED`
- May underperform a well-trained ML model with real data

### Future alternative

With real historical data, a gradient-boosted tree or calibrated neural network could replace the
cell model. The predictor interface (C-07) would be unchanged.

---

## 3. Optimisation vs ranking for allocation

### Context

REVIVE must select actions across a portfolio under multiple resource constraints.

### Alternatives

| Alternative | Description |
|---|---|
| **A. Rank by ENRV, greedy fill** | Sort all candidates by ENRV; accept top-N until budget exhausted |
| **B. Integer linear program (ILP)** | Exact optimisation with constraint enforcement |
| **C. Lagrangian relaxation with greedy fallback (chosen)** | Dual-based approximate optimisation; falls back to greedy if timeout |

### Chosen approach

**C. Lagrangian relaxation with greedy fallback.** Primary allocator uses Lagrangian relaxation to
handle multiple simultaneous constraints. Greedy fallback activated if the primary exceeds its time
budget (`RR-FUNC-039`). Fallback is recorded as `allocator_mode = FALLBACK_GREEDY` (`M-34`).

### Rationale

- Greedy-only ignores constraint interactions (e.g., SMS-heavy vs budget-heavy)
- ILP is exact but may be too slow for the cycle time budget
- Lagrangian relaxation gives near-optimal solutions with shadow prices (`M-30`)
- The fallback ensures the system always produces a feasible solution
- Track bar asks for allocation, not just ranking

### Downside

- More complex than greedy
- Shadow prices from Lagrangian relaxation are approximate, not exact duals
- Optimality gap (`M-31`) is reported only where exact ILP was also run

### Future alternative

With larger batches, column generation or branch-and-price could improve optimality. For the
hackathon, the Lagrangian approach is sufficient.

---

## 4. Synthetic vs real data

### Context

All evaluation runs on synthetic data.

### Alternatives

| Alternative | Description |
|---|---|
| **A. Real data** | Use Razorpay production data |
| **B. Synthetic only (chosen)** | Generate all data from a documented behavioural model |

### Chosen approach

**B. Synthetic only.** All data generated from a seeded PRNG with a documented behavioural model
([19](19-synthetic-dataset.md)).

### Rationale

- No access to Razorpay production data
- No real customer data can be used in a hackathon
- Synthetic data enables reproducibility (`RR-NFR-020`)
- Generator design allows adversarial and edge-case injection
- Honesty: generator fidelity is `UNVERIFIED` and labelled as such

### Downside

- Results do not prove anything about real-world performance
- Generator parameters are `PROPOSED`, not calibrated against reality
- A well-tuned generator could (unconsciously) favour REVIVE — guarded by the `ABUNDANT` profile
  and by disclosing the generator as a threat surface ([19 § 0](19-synthetic-dataset.md))

### Future alternative

Real data, with proper anonymisation and consent, would make results meaningful. This is `FUTURE`.

---

## 5. Autonomy vs approval

### Context

REVIVE can act autonomously or route actions to humans.

### Alternatives

| Alternative | Description |
|---|---|
| **A. Fully autonomous** | Every action executes without human oversight |
| **B. Fully supervised** | Every action requires human approval |
| **C. Threshold-based approval (chosen)** | Low-risk actions execute autonomously; high-risk/uncertain actions require approval |

### Chosen approach

**C. Threshold-based approval.** G7 routes actions to the approval queue based on value, uncertainty,
action class, and cumulative incentive thresholds. Everything else executes autonomously.

### Rationale

- Full autonomy is irresponsible for financial actions
- Full supervision defeats the purpose of an autonomous agent
- Threshold-based routing lets the merchant control the autonomy boundary
- `M-37` and `M-38` make the approval load and expiry rate visible
- Expired approvals never become executions (silence is not consent, `SR-06`)

### Downside

- Threshold tuning is a policy decision with no right answer in the abstract
- A busy approver creates an expiry bottleneck (`M-38`)
- In the benchmark, approval is simulated, not real

### Future alternative

With trust built over time, approval thresholds could be raised. This is a merchant-level
configuration change, not a code change.

---

## 6. Breadth vs depth

### Context

REVIVE covers four risk classes. An alternative is to do one class excellently.

### Alternatives

| Alternative | Description |
|---|---|
| **A. Single class (e.g., payment failures only)** | Deep implementation of one domain |
| **B. Four classes (chosen)** | Breadth across all four Track 03 domains |

### Chosen approach

**B. Four classes.** Payment failures, checkout abandonment, subscription/mandate failures, and
overdue receivables.

### Rationale

- Track 03 brief explicitly names all four
- The allocation differentiator is strongest when the portfolio is heterogeneous
- A single-class product cannot demonstrate cross-class resource contention
- JC-02 through JC-05 in [27](27-judging-criteria-mapping.md) require all four

### Downside

- Each class gets less implementation depth than a single-class approach
- Candidate sets for less-developed classes may be shallow
- Testing surface is larger

### Future alternative

Deeper per-class intelligence (e.g., issuer-specific retry strategies) is `FUTURE`.

---

## 7. Realism vs hackathon feasibility

### Context

Some design choices prioritise demonstrability over production readiness.

### Alternatives

| Alternative | Description |
|---|---|
| **A. Production-grade** | Real adapters, real data, real compliance |
| **B. Hackathon-scoped (chosen)** | Simulated adapters, synthetic data, documented assumptions |

### Chosen approach

**B. Hackathon-scoped.** Simulated adapters, synthetic data, simplified consent model, single
currency, single timezone.

### Rationale

- No access to production systems
- No time for real compliance verification
- Simulated adapters allow reproducible benchmarking
- Simplifications are documented (`HACKATHON-SCOPE` label) and not hidden
- The architecture supports real adapters without redesign (adapter interface is the same)

### Downside

- Results are not evidence about real-world performance
- Consent semantics are synthetic, not legally verified
- Single currency and timezone are not production-representative

### Future alternative

Real adapters, verified compliance, multi-currency, multi-timezone are all `FUTURE`.

---

## 8. Graph model vs relational-only representation

### Context

Revenue leakage involves relationships between risk classes, failure causes, instruments,
customers, and actions. These can be modelled as a graph or as relational tables.

### Alternatives

| Alternative | Description |
|---|---|
| **A. Graph database** | Store the leakage model as a property graph |
| **B. Relational with graph-like queries (chosen)** | Relational tables with join-based traversal and UI-rendered graph |

### Chosen approach

**B. Relational with graph-like queries.** The data model ([17](17-data-model.md)) is relational. The
Revenue Leakage Explorer (Screen 2) renders a graph visualisation from join queries.

### Rationale

- A graph database adds a dependency and operational complexity for the hackathon
- The relationship structure is well-defined and static (risk class → cause → action)
- Relational joins are sufficient for the query patterns needed
- The UI graph is a rendering concern, not a storage concern

### Downside

- Deep graph traversals (multi-hop reachability) are verbose in SQL
- If the leakage model becomes dynamic (learning new relationships), a graph may be more natural

### Future alternative

A graph layer (e.g., for dynamic causal-relationship discovery) is `FUTURE`.

---

## 9. Self-learning vs fixed strategy

### Context

REVIVE can update its predictor parameters from observed outcomes, or use fixed parameters.

### Alternatives

| Alternative | Description |
|---|---|
| **A. Fixed strategy** | Predictor parameters set at initialisation, never updated |
| **B. Full reinforcement learning** | End-to-end policy learning from rewards |
| **C. Bayesian updating (chosen)** | Cell posteriors updated from outcomes; strategy versioned |

### Chosen approach

**C. Bayesian updating.** The Learning Engine (C-21) updates cell posteriors from observed outcomes,
producing a new `StrategyVersion`. The prior version is retained. Calibration is monitored.

### Rationale

- Fixed strategy cannot adapt to distribution shifts within a run
- Full RL is unpredictable, hard to audit, and violates `RR-GUARD-022` boundaries
- Bayesian updating is transparent, versioned, rollbackable, and calibration-auditable
- `RR-GUARD-022` structurally prevents learning from changing policy limits
- Ablation (learning-on vs learning-off) makes the contribution measurable

### Downside

- Bayesian updating is limited to cell-level updates; no cross-cell generalisation
- In a short hackathon run, learning may not have enough data to improve materially
- Exploration budget cost (`M-29` exploration share)

### Future alternative

With sufficient data, a more sophisticated online learning approach (e.g., Thompson sampling with
contextual bandits) could improve exploration efficiency. This is `FUTURE`.

---

## 10. Voice: optional vs voice-first

### Context

Track 03 mentions "Hinglish voice recovery" as an example direction.

### Alternatives

| Alternative | Description |
|---|---|
| **A. Voice-first** | Voice as the primary recovery channel |
| **B. Voice optional (chosen)** | Voice as a MAY-tier action, implemented only after P0 stable |

### Chosen approach

**B. Voice optional.** `VOICE_CALL` is a MAY-tier action (`RR-FUNC-022`). The adapter interface
supports it. Implementation is only attempted after all P0 requirements are stable.

### Rationale

- Voice adds significant complexity (call orchestration, speech synthesis, Hinglish templates)
- Track 03 lists it as an "example direction", not a requirement
- The allocation framework treats voice as one more resource-constrained action — no special
  architecture is needed
- P0 requirements have higher submission risk if voice delays them

### Downside

- Missing a named example direction may reduce points
- Voice could be a differentiator if executed well

### Future alternative

Voice-first with real telephony integration is `FUTURE`.

---

## 11. Summary

| # | Decision | Chosen | Alternative that would change if… |
|---|---|---|---|
| 1 | LLM role | Diagnosis + copy only | Verifiable LLM pricing becomes possible |
| 2 | Prediction model | Bayesian cells | Real historical data is available |
| 3 | Allocation | Lagrangian + greedy fallback | Batch sizes grow beyond current scale |
| 4 | Data | Synthetic only | Production data access is granted |
| 5 | Autonomy | Threshold-based approval | Trust is built with a merchant over time |
| 6 | Breadth | Four risk classes | Track required only one |
| 7 | Feasibility | Hackathon-scoped | Production deployment is the goal |
| 8 | Leakage representation | Relational with UI graph | Dynamic causal discovery is needed |
| 9 | Learning | Bayesian updating | Sufficient data for contextual bandits |
| 10 | Voice | Optional (MAY) | Voice is a judging requirement |
