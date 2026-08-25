# 35 · Learning Engine

The Learning Engine (C-21) is the only component that modifies the system's predictive behaviour
across cycles. It updates predictor parameters from observed outcomes, producing a new
`StrategyVersion`. It is structurally prohibited from modifying policy, budget, or guardrail
parameters.

> **Safety.** `RR-GUARD-022`: C-21 has no write access to policy, budget, threshold, or limit
> tables. This is enforced at the data-access layer, not by convention. Write attempts raise.

---

## 1. What it learns

| What | How | Where |
|---|---|---|
| Recovery probabilities per cell | Bayesian posterior update from observed outcomes | `StrategyVersion` table |
| Natural recovery baseline per cell | Same mechanism, restricted to outcomes where no action was taken | `StrategyVersion` table |
| Cell population parameters | Posterior hyperparameters (alpha, beta for Beta distribution) | `StrategyVersion` table |

### 1.1 What it does NOT learn

| What | Why not |
|---|---|
| Policy parameters (contact caps, budget limits, gate thresholds) | `RR-GUARD-022` — structural prohibition |
| The objective function or ENRV formula | Frozen ([README § C-5](README.md)) |
| New action types or candidate rules | Action catalogue is in the policy pack, not in strategy |
| Gate evaluation logic | Gates are deterministic code, not learned models |
| Stopping rules or their parameters | Stopping rules are policy, not strategy |

---

## 2. Cell model

### 2.1 Cell definition

A cell is defined by the tuple `(risk_class, cause_code, action_code, customer_segment)`.

| Dimension | Source | Cardinality |
|---|---|---|
| `risk_class` | `RevenueOpportunity.risk_class` | 4 |
| `cause_code` | `Diagnosis.candidate_causes[0].code` | ~20 (closed taxonomy) |
| `action_code` | `ActionCandidate.action_code` | ~15 (from catalogue) |
| `customer_segment` | `ContextObject.customer_segment` | ~5 |

Total possible cells: ~6,000. Most will be sparse.

### 2.2 Prior initialisation

Initial cell parameters come from the generator's behavioural model:

```
For each cell (r, c, a, s):
  alpha_0(r,c,a,s) = generator_p(r,c,a,s) × prior_weight
  beta_0(r,c,a,s)  = (1 − generator_p(r,c,a,s)) × prior_weight
```

`prior_weight` is a hyperparameter controlling the strength of the prior. `PROPOSED`:
`prior_weight = 10` (equivalent to 10 pseudo-observations).

### 2.3 Posterior update

After observing an outcome for opportunity `i` with action `a`:

```
If recovered:
  alpha(cell) += 1
If not recovered:
  beta(cell) += 1

p_hat(cell) = alpha / (alpha + beta)
sigma(cell) = sqrt(alpha · beta / ((alpha + beta)² · (alpha + beta + 1)))
```

This is a conjugate Beta-Bernoulli update, which is:
- Deterministic given the same sequence of observations
- Transparently auditable (parameters are stored)
- Automatically shrinks toward the prior for sparse cells

### 2.4 Hierarchical shrinkage

When a cell has fewer than `min_obs` observations, the estimate is shrunk toward its parent cell:

```
Parent hierarchy:
  (risk_class, cause_code, action_code, customer_segment)
    → (risk_class, cause_code, action_code, *)          # drop segment
      → (risk_class, *, action_code, *)                 # drop cause
        → (risk_class, *, *, *)                         # drop action
          → (*, *, *, *)                                # global prior
```

Shrinkage weight:
```
w = min(1, n_cell / min_obs)
p_shrunk = w · p_cell + (1 - w) · p_parent
sigma_inflated = sigma_cell / sqrt(w)
```

`min_obs` is a hyperparameter. `PROPOSED`: `min_obs = 20`.

---

## 3. Natural recovery baseline

The same cell model is used for `p(i,∅)` — the natural recovery probability. But:

| Property | p(i,a) | p(i,∅) |
|---|---|---|
| Updated from | Outcomes of actioned opportunities | Outcomes of non-actioned opportunities |
| Data source | Interventions with `COMPLETED_*` outcomes | Opportunities with `NO_ACTION_CYCLE` or `B0` baseline outcomes |
| Calibration metric | `M-24` for `p(i,a)` | `M-24` for `p(i,∅)` (separately) |

`CE-1` in [11-counterfactual-engine.md](11-counterfactual-engine.md): calibration for `p(i,∅)` is
reported separately because a well-calibrated action model with a badly-calibrated baseline model
produces confidently wrong uplifts.

