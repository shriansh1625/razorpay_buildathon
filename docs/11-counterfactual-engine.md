# 11 · Counterfactual Engine

The counterfactual engine answers one question for every (opportunity, action) pair:

> **How much more money arrives if we do this, compared with doing nothing — and is that difference
> worth what the action costs?**

It produces uplift, prices it, and attaches an uncertainty interval. It does **not** establish
causation, and § 8 states plainly what it cannot claim.

---

## 1. What "counterfactual" means here — and what it does not

| Claim | Status |
|---|---|
| "We estimate the difference between two modelled outcomes: acting and not acting" | ✅ This is what the engine does |
| "We compare a policy against alternative policies on the same batch, under a paired design" | ✅ This is what [21-evaluation.md](21-evaluation.md) does |
| "We have identified the causal effect of an intervention on a real customer" | ❌ Not claimed. Not claimable from this design |
| "Our uplift estimates are unbiased on real traffic" | ❌ Not claimed. They are estimates from a synthetic response model |
| "This is a randomised controlled experiment" | ❌ It is a paired simulation against a common hidden outcome model |

The vocabulary discipline of `PP-4` applies throughout: **modelled**, **estimated**, **candidate**,
**on synthetic data**. The words *proven*, *causal*, and *guaranteed* do not appear in outputs.

---

## 2. The horizon

Uplift is undefined without a horizon. `H` is the window after a decision within which recovery is
counted.

| Rule | Statement |
|---|---|
| `H` is per risk class | A failed subscription renewal and a 60-day-overdue invoice do not share a recovery horizon |
| `H` is fixed before measurement | Choosing `H` after seeing results is the most common way to manufacture uplift. Frozen in the policy pack, versioned, and recorded on every decision |
| `H` is identical across all baselines | A baseline evaluated on a different horizon is not a baseline (`RR-BENCH-*`) |
| Recovery after `H` | Counted separately as `late_recovery`, reported, and **excluded** from attributed uplift |
| `H` never exceeds the recovery window | `min(H_class, window_expires_at − now)` |

Proposed values are `PROPOSED` placeholders in the policy pack; the real values are an open item
(§ 10).

---

## 3. The action catalogue

Fifteen action codes, one of which is `NO_ACTION`. Each declares its resources, cost structure,
reversibility, and tier. Cost *values* are policy-pack parameters, not fixed here.

| Code | Action | Family | Resources consumed | `d>0`? | Reversible | Tier |
|---|---|---|---|---|---|---|
| `A00` | `NO_ACTION` | — | none | no | n/a | T1 |
| `A01` | `RETRY_PAYMENT_NOW` | Payment | `retry_slots` | no | **false** | T1 |
| `A02` | `RETRY_PAYMENT_SCHEDULED` | Payment | `retry_slots` | no | **false** | T1 |
| `A03` | `REQUEST_INSTRUMENT_UPDATE` | Payment + comms | `message_capacity`, `contact_allowance` | no | **false** | T1 |
| `A04` | `SUGGEST_ALTERNATE_METHOD` | Payment + comms | `message_capacity`, `contact_allowance` | no | **false** | T1 |
| `A05` | `SEND_REMINDER` | Comms | `message_capacity`, `contact_allowance` | no | **false** | T1 |
| `A06` | `SEND_PAYMENT_LINK` | Comms | `message_capacity`, `contact_allowance` | no | **false** | T1 |
| `A07` | `SEND_CHECKOUT_RESUME_LINK` | Comms | `message_capacity`, `contact_allowance` | no | **false** | T1 |
| `A08` | `SEND_DUNNING_NOTICE` | Comms | `message_capacity`, `contact_allowance` | no | **false** | T2 |
| `A09` | `SEND_FINAL_NOTICE` | Comms | `message_capacity`, `contact_allowance` | no | **false** | T2 |
| `A10` | `OFFER_INCENTIVE` | Incentive | `incentive_budget`, `message_capacity`, `contact_allowance` | **yes** | **false** | T2 |
| `A11` | `OFFER_EXTENSION_OR_INSTALMENT` | Incentive | `incentive_budget`, `message_capacity`, `contact_allowance` | **yes** | **false** | T2 |
| `A12` | `VOICE_OUTREACH` | Voice | `voice_minutes`, `contact_allowance` | no | **false** | **T3** |
| `A13` | `ROUTE_TO_HUMAN_REVIEW` | Human | `human_review_slots` | no | true | T1 |
| `A14` | `PREPARE_COLLECTIONS_HANDOFF` | Human | `human_review_slots` | no | true | T2 |

