# 35b · Additional Decision Specifications

> **Note.** This document fills decision-level gaps not sufficiently captured in
> [09-decision-engine.md](09-decision-engine.md), [10-recovery-allocation.md](10-recovery-allocation.md),
> [11-counterfactual-engine.md](11-counterfactual-engine.md),
> [13-policy-and-guardrails.md](13-policy-and-guardrails.md), or
> [14-stopping-rules.md](14-stopping-rules.md). It does **not** duplicate content from those
> documents. It defines cross-module decision semantics and resolves ambiguity at module
> boundaries.
>
> **Naming.** The number `35` is occupied by [35-learning-engine.md](35-learning-engine.md).
> This document uses `35b` to avoid a filename collision. This naming decision is recorded in
> [36-documentation-consistency-check.md](36-documentation-consistency-check.md).

---

## 1. Opportunity prioritisation — the full ranking

The allocator (C-12) selects from priced candidates. But before a candidate reaches the allocator,
several stages have already reduced the set. The full priority funnel is:

```
All opportunities
  └─ Addressable? (C-02)           → NO: NOT_ADDRESSABLE; excluded
  └─ Diagnosed? (C-05)             → NO: deferred to next cycle
  └─ Candidates generated? (C-06)  → NO: deferred (candidate_fallback may apply)
  └─ Pre-filtered? (C-11)          → removed candidates with known gate violations
  └─ Priced (C-07, C-08, C-09)     → ENRV computed for each surviving candidate
  └─ ENRV > ε? (C-12)              → NO: NO_ACTION
  └─ Allocator selects (C-12)      → under resource constraints
  └─ Post-gate (C-13)              → ALLOW / DENY / DEFER / REQUIRE_APPROVAL
```

Each stage is documented in the component-level specification. This section clarifies the
**interactions** between stages.

---

## 2. Tie-breaking

`RR-FUNC-034` specifies deterministic tie-breaking by `(−ENRV, −value_at_risk_paise, opportunity_id)`.

### 2.1 When ties occur

Ties in ENRV are rare for non-identical opportunities. They occur when:
- Two `NO_ACTION` candidates (both ENRV = 0)
- Two candidates with identical cost structures and identical predictions (possible in synthetic data)
- Rounding to integer paise produces identical ENRV

### 2.2 Tie-breaking across the pipeline

| Stage | Tie-breaking rule |
|---|---|
| Candidate ranking within an opportunity | By `(−ENRV, action_code)` — lexicographic on action code |
| Allocation ranking across opportunities | By `(−ENRV, −value_at_risk_paise, opportunity_id)` |
| Gate evaluation order | Fixed G1…G12 order; no tie-breaking needed |
| Execution order within a cycle | By `opportunity_id` (ULID sort = creation order) |

### 2.3 Determinism guarantee

The tie-breaking rule plus seeded ULID generation guarantees identical rankings across runs at
the same seed. No sort depends on insertion order, memory address, or hash values.

---

## 3. Uncertainty handling

### 3.1 Sources of uncertainty

| Source | Component | Measure |
|---|---|---|
| Prediction uncertainty | C-07 | `sigma` (posterior spread) |
| Diagnosis uncertainty | C-05 | Confidence band (LOW/MED/HIGH) |
| Context degradation | C-04 | `context_degraded` flag |
| Unseen feature combination | C-07 | `unseen_cell` flag; inflated `sigma` |

### 3.2 How uncertainty flows through the pipeline

```
C-04: context_degraded → inflates sigma in C-07
C-05: confidence band → mapped to numeric prior weight in C-07
C-07: sigma → ENRV interval in C-09 → G7 approval threshold check in C-13
```

### 3.3 Decision rules under uncertainty

| Condition | Decision |
|---|---|
| Wide `sigma` on a material amount | G7 triggers `REQUIRE_APPROVAL` |
| `context_degraded` on a high-value opportunity | G7 threshold lowered; more likely to require approval |
| `unseen_cell` | Shrink to parent cell prior; inflate `sigma`; proceed with wider interval |
| All candidates have wide intervals | If the best candidate still clears `ε` by a margin exceeding the interval, proceed. Otherwise, `REQUIRE_APPROVAL` for material amounts or `NO_ACTION` for small amounts |

---

## 4. Action feasibility

Before pricing, the Candidate Generator (C-06) applies feasibility rules:

