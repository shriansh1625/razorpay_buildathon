# 39 · Glossary

Frozen vocabulary. A term defined here has exactly the meaning stated and no other. Where a term
is used in any document, its meaning is this document's meaning.

> **Convention.** Terms are alphabetical. Each entry states: term, definition, source, and any
> synonyms that are **not** used (to prevent drift).

---

| Term | Definition | Source | Not called |
|---|---|---|---|
| **Action** | A concrete recovery activity that REVIVE can execute: retry, send message, generate payment link, escalate, etc. Represented as an `ActionCandidate` before selection and an `Intervention` after execution | [05](05-functional-requirements.md), [17](17-data-model.md) | "Task", "job", "step" |
| **Action Adapter** | The interface that translates a REVIVE action into a provider-specific API call. In the hackathon, all adapters are simulators | [18](18-api-contracts.md), C-18 | "Connector", "plugin" |
| **Action Catalogue** | The closed set of action codes available per risk class and cause. Defined in the policy pack | [05 § 3](05-functional-requirements.md) | "Action library" |
| **Addressable** | An opportunity for which at least one recovery action is feasible. Non-addressable opportunities are counted in `M-01` but excluded from candidate generation | [05](05-functional-requirements.md) `RR-FUNC-007` | — |
| **ADR** | Architecture Decision Record. A documented decision with context, alternatives, rationale, and consequences. Stored in [31](31-decision-records.md) | [31](31-decision-records.md) | — |
| **Allocation** | The process of selecting one action per opportunity from a set of priced candidates, subject to resource constraints. Performed by C-12 | [10](10-recovery-allocation.md) | "Scheduling", "dispatching" |
| **Approval** | Human authorisation for a high-value or high-uncertainty action. Managed by C-15. Approved actions re-enter all gates | [13 § 3.1](13-policy-and-guardrails.md) G7 | "Review", "sign-off" |
| **Attribution** | Classification of a recovery outcome as `ATTRIBUTED` (REVIVE caused it), `NATURAL` (would have happened anyway), or `AMBIGUOUS` (uncertain). Performed by C-20 | [05](05-functional-requirements.md) `RR-FUNC-071` | "Credit assignment" |
| **Audit Event** | An immutable, hash-chained record of a material system action. The system of record | [16](16-audit-trail.md) | "Log entry" |
| **Baseline** | A reference policy against which REVIVE is compared. B0 (no action) through B6 (oracle-greedy) plus Oracle | [20](20-benchmark.md) § 2 | "Control group" |
| **Benchmark** | A reproducible batch evaluation run at a fixed seed. Produces a metrics artefact | [20](20-benchmark.md) | "Experiment", "test run" |
| **Candidate** | An `ActionCandidate`: a proposed action with its predicted recovery probability, cost, and ENRV, before the allocator selects | [17](17-data-model.md) | "Option", "alternative" |
| **Candidate Cause** | A ranked hypothesis about why a revenue event occurred. Produced by C-05 with a confidence band. Not a proven root cause | [12](12-revenue-leakage-model.md) | "Root cause" (avoided because it implies certainty) |
| **Cell** | A tuple `(risk_class, cause_code, action_code, customer_segment)` used for prediction and learning. The unit of the Bayesian model | [35](35-learning-engine.md) | "Bucket", "bin" |
| **Confidence Band** | A categorical measure of diagnosis certainty: LOW, MED, HIGH. Mapped to numeric prior weights by a versioned deterministic table | [08](08-agent-architecture.md) C-05 | "Confidence score" |
| **Context Object** | A structured bundle of customer, instrument, contact history, fatigue, and timing information assembled by C-04 for use in diagnosis and pricing | [08](08-agent-architecture.md) C-04 | "Feature vector" |
| **Cooldown** | A minimum interval between actions of the same family on the same opportunity. Enforced by G4 | [13](13-policy-and-guardrails.md) G4 | "Backoff", "delay" |
| **Cycle** | A periodic decisioning interval. Signals accumulate continuously; decisioning is batched per cycle. Default: 15 minutes of virtual time | [07 § 1.2](07-system-architecture.md) | "Tick", "epoch", "round" |
| **Decision** | The allocator's output for one opportunity in one cycle: `SELECTED`, `DEFERRED`, `REJECTED`, or `NO_ACTION` | [17](17-data-model.md) | "Plan", "recommendation" |
| **Deferral** | A deliberate decision to postpone action on an opportunity to a future cycle. The opportunity remains in the pool | [05](05-functional-requirements.md) `RR-FUNC-041` | "Delay", "skip" |
| **Degradation** | A cohort-level elevation in failure rate detected by C-03. Flags affected opportunities | [05](05-functional-requirements.md) `RR-FUNC-006` | "Outage" |
| **Deterministic** | A computation that, given the same inputs and seed, always produces the same output. All financial computations in REVIVE are deterministic | [README § C-7](README.md) | — |
| **ENRV** | Expected Net Recovered Value. The objective function. `u(i,a)·V(i)·m − c(a) − p(i,a)·d(i,a) − λ_f·F(i,a)` | [README § C-5](README.md) | "Score", "priority" |
| **Exploration** | Deliberately selecting an action in a sparse or unseen cell to collect data, within a capped budget | [35 § 5](35-learning-engine.md) | "Experiment" |
| **Fail closed** | The default posture: when uncertain or in error, do less, not more. Missing data → no action. Unknown state → treat as stopped. Gate error → deny | [04](04-principles-and-non-goals.md), [13](13-policy-and-guardrails.md), [14](14-stopping-rules.md) | — |
| **Fatigue** | The modelled future-value destruction caused by contacting a customer. A cost term in ENRV | [README § C-5](README.md) | "Annoyance" |
| **Gate** | A policy check that evaluates a proposed action and returns `ALLOW`, `DENY`, `DEFER`, `REQUIRE_APPROVAL`, or `ALLOW_WITH_MODIFICATION`. 12 gates, evaluated in fixed order G1…G12 | [13](13-policy-and-guardrails.md) | "Rule", "filter", "validator" |
| **Generator** | The synthetic data generator. Produces the dataset from a seed | [19](19-synthetic-dataset.md) | "Simulator" |
| **HALT** | A global stop command issued by a human operator. Stops all recovery activity | [13](13-policy-and-guardrails.md), [14](14-stopping-rules.md) SR-11 | "Kill switch", "emergency stop" |
| **Horizon (H)** | The time window within which a recovery must occur to count. Oracle outcomes are evaluated at `H` | [11](11-counterfactual-engine.md) | "Window" |
| **Idempotency Key** | A unique key per execution attempt. Ensures that retrying a failed call does not produce a duplicate effect | [15](15-execution-model.md) `RR-FUNC-060` | — |
| **Intervention** | An executed action instance. Created when an `ActionCandidate` is selected, gated, and dispatched to an adapter | [17](17-data-model.md) | "Execution", "attempt" |
| **Invariant Violation** | An event indicating the system's internal consistency has been compromised. `M-22 > 0` invalidates the run | [34 § 5.2](34-state-machine.md) | "Bug", "error" |
| **NO_ACTION** | A deliberate decision not to act on an opportunity. `ENRV(i,∅) = 0` by definition. Always included as a candidate | [05](05-functional-requirements.md) `RR-FUNC-040` | "Skip", "ignore" |
| **Opportunity** | A `RevenueOpportunity`: a detected instance of revenue at risk, with a value, risk class, and lifecycle state | [17](17-data-model.md) | "Case", "ticket", "lead" |
| **Oracle** | The hidden-outcome function in the synthetic dataset. Knows what would have happened under any action, including no action | [19 § 4](19-synthetic-dataset.md) | "Ground truth" |
| **Outcome** | The observed result of an intervention: `recovered_amount_paise`, `attribution_class`, and reconciliation data | [17](17-data-model.md) | "Result" |
| **Paise** | 1/100 of a rupee. All monetary values in REVIVE are integer paise | [README § C-2](README.md) | "Cents" |
| **Policy Pack** | A versioned, sealed bundle of all merchant-configurable policy parameters: contact caps, budget limits, gate thresholds, action catalogue, cooldowns | [13](13-policy-and-guardrails.md) | "Configuration", "settings" |
| **Profile** | A named parameter set for the synthetic generator: `BALANCED`, `HIGH_NATURAL`, `SCARCE`, `ABUNDANT` | [19 § 2.3](19-synthetic-dataset.md) | "Scenario" |
| **Reconciliation** | The process of determining the actual outcome of an action whose immediate result was unknown (e.g., `TIMEOUT_UNKNOWN`) | [15](15-execution-model.md) `RR-FUNC-065` | — |
| **Recovery** | A payment that was at risk and has now been settled. May be full or partial | [05](05-functional-requirements.md) | "Collection" |
| **Reservation** | A hold on a resource (budget, SMS credit, call minute) prior to action execution. Two-phase: `HELD → COMMITTED` or `HELD → RELEASED` | [34 § 4](34-state-machine.md) | "Lock" |
| **Revenue Leakage** | The economic pattern by which expected revenue fails to materialise | [12](12-revenue-leakage-model.md) | "Revenue loss" |
| **Risk Class** | The category of revenue event: `PAYMENT_FAILURE`, `CHECKOUT_ABANDONMENT`, `SUBSCRIPTION_FAILURE`, `RECEIVABLE_OVERDUE` | [05](05-functional-requirements.md) `RR-FUNC-001` | "Event type" |
| **Seed** | A deterministic initialisation value for the PRNG. Two runs at the same seed produce identical results | [19 § 2.1](19-synthetic-dataset.md) | — |
| **Shadow Price** | The marginal ENRV per unit of a binding resource. Tells the merchant what one more unit of capacity is worth | [10](10-recovery-allocation.md) | "Dual variable", "Lagrange multiplier" |
| **Signal** | An incoming event from the payment ecosystem: payment failed, checkout abandoned, subscription charged back, invoice overdue | [17](17-data-model.md) | "Event", "notification" |
| **Stopping Rule** | A condition that, when true, terminates all further activity on an opportunity. 11 rules, `SR-01`…`SR-11` | [14](14-stopping-rules.md) | "Exit condition" |
| **Strategy Version** | A snapshot of all predictor parameters (cell posteriors) at a point in time. Produced by the Learning Engine | [35](35-learning-engine.md) | "Model version" |
| **Uplift** | `u(i,a) = p(i,a) − p(i,∅)`. The incremental effect of taking action `a` on opportunity `i`. Can be negative | [README § C-5](README.md) | "Lift", "delta" |
| **Value at Risk** | `V(i)`: the recoverable monetary amount on an opportunity, in integer paise | [05](05-functional-requirements.md) `RR-FUNC-002` | "Exposure" |
