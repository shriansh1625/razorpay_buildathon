# 37 · Metrics Dictionary

One definition per metric, in one place. If a number appears in any artefact, UI surface, or document,
it is defined here or it is a defect.

**No values appear in this document** (`README § C-8`). Values exist only in generated artefacts.

Conventions: money in integer paise (`*_paise`); `↑` higher is better, `↓` lower is better, `=0` the
only acceptable value is zero, `—` diagnostic/neutral. Tiers per [21 § 1](21-evaluation.md).

> **IDs are historical.** They were assigned in the order metrics were introduced across this package,
> so they are not grouped by tier or theme. **Tier membership is stated explicitly per metric and in
> § 8; it must never be inferred from the ID.**

The tier sets, stated once:

| Tier | Members |
|---|---|
| **0 · Guardrail (must be 0)** | `M-16`, `M-17`, `M-18`, `M-22` |
| **1 · Primary** | `M-10` |
| **2 · Secondary constraint** | `M-11`, `M-12`, `M-13`, `M-23` |
| **0-adjacent (must pass)** | `M-46`, `M-47`, `M-57`, `M-58` |
| **3 · Diagnostic** | Everything else |

---

## 1. Metric record structure

Every entry carries **definition**, **unit**, **direction**, **tier**, and — where the metric could be
gamed — **gaming risk and defence**.

`RR-METRIC-002`: every metric emits a `MetricSnapshot` row with a `derivation_ref` (`DM-34`). A metric
with no derivation reference cannot be reported.

---

## 2. Group A — Money and recovery

| ID | Name | Definition | Unit | Dir | Tier |
|---|---|---|---|---|---|
| `M-01` | Detected value at risk | `Σ value_at_risk_paise` over all opportunities created, addressable or not | paise | — | 3 |
| `M-02` | Addressable value at risk | Same, restricted to `addressable = true` | paise | — | 3 |
| `M-03` | Considered value | `Σ value_at_risk_paise` over opportunities that entered decisioning | paise | — | 3 |
| `M-04` | Actioned value | `Σ value_at_risk_paise` over opportunities with ≥ 1 executed action | paise | — | 3 |
| `M-05` | Gross recovered revenue | `Σ recovered_amount_paise` over all outcomes, any attribution | paise | — | 3 |
| `M-06` | Attributed recovered revenue | `Σ recovered_amount_paise` where `attribution_class = ATTRIBUTED` | paise | ↑ | 3 |
| `M-07` | Natural recovered revenue | `Σ recovered_amount_paise` where `attribution_class = NATURAL` | paise | — | 3 |
| `M-08` | Realised recovery cost and variance | `Σ actual_cost_paise + Σ actual_incentive_paise`, plus the variance against the estimated `cost_paise` and `expected_incentive_paise` used at pricing time | paise | ↓ | 3 |
| `M-09` | Ambiguous recovered revenue | `Σ recovered_amount_paise` where `attribution_class = AMBIGUOUS` | paise | ↓ | 3 |
| `M-10` | **Incremental Net Recovered Revenue** | `NetRecovered(policy, seed) − NetRecovered(B0, seed)`, paired ([21 § 2.1](21-evaluation.md)) | paise | ↑ | **1** |
| `M-11` | Net recovery per unit cost | `M-10 / M-08`; undefined and reported as such when `M-08 = 0` | ratio | ↑ | **2** |
| `M-12` | False-positive contact value | `Σ value_at_risk_paise` over opportunities actioned **and** whose oracle row says they would have recovered naturally within `H` | paise | ↓ | **2** |
| `M-13` | Contacts per unit net recovered | `contact_count / (M-10 in rupees)`, contacts counted from `ContactLedger` | contacts per ₹ | ↓ | **2** |

### 2.1 Notes and defences