### 3.1 Notes on the catalogue

- **Reversibility.** Twelve of the fourteen real actions are irreversible: money moved, or a message a
  customer has already read. Per `P-5`, every irreversible action requires an idempotency key, a
  budget reservation, and an audit event **before** the adapter call.
- **`A12 VOICE_OUTREACH` is one row.** It sits at T3 with a T3 resource. It is not the product; it is
  a channel whose `ENRV` must beat the alternatives like any other. See
  [01-track-alignment.md § 4](01-track-alignment.md).
- **`A14 PREPARE_COLLECTIONS_HANDOFF` prepares a human task.** It does not initiate legal or
  collections action autonomously (`OS-08`). The action's effect is a queue entry for a person.
- **No action escalates itself.** Escalation tiers (`A08` → `A09` → `A14`) are separate action codes,
  each priced and gated independently in a later cycle. There is no code path where one action
  automatically becomes a stronger one.
- **`incentive_tier` is a bounded enum**, not a free number, and it is clamped by `G5`
  (`RR-GUARD-005`). No LLM selects it (`RR-GUARD-020`).

---

## 4. The predictor

### 4.1 What must be estimated

| Quantity | Meaning |
|---|---|
| `p(i, a)` | Probability the recoverable amount for `i` is recovered within `H`, **given** action `a` |
| `p(i, ∅)` | Probability it is recovered within `H` with **no** action — the natural-recovery baseline |
| `σ(i, a)` | Uncertainty of the uplift estimate |

`p(i, ∅)` is the load-bearing quantity. If it were modelled as a constant, then
`u = p(i,a) − const`, uplift would be a monotone transform of `p(i,a)`, and the whole system would
collapse into "act where conversion is likeliest" — which is a rejected objective
([00-project-charter.md](00-project-charter.md) § 4). Therefore:

> **`RR-FUNC-023` requires `p(i,∅)` to be estimated per opportunity from features that genuinely
> vary**: ageing, prior self-recovery behaviour, failure cause, instrument state, customer segment,
> amount band, and time-to-window-close.

A test asserts that `p(i,∅)` has non-trivial variance across the batch and that its rank correlation
with `p(i,a)` is materially below 1. If it is not, the model is degenerate and the finding is
reported.

### 4.2 Model family

Two candidate families, both deterministic, both interpretable (`OS-36` rejects deep models; see
`ADR-006`).

| Option | Description | Pros | Cons |
|---|---|---|---|
| **Beta-Binomial per cell** (`PROPOSED` default) | Discretise features into cells; maintain `Beta(α,β)` posteriors; `p̂ = α/(α+β)` | Trivially interpretable, natural uncertainty, closed-form update, exact reproducibility, supports Thompson sampling directly | Cell explosion; sparse cells need shrinkage |
| **Hierarchical logistic regression** | Pooled coefficients with class-level random effects | Handles continuous features, less sparsity | Needs a fitting step, harder to make byte-reproducible, uncertainty requires extra work |

**Decision:** start with Beta-Binomial with explicit hierarchical shrinkage; treat hierarchical
logistic as an alternative evaluated in an ablation. Recorded as `ADR-005`. Whether the two need
*different* families for `p(i,a)` and `p(i,∅)` is an open item (§ 10).

### 4.3 Cell definition and shrinkage

Cells are the cross-product of coarse bands:

```
cell = ( risk_class,
         cause_code,
         action_code,
         amount_band,          # 4–5 bands
         ageing_bucket,        # 3–4 buckets
         customer_history_band # 3 bands: never_recovered / sometimes / usually
       )
```

A three-level shrinkage hierarchy, so a sparse cell is never trusted:

```
level 0:  exact cell
level 1:  parent  = drop customer_history_band, then amount_band
level 2:  root    = (risk_class, action_code)
```

```
p̂ = (n_cell·p̄_cell + κ₁·p̂_parent + κ₂·p̂_root) / (n_cell + κ₁ + κ₂)
```

with `κ` fixed in the policy pack. Consequences that must hold:

- A cell with `n = 0` returns the parent estimate with **inflated `σ`**, never a default of 0.5 and
  never a silent zero.
- `unseen_cell_rate` is a reported metric. A high rate means the batch is more diverse than the
  training split, which is information, not an error to hide.

### 4.4 Feature list