---

## 4. Strategy versioning

### 4.1 Version semantics

Every update produces a new `StrategyVersion`:

```
StrategyVersion
├── strategy_version_id   strat_<ULID>
├── parent_version_id     strat_<ULID> of the previous version
├── created_at            virtual clock
├── cycle_id              the cycle that triggered the update
├── cell_updates[]        list of (cell_key, old_alpha, old_beta, new_alpha, new_beta)
├── observation_count     number of outcomes processed in this update
├── calibration_snapshot   M-24 values at this version
└── rollback_target       if this version was created by rollback: the version rolled back to
```

### 4.2 Version recording

Every `Decision` records the `strategy_version_id` that was active when the decision was made.
This allows:
- Post-hoc analysis of which strategy version produced which outcomes
- Comparison across versions
- Identification of the version that introduced a calibration regression

### 4.3 Rollback

If `M-24` degrades after an update (Brier score or ECE worsens by more than a configured
threshold), the Learning Engine rolls back to the parent version.

Rollback produces a new `StrategyVersion` with `rollback_target` set. The bad version remains in
the store for diagnosis but is no longer the active version.

---

## 5. Exploration budget

### 5.1 Purpose

Without deliberate exploration, the system will never observe outcomes for cells that the current
strategy rates poorly. This is the classic exploitation-exploration trade-off.

### 5.2 Mechanism

A fraction of the allocator's budget is reserved for exploration:

```
exploration_budget_fraction = 0.05  (PROPOSED)
exploration_pool = candidates with unseen or sparse cells (n < min_obs)
```

Exploration candidates are selected from the `exploration_pool` by highest uncertainty (`sigma`),
subject to all gates and stopping rules. Exploration does not bypass guardrails.

### 5.3 Constraints

| Constraint | Statement |
|---|---|
| Exploration never bypasses gates | `RR-GUARD-022` — exploration is a budget allocation, not a permission |
| Exploration spend is tracked | `M-29` reports exploration as a separate resource share |
| Exploration is bounded | `exploration_budget_fraction` is a hard cap per cycle |
| Exploration is auditable | Exploration candidates are marked `is_exploration = true` in the decision record |

---

## 6. Calibration monitoring

### 6.1 Metrics

| Metric | Definition | Reported |
|---|---|---|
| `M-24` Brier score | Mean squared error of predicted `p` vs binary outcome | Per action family, per cell level, per `p(i,a)` and `p(i,∅)` separately |
| `M-24` ECE | Expected calibration error across binned predictions | Same splits |
| `M-24` Reliability curve | Observed frequency vs predicted probability in bins | Published in evaluation artefact |

### 6.2 Calibration requirements

| Requirement | Statement |
|---|---|
| `CE-1` | `p(i,∅)` calibration reported separately from `p(i,a)` |
| `CE-2` | Brier score and ECE both reported — neither alone is sufficient |
| `CE-3` | Reliability curve published with bin counts — small-bin results are labelled |
| `CE-4` | Calibration regression triggers rollback |

---

## 7. Ablation

The learning engine's contribution is measured by ablation:

| Configuration | Description |
|---|---|
| **Learning ON** | Full system with posterior updates across cycles |
| **Learning OFF** | Strategy frozen at the initial priors; no posterior updates |

Both configurations run the full benchmark. The comparison is:
- `M-10` learning-on vs learning-off
- `M-24` calibration learning-on vs learning-off
- `M-23` wasted spend learning-on vs learning-off

If learning-off outperforms learning-on, the learning engine is harmful and this must be reported
prominently, not hidden.

---

## 8. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-FUNC-080` | Posterior updating (§ 2.3) |
| `RR-FUNC-081` | Calibration monitoring (§ 6) |
| `RR-FUNC-082` | Strategy version recording (§ 4) |
| `RR-FUNC-083` | Learning cannot write policy (§ 1.1, `RR-GUARD-022`) |
| `M-24` | § 6 |
| `RR-GUARD-022` | § 1, § 5.3 |

---

## 9. Open items

| Item | Label |
|---|---|
| `prior_weight` value | `PROPOSED` 10; sensitivity required |
| `min_obs` for shrinkage | `PROPOSED` 20; sensitivity required |
| `exploration_budget_fraction` | `PROPOSED` 0.05; sensitivity required |
| Calibration regression threshold for rollback | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION` |
| Whether to use Thompson sampling instead of fixed exploration fraction | `FUTURE` |
| Whether cell definition should include additional dimensions (e.g., ageing bucket) | `PROPOSED` no, for sparsity reasons |