| Metric | Gaming risk | Defence |
|---|---|---|
| `M-01` | Inflating detection by counting one economic loss many times makes the funnel look large | `LK-1`…`LK-5`; `M-01 ≤` outstanding money in the dataset, asserted (`GI-2`) |
| `M-05` | **The most dangerous metric in the system.** It reads naturally as "money we recovered" while including everything that would have recovered anyway | Never reported alone. The generator emits `M-05`, `M-06`, `M-07`, `M-09` in one block and asserts `M-05 = M-06 + M-07 + M-09` (`AT-3`) |
| `M-06` | Attribution bias toward the system doing the attributing | Ambiguity resolves against REVIVE (`AT-1`); `M-06` is tier 3 and never the judged number |
| `M-08` | Under-counting by excluding failed actions' cost, or by using estimates instead of actuals | Cost is charged on every executed action, success or not (`15 § 5`); actuals reconciled against estimates (`RR-FUNC-072`) |
| `M-10` | Pooling seeds to hide variance | Reported per seed, paired, with median/min/max and loss count (`20 § 3.3`) |
| `M-11` | Dividing by a near-zero cost | Undefined case reported explicitly, never as a large ratio (`RR-METRIC-008`) |
| `M-12` | Quietly excluding it from the report | Required alongside `M-19` in the same block (`RR-METRIC-011`) |
| `M-13` | Counting only contacts that "worked" | Counted from `ContactLedger`, not `Intervention` rows, so a contact counts even where its intervention record is inconsistent (`DM-24`). Non-contact actions are excluded from the numerator and reported separately |

`M-10` is the only metric the system optimises. It can be negative, and a negative value is reported as
the headline rather than suppressed.

---

## 3. Group B — Guardrails

| ID | Name | Definition | Unit | Dir | Tier |
|---|---|---|---|---|---|
| `M-14` | Guardrail-block profile | Gate outcomes by `gate_id` × `verdict` × `reason_code`, including modifications and passes | count | — | 3 |
| `M-15` | Deliberate no-action profile | Count and `Σ value_at_risk_paise` of decisions with outcome `NO_ACTION`, by reason code | count, paise | — | 3 |
| `M-16` | **Actions executed without `ALLOW`** | Interventions with no complete `ALLOW` gate trace | count | **=0** | **0** |
| `M-17` | **Missed stops** | Opportunities that satisfied a stopping condition at evaluation time and nonetheless had an action executed | count | **=0** | **0** |
| `M-18` | **Unapproved executions** | Executions of an action whose gate verdict was `REQUIRE_APPROVAL` without a valid, unexpired, matching approval | count | **=0** | **0** |
| `M-22` | **Invariant violations** | `INVARIANT_VIOLATION` audit events | count | **=0** | **0** |

### 3.1 Notes

| Metric | Note |
|---|---|
| `M-14` | Neither good nor bad. A gate that never denies anything is either unnecessary or untested, and this profile is what reveals which (`13 § 6`) |
| `M-15` | The measurement that makes "do nothing" a visible decision rather than an absence. Reported with its value, so the reader sees how much money REVIVE deliberately left alone this cycle |
| `M-16` | Derived by **traversal of the audit chain** (`V-7`), not by reading an application flag |
| `M-17` | Derived by **independently re-evaluating all eleven stopping rules** against the recorded pre-execution state, in a separate evaluator from the runtime one |
| `M-18` | Derived from approval records and the chain, matching approval id, expiry, and parameters — a modified approval that was not re-gated counts here (`RR-FUNC-066`) |
| `M-22` | Any non-zero value invalidates the run (`34 § 5.2`) |

`M-16`, `M-17`, and `M-18` being computed by paths independent of the components they audit is the most
important design choice in this dictionary. A guardrail metric computed by the component under audit
measures nothing.

---

## 4. Group C — Decision quality