| Rule | When an action is infeasible |
|---|---|
| **Channel unavailable** | Customer has no identifier for the required channel |
| **Instrument invalid** | Retry requires a valid instrument; instrument is expired/blocked |
| **Consent absent** | Communication requires consent; none on record |
| **Action class mismatch** | Action is not applicable to the risk class (e.g., `MANDATE_RETRY` for `RECEIVABLE_OVERDUE`) |
| **No template** | Communication action has no template for the customer's language |

Infeasible actions are never generated as candidates. They do not consume allocation capacity.
The pre-filter (C-11) catches borderline cases that pass feasibility but fail policy.

---

## 5. Expected-value thresholds

### 5.1 The ε threshold

`ε` is the merchant's minimum-justification threshold in paise. An action with `ENRV ≤ ε` is
not worth taking. `ε ≥ 0` is a policy parameter in the policy pack.

| Property | Statement |
|---|---|
| Default | `PROPOSED` `ε = 0` paise (any positive ENRV justifies action) |
| Sensitivity | Reported: value stopped on economic grounds (`SR-07`) vs value recovered |
| Setting | Merchant-configurable in the policy pack; higher ε = more conservative |
| Zero case | `ε = 0`: every positive-ENRV action is eligible; only the allocation constraints prevent over-action |

### 5.2 Confidence thresholds for approval

G7 triggers `REQUIRE_APPROVAL` when uncertainty exceeds a threshold relative to value:

| Parameter | Description | Label |
|---|---|---|
| `approval_value_threshold` | `V(i)` above which all actions require approval | `UNKNOWN — MUST BE DECIDED` |
| `approval_uncertainty_threshold` | ENRV interval width / ENRV ratio above which approval is required | `UNKNOWN — MUST BE DECIDED` |
| `approval_action_families` | Action families that always require approval | `PROPOSED`: `A10` (incentive), `A11` (voice), `A12` (collections), `A14` (escalation) |

---

## 6. No-action logic

`NO_ACTION` is a decision, not an absence. It is chosen when:

| Condition | Reason code |
|---|---|
| No candidate has `ENRV > ε` | `NO_ACTION_ECONOMIC` |
| All candidates pre-filtered by C-11 | `NO_ACTION_POLICY` |
| Allocator did not select (contention) and chose no-action over deferral | `NO_ACTION_ALLOCATION` |
| Customer is in a communication window but no non-contact action is feasible | `NO_ACTION_TIMING` |
| The opportunity is addressable but the predicted uplift is zero or negative for all actions | `NO_ACTION_NO_UPLIFT` |

Every `NO_ACTION` carries a reason code from this closed set. `M-15` reports the distribution.
`N` consecutive `NO_ACTION_ECONOMIC` cycles triggers `SR-07`.

---

## 7. Human-approval logic

### 7.1 When approval is required

Defined in [13 § 3.1 G7](13-policy-and-guardrails.md). This section clarifies the **sequencing**:

```
1. Allocator selects candidate
2. Policy engine evaluates gates G1…G12
3. G7 returns REQUIRE_APPROVAL
4. Reservation is released (not held during approval)
5. Action queued in C-15
6. Human approves / rejects / modifies
7. If approved: re-enter all gates in a LATER cycle
8. If modified: re-price, then re-enter all gates
9. If rejected or expired: opportunity deferred
```

### 7.2 Key property

A human cannot approve a policy violation. Even if the human approves, the action re-enters all
gates, and a gate can deny. This is why modification re-gating exists (`RR-FUNC-066`).

---

## 8. Budget allocation across cycles

### 8.1 Two-level budgets

| Level | Scope | Refill |
|---|---|---|
| **Period budget** | Per resource, per period (e.g., daily SMS limit) | At period boundary |
| **Cycle budget** | Optional per-cycle cap on period budget (pacing) | Each cycle |

### 8.2 Pacing

If a period budget is 1000 SMS and there are 96 cycles per day (15-min intervals), a naive
approach could exhaust the entire budget in the first cycle. Pacing allocates a fraction per cycle:

`cycle_cap = period_remaining / cycles_remaining_in_period × pacing_factor`

`pacing_factor` is a policy parameter. `1.0` = even pacing. `> 1.0` = front-loaded. `< 1.0` = conservative.

`PROPOSED`: `pacing_factor = 1.0` with sensitivity reporting.

---

## 9. Retry ordering

When an opportunity re-enters decisioning after a failed action:

