# 10 · Recovery Allocation Under Constraints

> This is REVIVE's primary differentiator. Every other document supports it.

---

## 1. Why allocation, and not a rules engine

A per-event recovery system asks: *"payment `X` failed — what should I do about `X`?"*

That question is answerable in isolation only if the answer costs nothing. It does not. Retrying
consumes a retry slot and a share of the merchant's issuer goodwill. Messaging consumes channel
capacity and, more importantly, a customer's finite tolerance. Discounting consumes margin. Human
review consumes a reviewer-hour. Every one of these is **shared across the whole book of at-risk
revenue**.

The moment a resource is shared, the correct question changes:

> *"Given everything at risk right now, where does the next unit of recovery effort produce the most
> incremental net revenue?"*

This is not a stylistic difference. It changes the answer. Concretely:

| Situation | Per-event answer | Allocation answer |
|---|---|---|
| Two failures, one retry slot | Retry the first one seen | Retry the one with higher `uplift × value`, defer the other and record why |
| Large invoice, likely to self-pay | Chase it (it's big) | Leave it — `uplift ≈ 0`, so `ENRV ≈ −cost`; spend the effort on a smaller invoice with real uplift |
| Incentive budget nearly exhausted | Keep offering until it's gone | Raise the effective bar: only actions clearing the *shadow price* of the budget get it |
| Customer with 3 recent contacts and a new failure | Send the reminder (it's a new event) | Contact allowance is a per-customer resource; the new failure competes against nothing left to spend |
| 500 opportunities, 50 message slots | First 50 by recency or size | The 50 with highest `ENRV`, with the marginal value of slot 51 reported to the merchant |

The right-hand column is the product.

---

## 2. Formal problem

### 2.1 Statement

Let `I` be the opportunities in the cycle, `A_i` the feasible actions for `i` (including `∅`), and
`R` the resource set. Decision variables `x_{i,a} ∈ {0,1}`.

```
maximise     Σ_{i∈I} Σ_{a∈A_i}  ENRV(i,a) · x_{i,a}

subject to   Σ_{a∈A_i} x_{i,a} = 1                        ∀ i ∈ I      (exactly one action per opportunity)
             Σ_{i} Σ_{a} usage_r(i,a) · x_{i,a} ≤ B[r]    ∀ r ∈ R      (capacity)
             x_{i,a} = 0  where gates(i,a) ≠ ALLOWABLE                 (feasibility)
             x_{i,a} = 0  where ENRV(i,a) ≤ ε  and  a ≠ ∅              (threshold)
             x_{i,a} ∈ {0,1}
```

This is a **multi-dimensional knapsack with multiple-choice structure** (MMKP). It is NP-hard in
general, which is why § 5 uses Lagrangian relaxation with a greedy primal recovery rather than exact
solution as the default — and why `RR-FUNC-038` mandates a time budget and a fallback.

### 2.2 The `NO_ACTION` column

`ENRV(i,∅) = 0` and `usage_r(i,∅) = 0 ∀ r`. Therefore:

- The problem is **always feasible** — assigning `∅` to everything is a valid solution with objective 0.
- The optimum is **never negative**.
- Any resource left unspent is a positive statement ("nothing else cleared the bar"), not a failure.

This single column is what makes "do nothing" first-class rather than a special case bolted on.

### 2.3 Multi-period myopia, stated

The formulation optimises **one cycle at a time**. It is myopic: spending a retry slot now may be
worse than saving it for a better opportunity two cycles later.

This is a deliberate, disclosed simplification (`ADR-004`). Partial mitigations:

| Mitigation | Mechanism |
|---|---|
| Period-level budgets, not just cycle-level | `B_cycle[r] ≤ B_period[r] − committed_period[r]`, so a cycle cannot exhaust the period |
| Cycle-level pacing caps | An optional per-cycle fraction cap on each resource, preventing early-cycle greed |
| Recovery-window awareness | `V(i)` and `p(i,∅)` already encode urgency; a closing window raises the cost of waiting |
| Reported, not hidden | The evaluation includes a myopia diagnostic: total resource spent early vs late in the period |

Full multi-period stochastic optimisation is `FUTURE / NOT IMPLEMENTED`
([41-future-ideas.md](41-future-ideas.md)).

---

## 3. The resource model

Six resource families (`RR-FUNC-031`). Each is declared with a scope, a period limit, an optional
cycle cap, and a usage function.

| Resource | Scope | Unit | Consumed by | Notes |
|---|---|---|---|---|
| `incentive_budget` | Merchant | paise | Any action with `incentive_tier > 0` | Reserved at `d(i,a)` (worst case, unconditional), committed at actual on success, released on failure |
| `message_capacity_<channel>` | Merchant × channel | messages | Messaging actions on that channel | Separate per channel; channels are not fungible |
| `voice_minutes` | Merchant | minutes | Voice actions | Reserved at expected duration; T3 resource |
| `retry_slots` | Merchant (and optionally × method) | attempts | Payment retry actions | Models both cost and issuer-goodwill scarcity |
| `human_review_slots` | Merchant | slots | `REQUIRE_APPROVAL` and human-task actions | The scarcest resource in practice |
| `contact_allowance_<customer>` | **Per customer** | contacts | Any customer-facing action | The only per-entity resource; the structural expression of PP-3 |

### 3.1 Why `contact_allowance` is a resource and not only a gate

`RR-GUARD-003` caps contacts as a hard gate — that is the compliance floor. But a cap alone produces
first-come-first-served behaviour within the cap: the first opportunity touching a customer spends
their allowance regardless of whether a better one arrives in the same cycle.

Modelling it as an allocated resource means that when one customer has two at-risk items in a cycle,
the allowance goes to the higher-`ENRV` one and the other is `DEFERRED` with
`DEFERRED_CHANNEL_CAPACITY` — visibly, with a shadow price. Gate and resource are complementary: the
gate says *never more than k*, the resource says *and within k, spend it well*.

### 3.2 Reservation semantics

Two-phase, owned solely by the Resource Ledger (C-16):

```
RESERVE(handle, r, qty)   →   granted | refused        (before gate ALLOW is final)
COMMIT(handle)            →   moves reserved → committed  (after adapter returns)
RELEASE(handle)           →   frees reserved             (on deny, abort, crash-recovery, or failure)
```

Invariant, asserted continuously (`RR-NFR-041`):

```
committed[r] + reserved[r]  ≤  min( B_period[r] − committed_prior_periods, B_cycle[r] )
```

Reservations carry a cycle id and are reclaimed at the next cycle open if orphaned by a crash, so a
crashed executor cannot permanently strand budget.

### 3.3 Conservative reservation for conditional costs

`d(i,a)` (the incentive) is charged **only on success**, but reserved **unconditionally**. This
deliberately over-reserves: the ledger can never over-commit, at the cost of occasionally under-using
the budget within a cycle. The alternative — reserving `p(i,a)·d(i,a)` — is cheaper on paper and
allows the realised spend to exceed the budget when several incentives land. For money, the
conservative direction is the correct one (`ADR-008`).

Under-utilisation caused by conservative reservation is reported as a diagnostic, not hidden.

---

## 4. Shadow prices, and why the merchant cares

For each resource `r`, the allocator produces `λ_r` — the estimated marginal `ENRV` gain per
additional unit of `r` at the current allocation.

| `λ_r` | Interpretation |
|---|---|
| `0` | `r` is not binding. More of it changes nothing. |
| `> 0` | `r` is binding. One more unit is worth about `λ_r` paise of incremental net revenue. |

This turns an internal solver artefact into the most actionable output REVIVE has:

> "Your reviewer capacity is the binding constraint this week. One additional review slot is worth
> approximately `λ` paise of incremental net recovery, and we deferred `n` opportunities worth `V`
> because of it."

That sentence is a business recommendation derived from the optimisation, not from an LLM, and it is
falsifiable — the report states the deferred set so the merchant can check it.

### 4.1 How `λ` is obtained

From the Lagrangian multipliers at convergence (§ 5). Where the greedy fallback runs, `λ_r` is
estimated as the `ENRV`-per-unit of the highest-value *rejected* candidate that would have consumed
`r` — a lower bound, and labelled as an estimate with `shadow_price_method = GREEDY_ESTIMATE`.

### 4.2 Honesty requirement

Shadow prices from a heuristic are **estimates**. `RR-UI-006` requires the UI and report to label the
method, and `PP-4` forbids presenting them as exact marginal values. Where the ILP cross-check runs
(§ 6.2), the exact duals are reported alongside the heuristic estimate and the gap is shown.

---

## 5. The allocation algorithm

Three modes. The active mode is recorded on every decision (`allocator_mode`).

### 5.1 Mode `LAGRANGIAN` (default)

Relax the capacity constraints into the objective with multipliers `λ`:

```
L(λ) = max_x  Σ_i Σ_a [ ENRV(i,a) − Σ_r λ_r · usage_r(i,a) ] · x_{i,a}
              + Σ_r λ_r · B[r]
```

For fixed `λ`, the inner problem **decomposes per opportunity**: each `i` independently picks the
action maximising its *reduced* value

```
rv(i,a) = ENRV(i,a) − Σ_r λ_r · usage_r(i,a)
```

taking `∅` if no action has `rv > 0`. That decomposition is what makes this tractable at batch scale
and is the reason this method is preferred over a monolithic solver.

```
ALLOCATE(candidates, capacities, ε, time_budget):

  1  λ ← λ_init                                  # warm-started from the previous cycle
  2  for k in 1 .. K_max:                        # subgradient ascent, K_max fixed
  3      for each opportunity i (in ULID order):
  4          a*(i) ← argmax over a ∈ A_i of rv(i,a)      # ties → frozen key (§7)
  5          if rv(i, a*(i)) ≤ 0 : a*(i) ← ∅
  6      usage[r] ← Σ_i usage_r(i, a*(i))
  7      g[r]     ← usage[r] − B[r]              # subgradient
  8      if g[r] ≤ 0 ∀ r and duality_gap ≤ tol : break
  9      λ[r] ← max(0, λ[r] + step(k) · g[r])    # step(k) deterministic, non-adaptive to wall time
 10      if elapsed > time_budget : goto FALLBACK
 11
 12  # Primal recovery: the relaxed solution may still violate capacity.
 13  x ← {}
 14  for each (i, a*(i)) sorted by rv desc, then frozen tie key:
 15      if RESERVE_all(usage(i,a*(i))) succeeds:
 16          x[i] ← a*(i)
 17      else:
 18          a' ← best feasible alternative in A_i with rv > 0 and ENRV > ε
 19          x[i] ← a'  if reservable  else  DEFERRED(binding resource)
 20
 21  emit λ as shadow prices, method = LAGRANGIAN_DUAL
 22  emit duality gap as allocation_optimality_gap
 23  return x
```

Notes on specific lines:

- **Line 1 (warm start).** `λ` from the previous cycle is a good starting point and reduces
  iterations. It is part of cycle state, so it is snapshotted and versioned — warm starting must not
  make the run depend on history in an unrecorded way (`RR-NFR-091`).
- **Line 9 (step rule).** Deterministic in `k` only. It must not depend on elapsed time, or two runs
  on differently-loaded machines would diverge and break `RR-NFR-020`.
- **Line 10 (time budget).** Checked against the *virtual* iteration count in benchmark mode and wall
  time in interactive mode. In benchmark mode the iteration cap alone decides, so timing jitter
  cannot change the result.
- **Line 19.** Deferral records *which* resource refused the reservation. That record is what
  populates the binding-constraint report.

### 5.2 Mode `FALLBACK_GREEDY`

Reached on time-budget expiry (`RR-FUNC-038`) or on a Lagrangian failure. Guarantees feasibility, not
optimality.

```
FALLBACK(candidates, capacities, ε):
  1  pool ← all candidates with ENRV > ε and a ≠ ∅
  2  sort pool by  ENRV / normalised_resource_cost   desc,
                   then by frozen tie key
  3  for each candidate in pool:
  4      skip if its opportunity is already assigned
  5      if RESERVE_all succeeds : assign
  6      else : record the refusing resource
  7  unassigned opportunities → NO_ACTION (if no candidate cleared ε)
                              → DEFERRED  (if a candidate cleared ε but no capacity)
  8  emit shadow prices, method = GREEDY_ESTIMATE
```

`ENRV / normalised_resource_cost` (density) rather than raw `ENRV` — raw-`ENRV` greedy is precisely
baseline `B3`, and the allocator must not silently degrade into its own baseline. If the fallback
fires, the report says so, per cycle, with a count.

### 5.3 Mode `EXACT`

An ILP solve, used in three situations only:

1. Small batches during development and in unit tests, to measure the optimality gap
2. The offline cross-check described in § 6.2
3. Benchmark configurations small enough to solve exactly within the time budget, so the reported gap
   is a measurement rather than an assumption

`EXACT` is not the default because it does not degrade gracefully at batch scale and because a
solver's internal nondeterminism threatens `RR-NFR-020` unless carefully pinned.

---

## 6. Correctness of the allocator

### 6.1 Invariants (asserted, not hoped for)

| # | Invariant |
|---|---|
| AL-1 | Every opportunity entering the cycle receives exactly one decision |
| AL-2 | No resource is over-allocated at any instant: `committed + reserved ≤ limit` |
| AL-3 | No `SELECTED` action has `ENRV ≤ ε` |
| AL-4 | No `SELECTED` action lacks a subsequent gate `ALLOW` before execution |
| AL-5 | Objective is monotone non-decreasing in capacity: relaxing any `B[r]` never lowers achieved `ENRV` |
| AL-6 | `λ_r = 0` whenever `r` is not binding |
| AL-7 | Identical inputs + seed → identical decisions, byte for byte |
| AL-8 | `NO_ACTION` for all is always a reachable solution; achieved objective ≥ 0 |
| AL-9 | Every `DEFERRED` decision names the resource that refused it |
| AL-10 | Total reserved at cycle end = 0 (everything committed or released) |

### 6.2 The ILP cross-check

For a set of pinned small fixtures and a sampled subset of benchmark cycles, the same input is solved
exactly and compared:

```
optimality_gap = (ENRV_exact − ENRV_heuristic) / ENRV_exact
```

The gap is **reported in the evaluation, not asserted to be small**. If the heuristic is far from
optimal, that is a finding about the allocator, and hiding it would violate P-7. `RR-BENCH-*`
requires the gap distribution to appear in the report.

### 6.3 Adversarial test cases

| Case | Expected behaviour |
|---|---|
| All candidates negative `ENRV` | All `NO_ACTION`; zero resources consumed |
| One enormous opportunity, tiny budget | It gets the budget; everything else `DEFERRED` with a high `λ` |
| Many identical opportunities | Deterministic tie-break; capacity spent to exhaustion; remainder `DEFERRED` |
| Zero capacity on every resource | All `DEFERRED`; `λ` reflects the value of the whole blocked pool |
| Capacity larger than demand | All positive-`ENRV` actions selected; all `λ_r = 0` |
| One customer, ten opportunities, contact allowance 1 | Exactly one contact; nine `DEFERRED`; per-customer resource honoured |
| Candidate consuming two scarce resources | Correctly charged against both; not double-counted within one |
| Gate denies the allocator's top pick | No action executes; reservation released; decision `REJECTED`, and the runner-up is **not** silently promoted within the same cycle (`RR-GUARD-023`) |

The last row deserves emphasis: a denied top pick does **not** trigger re-allocation inside the cycle.
Re-optimising around a gate verdict is how systems learn to route around their own guardrails. The
opportunity is reconsidered in the next cycle, from scratch.

---

## 7. Determinism and tie-breaking

Frozen ordering key, used at every point where candidates or opportunities are compared:

```
sort_key(i, a) = ( −reduced_value(i,a),      # or −ENRV in greedy mode
                   −value_at_risk(i),
                   opportunity_id,           # ULID, unique
                   action_code )             # enum ordinal
```

Because `opportunity_id` is unique, the key is a total order — there are no genuine ties, so no
implementation-defined behaviour can leak in. All floating-point comparisons on `ENRV` operate on
integer paise, removing float-comparison instability from the ordering path entirely.

---

## 8. Illustrative arithmetic

> ⚠️ **ILLUSTRATIVE ONLY — NOT A RESULT, NOT A MEASUREMENT, NOT A CLAIM.**
> The numbers below are invented by hand to demonstrate the mechanism of the objective function and
> the effect of a binding constraint. They are not produced by any implementation, they are not drawn
> from any dataset, and they must never be cited as evidence of performance. Every real figure in this
> project comes from a benchmark artefact ([20](20-benchmark.md)) and none exists yet.

Three opportunities, one message slot, no incentive budget. All amounts in paise.

| | `V(i)` | Action `a` | `p(i,a)` | `p(i,∅)` | `u` | `gross = u·V` | `c(a)` | `λ_f·F` | `ENRV` |
|---|---|---|---|---|---|---|---|---|---|
| **O1** | 500 000 | `SEND_REMINDER` | 0.40 | 0.35 | 0.05 | 25 000 | 200 | 400 | **24 400** |
| **O2** | 120 000 | `SEND_REMINDER` | 0.55 | 0.15 | 0.40 | 48 000 | 200 | 400 | **47 400** |
| **O3** | 900 000 | `SEND_REMINDER` | 0.92 | 0.90 | 0.02 | 18 000 | 200 | 1 200 | **16 600** |

Reading the table:

- **Ranking by value at risk** picks **O3** (900 000) — the largest number on the page, and the worst
  choice, because that customer was going to pay anyway (`p(i,∅) = 0.90`) and has high fatigue cost.
- **Ranking by conversion probability** also picks **O3** (`p = 0.92`) — the same mistake for a
  different reason.
- **Ranking by `ENRV`** picks **O2**, whose value at risk is the smallest of the three but whose
  *uplift* is eight times O1's and twenty times O3's.

O1 and O3 are then `DEFERRED_CHANNEL_CAPACITY`, and `λ_message ≈ 24 400` paise per slot — the
`ENRV` of the best action the missing slot would have bought. The merchant-facing statement is: *"one
more message slot this cycle was worth about `λ` to you, and here are the two items it would have
gone to."*

This is the entire product in one table: **not the biggest number, not the likeliest conversion — the
largest incremental net gain per unit of scarce resource, with the cost of scarcity made explicit.**

---

## 9. What the allocator is not

| Not | Because |
|---|---|
| A priority queue with weights | Weights do not respond to capacity; shadow prices do |
| A rules engine with a sort | A sort cannot express "these two candidates compete for two different resources" |
| An LLM ranking prompt | Nondeterministic, unauditable, cannot produce shadow prices, and violates `RR-GUARD-020` |
| A guarantee of optimality | It is a heuristic with a measured gap (§ 6.2) |
| A multi-period planner | Explicitly myopic per § 2.3, disclosed as `ADR-004` |
| A permission system | It proposes; C-13 authorises. Selection is not authorisation |

---

## 10. Requirement mapping

| Requirement | Where satisfied |
|---|---|
| `RR-FUNC-030` batch-level optimisation | § 2, § 5 |
| `RR-FUNC-031` resource model | § 3 |
| `RR-FUNC-032` contention resolution | § 5.1 lines 12–19 |
| `RR-FUNC-033` shadow prices | § 4 |
| `RR-FUNC-034` `ε` threshold respected | AL-3 |
| `RR-FUNC-035` decision for every opportunity | AL-1 |
| `RR-FUNC-036` deterministic tie-breaking | § 7 |
| `RR-FUNC-037` gates run after allocation | § 6.3 last row, `RR-GUARD-023` |
| `RR-FUNC-038` time budget + fallback | § 5.2 |
| `RR-FUNC-039` binding constraint recorded | AL-9 |
| `RR-NFR-031` ≤ 3 s allocator budget | § 5.1 line 10 |
| `RR-NFR-041` no over-allocation | § 3.2, AL-2 |

---

## 11. Open items

| Item | Label |
|---|---|
| `K_max` and the subgradient step rule | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION`; must be deterministic in `k` |
| Whether `retry_slots` is scoped per merchant or per merchant × method | `UNKNOWN`; depends on unverified issuer/gateway behaviour ([36](36-razorpay-integration-assumptions.md)) |
| Cycle-level pacing fractions | `PROPOSED`; needs a sensitivity sweep against the myopia diagnostic |
| ILP solver choice and determinism pinning | `UNKNOWN`; `EXACT` mode is optional and must not gate `SC-8` |
| Whether shadow prices should be smoothed across cycles for UI stability | `PROPOSED`; smoothing must not feed back into allocation |