| ID | Name | Definition | Unit | Dir | Tier |
|---|---|---|---|---|---|
| `M-19` | Missed opportunity value | `Σ value_at_risk_paise` over opportunities that closed unrecovered where the oracle says an available action would have recovered them within `H` and within capacity. Also reports the deferral-caused subset | paise | ↓ | 3 |
| `M-20` | Harmful-action avoidance | Count and `Σ` of negative-uplift candidates that were priced, reached the allocator, and were rejected **on price** rather than filtered earlier | count, paise | ↑ | 3 |
| `M-21` | Outcome observation and reconciliation | Recovered-amount reconciliation against domain records; `partial_recovery_rate`; `unobservable_rate`; `late_recovery_rate` | ratios | — | 3 |
| `M-23` | Wasted spend | `Σ (actual_cost + actual_incentive)` over executed actions whose opportunity recovered nothing within `H` | paise | ↓ | **2** |
| `M-24` | Calibration | Brier score **and** expected calibration error **and** reliability table with bin counts, reported separately for `p(i,a)` and `p(i,∅)`, per action family and per cell level | score, ratio | ↓ | 3 |
| `M-25` | Uplift ranking quality | Decile lift of predicted uplift against oracle uplift | ratio | ↑ | 3 |
| `M-26` | `NO_ACTION` correctness | Of decisions with outcome `NO_ACTION`, the fraction where the oracle confirms no available action had positive uplift net of cost | ratio | ↑ | 3 |
| `M-27` | Diagnosis agreement | Fraction of diagnoses whose top cause matches the generated cause, computed **only** over opportunities where the cause is observable | ratio | ↑ | 3 |
| `M-28` | Wrong-action value loss | `Σ (oracle_best_action_ENRV − chosen_action_ENRV)` over selected decisions, oracle-evaluated | paise | ↓ | 3 |

### 4.1 Notes

| Metric | Note |
|---|---|
| `M-19` | The counterweight to `M-12`. `M-12` punishes acting too much; `M-19` punishes acting too little. `RR-METRIC-011` requires both in the same block, because reporting either alone biases the picture |
| `M-20` | Deliberately a *positive*-direction metric. Declining a harmful action is a product behaviour worth counting, and it is only countable because negative-uplift candidates are priced rather than pre-filtered (`CF-10`) |
| `M-21` | Covers what `M-05`…`M-09` cannot: whether outcomes were observable at all. `unobservable_rate` is reported, never silently excluded |
| `M-24` | Prioritised over `M-25` because `ENRV` is linear in `p` (`11 § 4.5`). `CE-1` requires calibration for `p(i,∅)` separately — a well-calibrated action model with a badly-calibrated baseline model produces confidently wrong uplifts |
| `M-26` | Makes `NO_ACTION` falsifiable rather than rhetorical (`RR-BENCH-006`) |
| `M-27` | Restricted to observable causes, because most cause codes are not observable in real data (`12 § 8.2`); scoring against unobservable ground truth would measure the generator, not the diagnoser. `UNCLASSIFIED` is not penalised |
| `M-28` | Oracle-dependent and therefore carries `D-E3` wherever it appears |

---

## 5. Group D — Allocation

| ID | Name | Definition | Unit | Dir | Tier |
|---|---|---|---|---|---|
| `M-29` | Capacity utilisation | Per resource: `committed / limit`, per cycle and per period | ratio | — | 3 |
| `M-30` | Shadow price | Per binding resource: marginal `ENRV` per unit, always with `shadow_price_method` | paise per unit | — | 3 |
| `M-31` | Optimality gap | `(ENRV_EXACT − ENRV_LAGRANGIAN) / ENRV_EXACT`, **only where `EXACT` was actually run** | ratio | ↓ | 3 |
| `M-32` | Displacement | Count and `Σ ENRV` of positive-`ENRV` candidates not selected because a constraint bound | count, paise | — | 3 |
| `M-33` | Allocator runtime | Wall-clock for the allocation stage, per cycle | ms | ↓ | 3 |
| `M-34` | Allocator fallback rate | Fraction of cycles using `FALLBACK_GREEDY`, with reasons | ratio | ↓ | 3 |

### 5.1 Notes

| Metric | Note |
|---|---|
| `M-29` | If binding resources are not near-saturated, the profile is not testing allocation, and the report must say so (`21 § 6`) |
| `M-30` | The merchant-facing output of contention. `shadow_price_method` travels with it so a `GREEDY_ESTIMATE` is never read as a dual optimum (`AC-20`) |
| `M-31` | **Absent where `EXACT` was not run. Never estimated.** An invented gap would be a fabricated number (`README § C-8`) |
| `M-32` | "These were worth doing and we could not afford them" — the honest statement of what scarcity cost |
| `M-34` | A high fallback rate means the default allocator is not what is being measured, which must be visible |

---

## 6. Group E — Operational honesty