Only features derivable from the `ContextObject` (`RR-FUNC-013`…`017`). No feature may derive from the
hidden oracle (`AI-6`), and a test asserts the feature extractor cannot import the generator's
response model.

| Group | Features |
|---|---|
| Opportunity | `risk_class`, `value_at_risk_band`, `ageing_bucket`, `time_to_window_close_band`, `attempt_seq` |
| Diagnosis | `top_cause_code`, `confidence_band`, `unclassified`, `degradation_flag`, `degradation_severity` |
| Instrument | `method_type`, `instrument_expiry_state`, `mandate_state`, `prior_failure_count_on_instrument` |
| Customer | `history_band`, `prior_self_recovery_rate_band`, `tenure_band`, `contacts_last_7d`, `fatigue_index_band` |
| Timing | `merchant_local_hour_band`, `day_type` (weekday/weekend), `salary_cycle_proximity_band` |
| Action | `action_code`, `channel`, `incentive_tier`, `delay_band` |
| Context quality | `context_degraded` |

### 4.5 Calibration is the priority, not discrimination

`ENRV` is **linear in `p`**. A model with excellent ranking but poor calibration produces excellent
rankings of *wrong prices*, and prices are what the allocator spends money against. Therefore:

| Metric | Role |
|---|---|
| Brier score | Primary (`M-24`) |
| Expected Calibration Error | Primary (`M-24`) |
| Reliability curve | Reported per risk class |
| AUC / lift curves | Secondary, reported but never headline |

A miscalibrated predictor that still wins on `M-10` is reported as such, because it means the win
came from ordering rather than pricing, and that is a fragile win worth disclosing.

### 4.6 Prohibitions

| Prohibition | Requirement |
|---|---|
| No LLM produces or adjusts `p` | `RR-GUARD-020` |
| No access to the hidden oracle | `AI-6`, `RR-BENCH-005` |
| No fitting on the evaluation split | `RR-BENCH-*`, train/eval separation |
| No wall clock, no unseeded randomness | `RR-NFR-004`, `RR-NFR-005` |
| Parameters read-only during a cycle | Snapshot `StrategyVersion` at cycle open |
| Only C-21 may write parameters, and nothing else | `RR-GUARD-022`, `P-12` |

---

## 5. The objective function, term by term

```
u(i,a)     = p(i,a) − p(i,∅)

ENRV(i,a)  =   u(i,a) · V(i) · m          (1) expected incremental gross
             − c(a)                       (2) unconditional direct cost
             − p(i,a) · d(i,a)            (3) expected conditional incentive cost
             − λ_f · F(i,a)               (4) fatigue externality

ENRV(i,∅)  = 0                            by definition
```

### 5.1 Term-by-term specification

| Term | Unit | Sign | Conditional? | Specification |
|---|---|---|---|---|
| `u(i,a)` | probability | may be **negative** | — | Negative uplift is real: a badly-timed dunning notice can suppress payment. Negative-uplift candidates must survive to the allocator and be rejected *on price*, not filtered out earlier — otherwise the system can never demonstrate that it declined a harmful action (`M-20`) |
| `V(i)` | paise | ≥ 0 | — | **Recoverable** amount, not invoiced amount. Excludes amounts already written off, disputed, refunded, or outside the addressable set (`RR-FUNC-007`) |
| `m` | ratio | `(0, 1]` | — | Merchant net-retention factor: the fraction of recovered gross the merchant actually keeps after fees, refunds, and downstream churn. Default `1.0` as an `ASSUMPTION`, which makes REVIVE's reported value **an upper bound** — stated, not hidden |
| `c(a)` | paise | ≥ 0 | **Unconditional** | Paid whether or not recovery happens: message send fee, voice minutes, retry processing cost, reviewer time. Charged once per attempt |
| `d(i,a)` | paise | ≥ 0 | **Conditional on success** | The incentive actually granted. Enters the objective as `p(i,a) · d(i,a)`. Reserved unconditionally in the ledger ([10 § 3.3](10-recovery-allocation.md)) — priced in expectation, reserved conservatively |
| `F(i,a)` | fatigue units | ≥ 0 | — | Externality: the expected future value destroyed by consuming this customer's tolerance. Increases with recent contact count, channel intrusiveness, and customer value |
| `λ_f` | paise per fatigue unit | ≥ 0 | — | Converts fatigue to money. Default `1.0` (`PROPOSED`). It is a **merchant policy dial**, not a learned parameter — `RR-GUARD-022` forbids the learner from touching it |

