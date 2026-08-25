# 09 · Decision Engine

The decision engine is the part of REVIVE that turns *"here is an opportunity"* into *"here is the
action we will take, at this price, for this reason, or here is why we will take none."*

It is specified here as a pipeline of pure functions over a frozen input set. The allocator, which
resolves contention *between* opportunities, is specified separately in
[10-recovery-allocation.md](10-recovery-allocation.md); this document covers everything up to and
including the decision record, plus the semantics that make a decision meaningful.

---

## 1. The decision problem, stated precisely

For a cycle `t`, given:

- a set of open, addressable opportunities `I_t`
- for each `i ∈ I_t`, a feasible action set `A_i` (always containing `∅` = `NO_ACTION`)
- resource capacities `B_t` over resources `R`
- a policy pack `P` and its gates
- a strategy version `S` supplying predictor parameters

choose an assignment `x : I_t → A_i` maximising

```
Σ_{i ∈ I_t}  ENRV(i, x(i))
```

subject to

```
∀ r ∈ R :   Σ_i  usage_r(i, x(i))  ≤  B_t[r]
∀ i     :   gates(P, i, x(i))  =  ALLOW
∀ i     :   ENRV(i, x(i))  >  ε   or   x(i) = ∅
```

Three properties of this statement are load-bearing:

1. **The objective sums over the batch**, not over one opportunity. This is what makes it an
   allocation problem rather than a rules engine.
2. **`ENRV(i, ∅) = 0` by definition**, so `NO_ACTION` is always feasible and always priced. There is
   no configuration under which the system is forced to act.
3. **The gate constraint is not a penalty term.** It is a hard feasibility constraint evaluated by a
   separate component with final authority. It cannot be traded off against `ENRV`, however large
   `ENRV` is. See [13-policy-and-guardrails.md](13-policy-and-guardrails.md).

---

## 2. The pipeline

Nine stages. Each is a pure function of its inputs plus `(S, P, seed)`.

```
 (1) SELECT      open opportunities eligible for this cycle
 (2) ENRICH      → ContextObject                      [C-04]
 (3) DIAGNOSE    → Diagnosis (ranked candidate causes) [C-05]
 (4) GENERATE    → ActionCandidate[]  (incl. NO_ACTION)[C-06]
 (5) PREDICT     → p(i,a), p(i,∅), σ  per candidate    [C-07]
 (6) PRICE       → c(a), d(i,a), F(i,a)                [C-08]
 (7) EVALUATE    → ENRV(i,a), uplift, interval         [C-09]
 (8) PRE-FILTER  → drop never-allowable candidates     [C-11]
 (9) ALLOCATE    → Decision per opportunity            [C-12]
     ────────────── then GUARD, which can still deny ──────────── [C-13]
```

### 2.1 Stage 1 — Selection

An opportunity enters cycle `t` if all hold:

| Condition | Source |
|---|---|
| State ∈ `{DETECTED, DIAGNOSED, DEFERRED, AWAITING_OUTCOME_WITH_CAPACITY}` | [34-state-machine.md](34-state-machine.md) |
| `addressable = true` | `RR-FUNC-008` |
| Recovery window not expired at virtual `now` | `SR-01` |
| No stopping rule already satisfied | `RR-FUNC-050` |
| Not in `RECONCILING` | `RR-FUNC-065` |
| `next_eligible_at ≤ now` (cooldown honoured) | `RR-GUARD-004` |

Selection is deliberately *inclusive*: an opportunity that will certainly be denied still enters, so
that its denial is recorded and countable (`AI-8`, set-completeness). Only the pre-filter (stage 8)
removes candidates, and it records why.

**Ordering.** Selected opportunities are sorted by `(opportunity_id)` — a ULID, hence stable — before
any downstream processing, so that iteration order never affects output (`RR-NFR-006`).

### 2.2 Stage 2 — Enrichment

Produces a `ContextObject`. Two rules matter:

- **Every field is present or explicitly null with a reason code.** There is no "missing means zero".
- If any field material to prediction is null, `context_degraded = true`, which inflates `σ` in
  stage 5 rather than silently degrading the estimate.

### 2.3 Stage 3 — Diagnosis

Deterministic taxonomy lookup first. The LLM is consulted only for the residual (unmapped or
conflicting evidence), returns a ranked list of **closed-set** cause codes with confidence *bands*,
and never a number. Bands map to numeric priors via a versioned table the analyst cannot read.

Diagnosis affects the decision in exactly two ways, both structural:

1. It **shapes the candidate set** (stage 4) — different causes make different actions feasible.
2. It **selects the predictor cell** (stage 5) — cause is a feature.

It never adjusts a price directly. See [08 § 4](08-agent-architecture.md) C-05.

### 2.4 Stage 4 — Candidate generation

Rule-table driven, from `(risk_class, cause_code, context flags)`. Guarantees:

- ≥ 2 real candidates plus `NO_ACTION` for every addressable opportunity (`RR-FUNC-021`)
- Candidate sets differ across cause codes — asserted in test, because an identical candidate set
  for every cause would mean diagnosis is decorative
- Candidates carry parameters: `delay_minutes`, `channel`, `incentive_tier`, `template_id`,
  `requires_approval_hint`

### 2.5 Stage 5 — Prediction

For each candidate, the predictor returns `p(i,a)`, and separately `p(i,∅)`, the natural-recovery
probability over the same horizon `H`. **`p(i,∅)` is estimated per opportunity, not as a global
constant** — this is the single most important modelling requirement in the system, because uplift is
a difference against it and a constant baseline would make uplift a monotone transform of `p(i,a)`,
collapsing the whole design back into "act on whatever is most likely to convert".

Model family, horizon semantics, feature list, calibration and shrinkage: see
[11-counterfactual-engine.md](11-counterfactual-engine.md) § 4.

### 2.6 Stages 6–7 — Pricing and evaluation

```
u(i,a)    = p(i,a) − p(i,∅)                       uplift, may be negative
gross(i,a)= u(i,a) · V(i) · m                     expected incremental gross, paise
ENRV(i,a) = gross(i,a) − c(a) − p(i,a)·d(i,a) − λ_f·F(i,a)
```

Every term, its unit, its sign convention, and the conditional-vs-unconditional distinction are
specified in [11 § 5](11-counterfactual-engine.md). Two properties are asserted in code:

- **Component-sum reconstruction:** the stored `ENRV` equals the sum of its stored components
  exactly, in paise, with no residual (`RR-FUNC-029`).
- **Interval containment:** `enrv_point ∈ enrv_interval`.

### 2.7 Stage 8 — Pre-filter

Removes only candidates that **no gate could ever allow** in this cycle (no consent, channel
ineligible, outside communication window, already at hard contact cap, duplicate in flight). Each
removal stores a `prefilter_reason`.

Pre-filter passing grants nothing. The full gate suite still runs after allocation
(`RR-FUNC-037`). The over-filter test asserts that nothing the pre-filter removed would have been
allowed by the full gates; where uncertain, the pre-filter must **not** filter.

### 2.8 Stage 9 — Allocation

Specified in [10-recovery-allocation.md](10-recovery-allocation.md).

---

## 3. Decision semantics

Four outcomes, mutually exclusive and exhaustive. Every opportunity that entered the cycle receives
exactly one (`RR-FUNC-040`, `AI-8`).

| Outcome | Meaning | Ledger effect | Countable as |
|---|---|---|---|
| `SELECTED(a)` | Action `a` proposed and gate-allowed; will execute this cycle | Reservation held, then committed | An intervention |
| `DEFERRED(reason)` | Positive `ENRV` existed but this cycle could not act | Reservation released | A constraint cost — feeds `M-19` |
| `REJECTED(reason)` | A gate denied every real candidate | None | A guardrail event — feeds `M-14` |
| `NO_ACTION(reason)` | `∅` was the best-priced option, or every real candidate had `ENRV ≤ ε` | None | A deliberate economic choice — feeds `M-15` |