| ID | Name | Definition | Unit | Dir | Tier |
|---|---|---|---|---|---|
| `M-35` | Unresolved reconciliations | Interventions ending `UNRESOLVED` | count | ↓ | 3 |
| `M-36` | Reconciliation load | Reconcile attempts; mean cycles spent in `RECONCILING` | count | ↓ | 3 |
| `M-37` | Approval load | Requests raised, resolved, rejected, modified; approver decisions per cycle | count | ↓ | 3 |
| `M-38` | Approval expiry rate | `expired / raised` | ratio | ↓ | 3 |
| `M-39` | Stopped value by reason | `Σ value_at_risk_paise` at stop, grouped by `SR-*` | paise | — | 3 |
| `M-40` | Re-open count | Re-openings by rule, with triggering evidence refs | count | ↓ | 3 |
| `M-41` | Deferral profile | Deferrals by reason, plus the age distribution of repeatedly-deferred opportunities | count | — | 3 |
| `M-42` | Closed-unrecovered value | `Σ value_at_risk_paise` in `CLOSED_UNRECOVERED` | paise | — | 3 |
| `M-43` | Adapter result profile | Interventions by `AdapterResult` | count | — | 3 |
| `M-44` | Halt events | Halts engaged and released, with actor role and reservations released | count | — | 3 |
| `M-45` | Incentive intensity | `Σ actual_incentive_paise / M-05` | ratio | ↓ | 3 |

### 6.1 Notes

| Metric | Note |
|---|---|
| `M-35` | The count of cases where REVIVE **does not know what it did**. Reported prominently; a zero without an injected-timeout test is not credible (`15 § 6`) |
| `M-37` | An autonomous system that routes most decisions to a person has automated little. This metric makes that visible instead of letting it hide inside a good `M-10` |
| `M-38` | A high expiry rate means the approval design is impractical — a design failure that would otherwise surface only as unexplained under-recovery |
| `M-39` | The honest accounting of what REVIVE walked away from, deliberately (`14 § 6`) |
| `M-41` | Chronic deferral is how an opportunity is neither pursued nor stopped. The age distribution is what exposes it |
| `M-45` | Reported because recovery bought entirely with discounts is a different product than recovery bought with better targeting |

---

## 7. Group F — Reproducibility, cost, coverage

| ID | Name | Definition | Unit | Dir | Tier |
|---|---|---|---|---|---|
| `M-46` | Reproducibility check | Byte identity of artefacts across two runs at a fixed seed | pass/fail | pass | 0-adjacent |
| `M-47` | Uncached LLM calls in EVALUATE | Count of live model calls during a measured run | count | **=0** | 0-adjacent |
| `M-48` | LLM cache hit rate | Hits / lookups, per purpose | ratio | ↑ | 3 |
| `M-49` | LLM token usage and cost | Input and output tokens, and monetary cost, per mode and purpose | tokens, currency | ↓ | 3 |
| `M-50` | LLM output rejection rate | Schema-validation failures / calls, with fallbacks applied | ratio | ↓ | 3 |
| `M-51` | Unclassified diagnosis rate | Diagnoses with `unclassified = true` / total | ratio | — | 3 |
| `M-52` | Cycle wall clock | Per cycle, and per stage | ms | ↓ | 3 |
| `M-53` | Run wall clock | Per seed, and for the full matrix | s | ↓ | 3 |
| `M-54` | Audit event volume | Events per cycle and per considered opportunity | count | — | 3 |
| `M-55` | Coverage | Gates fired, stopping rules fired, states reached, action codes used, adapter results observed — each with a **named gap list** | counts | ↑ | 3 |
| `M-56` | Signal hygiene | Duplicates suppressed, quarantined, late, out-of-order | count | — | 3 |
| `M-57` | Privacy canary scan | Sentinel hits across all sinks | count | **=0** | 0-adjacent |
| `M-58` | Audit verification | Result of `V-1`…`V-12` | pass/fail per check | pass | 0-adjacent |

### 7.1 Notes

| Metric | Note |
|---|---|
| `M-46` | A failure invalidates every comparison in the report: nothing can be attributed to a policy change if runs are not reproducible |
| `M-47` | Non-zero means a measured run made a live model call, breaking determinism. Hard error (`RR-NFR-035`) |
| `M-49` | Reported because "we used an LLM" has a price, and the `LLM_OFF` ablation is only interpretable next to it (`20 § 5.1`) |
| `M-51` | Neither good nor bad alone. A suspiciously low rate on a dataset with deliberately incomplete cause signals (`DS-9`) suggests the diagnoser is guessing rather than abstaining |
| `M-55` | The gap list is the point. A coverage number without named gaps is a claim; with them it is evidence (`P-15`) |
| `M-57` | Zero is required, and the planted sentinels are what make zero meaningful (`19 § 7`) |