| Rule | Statement |
|---|---|
| Failed action code is not excluded | It may be regenerated as a candidate if it is still feasible |
| But attempt cap is checked | `SR-03` and `G4` may deny it |
| Alternative actions are generated | Candidate Generator considers the updated context (failure + new fatigue state) |
| ENRV is recomputed | The failed attempt's cost is sunk; the new ENRV is computed fresh |
| Priority is not boosted or penalised | The opportunity competes on its current ENRV like any other |

---

## 10. Delayed recovery windows

Some risk classes have longer recovery windows than others:

| Risk class | Window | Label |
|---|---|---|
| `CHECKOUT_ABANDONMENT` | Short (hours to days) | `PROPOSED` |
| `PAYMENT_FAILURE` | Medium (days to weeks) | `PROPOSED` |
| `SUBSCRIPTION_FAILURE` | Medium (days to weeks) | `PROPOSED` |
| `RECEIVABLE_OVERDUE` | Long (weeks to months) | `PROPOSED` |

Exact values are `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION` and must be frozen before
measurement.

The window affects ENRV through the horizon: `H = min(H_class, window_close − now)`. A closing
window raises urgency by increasing `p(i,∅)` (more time for natural recovery to occur) and
decreasing the time available for an action to take effect.

---

## 11. Customer fatigue

### 11.1 Fatigue model

Fatigue cost `F(i,a)` is the modelled future-value destruction caused by contacting a customer.
It is a function of:

- Contact history (how many times contacted in the rolling window)
- Customer value band (high-value customers have higher fatigue cost)
- Channel (voice has higher fatigue cost than SMS)
- Time since last contact (rapid re-contact has higher cost)

### 11.2 Fatigue aversion weight

`λ_f` is the merchant-configurable fatigue aversion weight in the ENRV formula.

| Value | Effect |
|---|---|
| `λ_f = 0` | Fatigue ignored; system contacts freely up to caps |
| `λ_f = 1.0` | Default; fatigue cost counts at face value |
| `λ_f > 1.0` | Conservative; system avoids contact more aggressively |

`PROPOSED`: `λ_f = 1.0` default with sensitivity reporting.

---

## 12. Escalation selection

When `ESCALATE_HUMAN` is a candidate action:

| Rule | Statement |
|---|---|
| Escalation is priced | It has a cost (human time), an estimated recovery probability, and an ENRV |
| Escalation competes | It is selected only if its ENRV exceeds alternatives |
| Escalation requires approval | G7 always triggers for `ESCALATE_HUMAN` (action family flagged sensitive) |
| Escalation is bounded | Attempt cap and contact cap apply to escalation actions |
| Escalation is not a catch-all | It is an action of last resort, not a default when the system is uncertain |

---

## 13. Conflicting evidence

When diagnosis produces conflicting signals (e.g., `DO_NOT_HONOUR` on a customer with good
instrument history during a degradation window):

| Rule | Statement |
|---|---|
| LLM may be consulted | C-05 ranks the conflicting causes by plausibility (`RR-FUNC-016`) |
| Confidence band reflects conflict | Conflicting evidence → lower confidence band |
| Both causes are reported | The diagnosis retains multiple ranked causes |
| Pricing uses the top-ranked cause | But the lower confidence inflates `sigma` |
| The conflict is recorded | Audit event includes both signals and the ranking |

---

## 14. Stale predictions

A prediction becomes stale when the state it was computed from has changed:

| Change | Effect |
|---|---|
| `V(i)` changed (partial recovery) | ENRV must be recomputed at the new `V(i)` |
| Contact history changed | Fatigue cost `F(i,a)` must be recomputed |
| Consent revoked | Candidates requiring that consent are removed |
| Instrument state changed | Candidates requiring that instrument are removed |

Stale-prediction detection is part of stale-decision detection (`RR-FUNC-043`). A stale
decision is invalidated and the opportunity re-enters the pipeline.

---

## 15. Open items

| Item | Label |
|---|---|
| Exact `ε` value | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION`; sensitivity required |
| G7 threshold values | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION` |
| Recovery window lengths per class | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION`; frozen before measurement |
| Pacing factor default | `PROPOSED` 1.0; sensitivity required |
| Customer fatigue model parameters | `PROPOSED`; calibration is `UNVERIFIED` |
| Whether `NO_ACTION_ALLOCATION` should be a distinct reason from `DEFERRED` | `PROPOSED` distinct, for clarity |