### 5.2 The two errors this structure prevents

1. **Charging the incentive unconditionally** would make incentives look uniformly worse than they
   are and suppress `A10`/`A11` entirely.
2. **Charging the incentive as if always paid *and* reserving it in expectation** would allow realised
   spend to exceed the budget when several incentives land at once.

REVIVE prices in expectation (term 3) and reserves conservatively (ledger). The gap between the two is
reported as `budget_reservation_slack`, not concealed.

### 5.3 The action threshold

```
act(i,a)  ⟺  ENRV(i,a) > ε   and   a ≠ ∅
```

`ε > 0` strictly. `ε = 0` would authorise actions of zero expected value, which spend real resources
for no modelled gain and inflate action counts — precisely the activity bias `P-1` rejects. `ε` is a
policy parameter and the evaluation includes an `ε` sensitivity sweep.

### 5.4 Arithmetic discipline

| Rule | Requirement |
|---|---|
| `V`, `c`, `d`, `ENRV` are integers in paise | `RR-NFR-001` |
| `p`, `u`, `m`, `λ_f` are floats | `RR-NFR-002` |
| Float → paise conversion happens **once**, at persistence, banker's rounding | `RR-NFR-002` |
| Stored `ENRV` equals the exact sum of stored components, zero residual | `RR-FUNC-029` |
| All comparisons and sorts operate on integer paise | [10 § 7](10-recovery-allocation.md) |

---

## 6. Properties the engine must satisfy

Asserted as property tests, because a pricing bug is silent and expensive.

| # | Property | Statement |
|---|---|---|
| CF-1 | `NO_ACTION` neutrality | `ENRV(i,∅) = 0` exactly, for every `i` |
| CF-2 | Monotone in value | `V ↑` with all else fixed and `u > 0` ⟹ `ENRV ↑` |
| CF-3 | Monotone in uplift | `u ↑` with all else fixed ⟹ `ENRV ↑` |
| CF-4 | Monotone in cost | `c ↑` ⟹ `ENRV ↓`, one paise for one paise |
| CF-5 | Monotone in fatigue aversion | `λ_f ↑` ⟹ `ENRV ↓` for any action with `F > 0`; and `λ_f → ∞` ⟹ all contact actions rejected |
| CF-6 | Zero-uplift rejection | `u = 0` and any cost `> 0` ⟹ `ENRV < 0` ⟹ never selected |
| CF-7 | Natural-recovery dominance | `p(i,∅) → 1` ⟹ `u → 0` ⟹ no action selected, regardless of `V`. **This is the test that the "don't chase customers who were going to pay" behaviour actually exists** |
| CF-8 | Component reconstruction | Stored components sum exactly to stored `ENRV` |
| CF-9 | Interval containment | `ENRV_point ∈ ENRV_interval`; interval width increases with `σ` |
| CF-10 | Sign symmetry | Negative `u` with any positive cost ⟹ `ENRV < 0`; such candidates appear in the candidate set and are counted in `M-20` |
| CF-11 | Unit safety | No test can produce an `ENRV` from mixed rupee/paise inputs without failing a type check |
| CF-12 | Determinism | Identical inputs ⟹ bit-identical `ENRV` |

---

## 7. Uncertainty

### 7.1 Where `σ` comes from

Beta-Binomial posteriors give variance directly. For an uplift that is a difference of two estimated
probabilities:

```
Var(u) ≈ Var(p_a) + Var(p_∅)      # conservative: assumes independence, which over-states variance
```

Over-stating uncertainty is the safe direction: it widens intervals and pushes marginal cases toward
review or no-action.

### 7.2 How uncertainty is used

Three uses, all explicit:

| Use | Mechanism |
|---|---|
| **Interval reporting** | Every `ENRV` carries `[lo, hi]`, rendered in the UI (`RR-UI-003`) |
| **Escalation trigger** | High `V(i)` combined with a wide interval routes to `REQUIRE_APPROVAL` (`RR-GUARD-007`) — uncertainty on a large amount is exactly when a human should look |
| **Exploration** | Thompson sampling draws from the posterior, under the capped exploration budget (`RR-FUNC-081`) |

Uncertainty is **not** used to inflate `ENRV`. There is no optimism bonus in the exploitation path;
optimism lives only in the separately-budgeted exploration path, so an exploration bug cannot spend
the recovery budget.