---

## 8. Metric requirements

| ID | Requirement |
|---|---|
| `RR-METRIC-001` | The primary metric is `M-10`, computed by paired policy comparison against `B0` |
| `RR-METRIC-002` | Every metric emits a `MetricSnapshot` with a `derivation_ref` |
| `RR-METRIC-003` | `M-05` is never reported without `M-06`, `M-07`, and `M-09` in the same block, and the identity is asserted |
| `RR-METRIC-004` | `M-16`, `M-17`, `M-18`, `M-22` must be zero; non-zero invalidates the run and it produces no metrics |
| `RR-METRIC-005` | `M-16`, `M-17`, `M-18` are computed by evaluators independent of the runtime components they audit |
| `RR-METRIC-006` | No metric is reported without its unit and direction |
| `RR-METRIC-007` | Money metrics are integer paise throughout; conversion to rupees happens only at presentation |
| `RR-METRIC-008` | Ratios with a zero or near-zero denominator are reported as undefined, never as a large number |
| `RR-METRIC-009` | Coverage metrics publish their gap lists |
| `RR-METRIC-010` | An `M-10` gain accompanied by a worse `M-13` is presented as a trade-off, not an improvement |
| `RR-METRIC-011` | `M-12` and `M-19` are reported together — over-acting and under-acting side by side |
| `RR-METRIC-012` | Oracle-dependent metrics (`M-12`, `M-19`, `M-20`, `M-25`, `M-26`, `M-27`, `M-28`) are labelled oracle-dependent wherever they appear and carry `D-E3` |
| `RR-METRIC-013` | No metric may appear in a report that is not defined in this document |
| `RR-METRIC-014` | No metric definition changes after the parameter freeze without a full re-run (`19 § 8.3`) |
| `RR-METRIC-015` | No metric is reported as a percentage improvement without the absolute values beside it |
| `RR-METRIC-016` | Tier membership is read from § 0's table, never inferred from the ID |

`RR-METRIC-012` exists because seven of the most persuasive metrics here are computable **only** because
the world is synthetic. Every one of them must carry that fact wherever it travels.

---

## 9. Deliberately absent metrics

| Absent | Why |
|---|---|
| Recovery rate (`recovered / detected`) | Maximised by detecting less. If shown at all, only beside `M-01` and `M-10` |
| Action success rate | Conflates a delivered action with recovered money (`15 § 5.1`) |
| Conversion rate on actioned opportunities | Ignores the counterfactual; maximised by acting only where recovery is certain |
| LLM accuracy or quality score | Not a business outcome; `M-27`, `M-50`, `M-51` cover what is measurable |
| Time saved or manual effort avoided | No human baseline exists here, so any figure would be invented |
| Customer satisfaction | No instrument exists in a synthetic environment; inventing one would be fabrication |
| Any per-merchant projection or extrapolation | Would be a claim about reality (`README § C-8`) |
| A composite score across tiers | Would let a tier-2 loss be bought with a tier-1 gain, which `21 § 1` forbids |

Listing absences matters: the reviewer's question is usually "why isn't X here?", and the honest answer
is often "because X is the metric that would let us cheat."

---

## 10. Open items

| Item | Label |
|---|---|
| Calibration bin edges and count for `M-24` | `PROPOSED`; frozen before measurement |
| Whether `M-13` should count non-contact actions in a separate denominator | `PROPOSED` yes, reported separately |
| Whether `M-25` should be decile lift or a Qini-style curve | `PROPOSED` decile lift, for interpretability |
| Billing currency for `M-49` | `PROPOSED` reported in the provider's billing currency, unconverted |
| Threshold for "near-zero denominator" in `RR-METRIC-008` | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION` |
| Whether `M-21`'s `unobservable_rate` should gate reporting of `M-06` | `PROPOSED` no, but the two are printed adjacently |