### 3.1 The distinction that matters most

`DEFERRED` and `NO_ACTION` must never be conflated.

- `NO_ACTION` says **"acting is not worth it."** It is an economic judgement. If it is wrong, the
  cost appears in `M-19 Missed Opportunity Value`.
- `DEFERRED` says **"acting is worth it but we could not."** It is a capacity statement. If it
  happens often, the report shows a binding constraint and a shadow price, which is a *merchant
  finding* ("your incentive budget is the limiting factor, and its marginal value is X paise per
  paise").

Collapsing them would hide the single most useful output the allocator produces. Enforced by
`RR-FUNC-041` and asserted by a test that no `DEFERRED` decision carries a `NO_ACTION` reason code
and vice versa.

### 3.2 Reason codes

Every non-`SELECTED` decision carries a code from a closed enumeration, never free text. Illustrative
groupings (full list in [37-metrics-dictionary.md](37-metrics-dictionary.md) § 7):

| Group | Examples |
|---|---|
| `NO_ACTION_*` | `BELOW_EPSILON`, `NEGATIVE_UPLIFT`, `NATURAL_RECOVERY_LIKELY`, `VALUE_TOO_LOW`, `COST_EXCEEDS_GAIN`, `FATIGUE_COST_DOMINATES` |
| `DEFERRED_*` | `BUDGET_EXHAUSTED`, `CHANNEL_CAPACITY`, `COOLDOWN`, `AWAITING_APPROVAL`, `OUTSIDE_WINDOW`, `ALLOCATOR_CAPACITY`, `PREDICTOR_DEGRADED` |
| `REJECTED_*` | `NO_CONSENT`, `CONTACT_CAP`, `RETRY_CAP`, `INCENTIVE_CEILING`, `RISK_BLOCK`, `DUPLICATE`, `CHANNEL_INELIGIBLE`, `AMOUNT_SANITY`, `STOPPED` |

Reason codes are a product surface, not a log detail: they populate the UI, the report, and the
merchant-facing explanation.

---

## 4. The decision record

One immutable row per `(cycle_id, opportunity_id)`. It is the explainability substrate — P-6 requires
that deleting every LLM-generated text field leaves this record sufficient to explain the decision.

| Field | Notes |
|---|---|
| `decision_id` | `dec_<ULID>` |
| `cycle_id`, `opportunity_id` | |
| `outcome` | `SELECTED` / `DEFERRED` / `REJECTED` / `NO_ACTION` |
| `chosen_action_code` | null unless `SELECTED` |
| `chosen_action_params` | delay, channel, incentive tier, template id |
| `candidate_set_ref` | all candidates considered, with prices — **the full set, not just the winner** |
| `enrv_chosen_paise`, `enrv_runner_up_paise` | the margin is what makes the choice legible |
| `enrv_components` | `gross`, `c`, `expected_incentive`, `fatigue` — each in paise |
| `p_action`, `p_natural`, `uplift`, `sigma` | the estimates as of decision time, frozen |
| `binding_constraints` | resources that bound this cycle |
| `shadow_prices` | per binding resource |
| `gate_trace_ref` | every gate, in order, with verdict |
| `reason_code` | closed set |
| `allocator_mode` | `EXACT` / `LAGRANGIAN` / `FALLBACK_GREEDY` |
| `strategy_version`, `policy_pack_version`, `generator_version`, `seed` | reproducibility quad |
| `diagnosis_ref` | ranked causes + evidence refs |
| `explanation_text` | **derived**, nullable, never authoritative |
| `decided_at` | virtual clock |

**Immutability.** Decisions are never updated. A changed circumstance produces a *new* decision in a
later cycle. Outcomes attach by reference, not by mutation (`RR-FUNC-044`).

---

## 5. Worked structure of an explanation

Given the record above, the system can answer — from stored rows alone — every question a reviewer
or merchant will ask:

| Question | Answered from |
|---|---|
| What did you do? | `chosen_action_code`, `chosen_action_params` |
| What else did you consider? | `candidate_set_ref` |
| Why this one? | `enrv_chosen` vs `enrv_runner_up`, with components |
| Why act at all? | `uplift`, `p_natural`, `ε` |
| Why not more? | `binding_constraints`, `shadow_prices` |
| Was it allowed? | `gate_trace_ref` |
| Who decided? | `allocator_mode` + approval record if any |
| Would it be the same tomorrow? | `strategy_version`, `policy_pack_version`, `seed` |
| Did it work? | linked `Outcome` (later cycle) |

No LLM is required for any row in that table. That is the test of P-6.

---

## 6. Reconciling LLM reasoning with byte-identical reproducibility

This is the hardest constraint in the package: `RR-NFR-020` demands byte-identical artefacts at a
fixed seed, and LLM outputs are not reproducible. The resolution is a **content-addressed cache with
a closed-set validator**, and a strict rule about when the cache may be populated.

### 6.1 Cache key

```
key = H( prompt_version, model_id, decoding_params, seed, opportunity_id, input_hash )
```

where `input_hash` is a canonical hash of the exact serialised context passed to the model. Any change
to the prompt, the model, the decoding parameters, or the input produces a different key — so a stale
cache can never masquerade as a fresh answer.

### 6.2 Two phases, strictly separated

| Phase | Network | Cache | Determinism |
|---|---|---|---|
| **Cache population** (`PREPARE`) | Allowed | Written | Not required. Explicitly labelled as a non-benchmark step |
| **Benchmark run** (`EVALUATE`) | **Forbidden** (`RR-NFR-092`) | Read-only | **Required.** Cache miss is a hard error, not a fallback |

`RR-NFR-035` asserts the uncached-call counter is exactly `0` during a benchmark run. If population
was incomplete, the run fails loudly rather than producing a differently-shaped result.

### 6.3 Validation before caching

An LLM response is cached only after it passes schema validation against the closed set. Invalid
responses are recorded (`llm_output_rejected{reason}`) and the deterministic fallback is cached in
their place. Consequence: the cache contains only values the system would accept, so the benchmark
never exercises a code path that production wouldn't.

### 6.4 What this costs, stated honestly

| Cost | Statement |
|---|---|
| The benchmark does not test LLM variance | True. Variance is measured separately by re-populating the cache at *k* different sampling seeds and reporting decision-flip rate as a sensitivity result, not as a headline metric |
| Cache population is a manual prerequisite | True, and it is documented as a step in the run instructions |
| A prompt change invalidates prior artefacts | True, and desirable — `prompt_version` is part of the reproducibility quad |

### 6.5 The ablation that keeps this honest

Because both agents have complete deterministic fallbacks, the benchmark can be run in three modes:

| Mode | Diagnosis | Copy |
|---|---|---|
| `LLM_OFF` | taxonomy lookup only; residual → `UNCLASSIFIED` | static templates |
| `LLM_DIAGNOSIS_ONLY` | LLM-assisted | static templates |
| `LLM_FULL` | LLM-assisted | generated |

All three are reported. If `LLM_OFF` performs as well as `LLM_FULL` on `M-10`, the package says so
— that is a finding about where the value actually lives, and suppressing it would be exactly the
metric theatre `AG-05` forbids.

---

## 7. Determinism contract

The decision engine is a pure function:

```
decide : (Opportunities, Context, StrategyVersion, PolicyPack,
          Capacities, VirtualClock, Seed, LLMCache) → Decision[]
```

| Requirement | Mechanism |
|---|---|
| No wall clock | `VirtualClock` injected; static check forbids direct time calls (`RR-NFR-004`) |
| No unseeded randomness | `stream(seed, label)` per component; labels `generator`, `oracle`, `exploration`, `approver` (`RR-NFR-005`) |
| Stable iteration | Explicit sort keys everywhere output-affecting (`RR-NFR-006`) |
| Stable tie-breaking | Frozen lexicographic key: `(−ENRV, −value_at_risk, opportunity_id, action_code)` |
| No hidden state | Predictor parameters read from an immutable `StrategyVersion` snapshot taken at cycle open |
| No oracle access | The predictor cannot reach the generator's response model (`AI-6`) |

### 7.1 Exploration and determinism

Exploration (Thompson sampling under a capped budget, `RR-FUNC-081`) is randomised *and* deterministic:
draws come from `stream(seed, "exploration")`, advanced in a fixed order. Exploration is therefore
reproducible at a seed and varies across seeds — which is what the multi-seed evaluation needs.

Exploration spend is a **separate, capped resource** in the ledger. It cannot borrow from the
exploitation budget, so an exploration bug cannot consume the merchant's recovery budget.

---

## 8. Failure behaviour of the engine

| Failure | Stage | Behaviour |
|---|---|---|
| Context assembly incomplete | 2 | Proceed with `context_degraded`, inflated `σ`; if a *required* key is missing, opportunity → `DEFERRED_PREDICTOR_DEGRADED` |
| LLM unavailable / cache miss in `PREPARE` | 3 | Deterministic-only diagnosis; cycle completes |
| LLM cache miss in `EVALUATE` | 3 | **Hard error.** Run aborts (`RR-NFR-035`) |
| Empty candidate set | 4 | Class-default set + `candidate_fallback` flag |
| Predictor parameters unloadable | 5 | **Whole cycle defers.** No actions at all (P-11) |
| Unseen predictor cell | 5 | Shrink to parent cell, inflate `σ` |
| Pricing assertion failure | 7 | Abort cycle rather than store a wrong price |
| Allocator timeout | 9 | Greedy fallback, `allocator_mode` recorded |
| Allocator infeasible | 9 | All `DEFERRED` with the binding constraint recorded |

Note the asymmetry: **every failure path reduces action.** There is no failure path in the decision
engine that increases the number or size of actions taken. That asymmetry is the operational meaning
of P-11.

---

## 9. Evaluation criteria for the engine itself

Distinct from the product-level evaluation in [21](21-evaluation.md). The engine is judged on:

| Criterion | Test |
|---|---|
| Purity | Repeated invocation on identical inputs → identical output (`RR-NFR-003`) |
| Set completeness | `|decisions| = |selected opportunities|`, every cycle (`AI-8`) |
| Price integrity | Component-sum reconstruction, zero residual |
| Threshold respect | No `SELECTED` decision has `ENRV ≤ ε` |
| Semantic separation | No `DEFERRED`/`NO_ACTION` reason-code crossover |
| Gate supremacy | No executed action lacks an `ALLOW` verdict |
| Explainability | Every decision explainable with all LLM text fields nulled (P-6) |
| Calibration | Brier score and ECE on the eval split (`M-24`) — reported per mode |
| Baseline dominance | `ENRV` achieved exceeds `B3 GREEDY_BY_AMOUNT` on the paired comparison (`SC-8`) |

---

## 10. Open items

| Item | Label |
|---|---|
| Value of `ε` | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION`. Must be a stated policy parameter, and sensitivity to it reported |
| Value of `λ_f` | `PROPOSED` default `1.0`. Sensitivity sweep required ([21 § 7](21-evaluation.md)) |
| Value of `m` (net-retention factor) | `ASSUMPTION` default `1.0`. Real value depends on merchant margin and refund behaviour |
| Horizon `H` per risk class | `PROPOSED`; must be fixed before any measurement, and identical across baselines |
| Whether `p(i,∅)` needs a separate model family from `p(i,a)` | `UNKNOWN`; [11 § 4](11-counterfactual-engine.md) records both options |