### 7.3 The `context_degraded` path

When context assembly is incomplete, `σ` inflates. The consequence is automatic and desirable: wider
intervals lower the number of candidates clearing `ε` with confidence, and raise the number routed to
approval. Degraded input therefore produces *less* autonomous action, not equally confident action on
worse data.

---

## 8. Limits — what this engine cannot claim

Read this section as the honest answer to "so you've built causal inference?" — no.

| # | Limitation |
|---|---|
| L-1 | **`p(i,∅)` is never directly observed for an opportunity that was acted on.** The fundamental problem of causal inference applies. In the benchmark the generator's hidden oracle lets the *evaluator* compute the counterfactual, but the decision policy never sees it, and on real data it would not exist at all |
| L-2 | **Uplift estimates are calibrated against a synthetic response model.** Their accuracy on real traffic is unknown and unclaimed |
| L-3 | **No causal identification strategy is used.** No randomised holdout on real traffic, no instrumental variable, no DiD, no propensity weighting on observational data. The paired-policy design in [21](21-evaluation.md) is a *simulation* comparison, not an experiment |
| L-4 | **Attribution of an individual recovery is unreliable.** A recovery after a reminder may have happened anyway. This is why `M-10` is computed by **paired policy comparison**, not by summing attributed individual recoveries (`RR-FUNC-071`) |
| L-5 | **Interference is not modelled.** Contacting a customer about invoice A may affect invoice B. The model treats opportunities as independent given features, which is an `ASSUMPTION` |
| L-6 | **Long-run effects beyond `H` are not modelled**, except crudely through `F(i,a)`. Churn caused by over-contact is proxied by a fatigue term, not measured |
| L-7 | **`m = 1.0` by default**, so reported value is an **upper bound** on merchant-retained value |
| L-8 | **Model misspecification is not detectable from within.** If the true response surface differs in shape from the assumed family, calibration metrics on synthetic data will not reveal it, because the synthetic data was generated by a model of the same general kind |
| L-9 | **The oracle-gap metric bounds how much of the achievable value the policy captured** — but only within the synthetic world. It says nothing about the real world |

### 8.1 The required disclosure sentence

Any external presentation of uplift figures must carry:

> *"All uplift and recovery figures are produced by a synthetic outcome model, not by real payment
> rails. No causal claim about real customer behaviour is made."*

This is the same clause frozen in [01-track-alignment.md § 7](01-track-alignment.md).

---

## 9. Requirement mapping

| Requirement | Where satisfied |
|---|---|
| `RR-FUNC-020`…`022` candidate sets | [09 § 2.4](09-decision-engine.md); catalogue § 3 |
| `RR-FUNC-023` per-opportunity `p(i,∅)` | § 4.1 |
| `RR-FUNC-025` uplift computed as a difference | § 5 |
| `RR-FUNC-026` cost model | § 5.1 |
| `RR-FUNC-027` `ENRV` with interval | § 5, § 7.1 |
| `RR-FUNC-028` uncertainty estimated | § 7 |
| `RR-FUNC-029` component reconstruction | CF-8 |
| `RR-GUARD-020` no LLM numbers | § 4.6 |
| `RR-NFR-001`/`002` money arithmetic | § 5.4 |
| `RR-NFR-003` purity | CF-12 |
| `AG-13` no causal claim | § 8 |

---

## 10. Open items

| Item | Label |
|---|---|
| `H` per risk class | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION`; must be frozen before any measurement |
| Whether `p(i,a)` and `p(i,∅)` need different model families | `UNKNOWN`; both options in § 4.2, decide by ablation |
| Shrinkage constants `κ₁`, `κ₂` | `UNKNOWN`; sensitivity required |
| Functional form of `F(i,a)` | `PROPOSED`; a monotone function of recent contact count, channel intrusiveness, and customer value band. Exact form undecided |
| Real value of `m` | `ASSUMPTION` `1.0`; a real value needs merchant margin and refund data that does not exist here |
| Cost values `c(a)` | `UNVERIFIED` for anything provider-dependent (message fees, retry costs) — see [36](36-razorpay-integration-assumptions.md) |
| Whether `retry_slots` scarcity should also appear inside `c(a)` | `PROPOSED` no — scarcity belongs in the shadow price, not the direct cost, to avoid double-counting |
| Salary-cycle timing feature | `ASSUMPTION` that it matters; included as a feature, and its learned effect is reported rather than presumed |
