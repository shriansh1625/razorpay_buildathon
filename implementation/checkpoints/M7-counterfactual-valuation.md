# M7 Checkpoint — Counterfactual Recovery Valuation + ENRV

**Milestone:** M7 — Counterfactual Recovery Valuation (SIMULATE / VALUE)  
**Date:** 2026-08-23  
**Status:** COMPLETE

---

## Purpose

Given M4 opportunity, M5 context/diagnosis, and M6 candidate set, estimate **expected incremental economic value** for each feasible action relative to the no-action counterfactual. M7 does **not** rank, allocate, execute, or select actions.

---

## Economic model (canonical)

From `implementation/pre-m1-economic-model-audit.md` and docs/11 §5:

```
u(i,a)     = p(i,a) − p(i,∅)

gross(i,a) = u(i,a) · V(i) · m

ENRV(i,a)  = gross(i,a)
             − c(a)
             − p(i,a) · d(i,a)
             − λ_f · F(i,a)

ENRV(i,∅)  = 0   (CF-1)
```

| Term | Implementation |
|------|----------------|
| `V(i)` | `DetectedOpportunity.value_at_risk_paise` |
| `m` | `ValuationConfig.net_retention_factor` (default 1.0) |
| `c(a)` | `RecoveryCandidate.nominal_cost_paise` (0 for A00) |
| `d(i,a)` | Incentive tier from candidate `params` |
| `F(i,a)` | Observable fatigue units from contact history + channel |
| `λ_f` | `ValuationConfig.lambda_fatigue` (default 1.0) |

Integer paise for all money; banker's rounding once at persistence (`revive/recovery/valuation/money.py`).

---

## No-action semantics

- A00 always valued with **ENRV = 0 exactly** (all components zero).
- Natural recovery is embedded in `p(i,∅)` — incremental uplift measures action value **above** natural recovery.
- A00 does not mean “no natural recovery exists.”

---

## Action probability model

**Architecture:** Beta-Binomial per cell with hierarchical shrinkage (docs/11 §4, ADR-005).

| Quantity | Cell key |
|----------|----------|
| `p(i,∅)` | `(risk_class, cause_code, NATURAL, customer_segment)` |
| `p(i,a)` | `(risk_class, cause_code, action_code, customer_segment)` |

**Development priors (PROVISIONAL):** Observable features only — `prior_self_recovery_rate`, `success_rate`, ageing, degradation, window timing. Action deltas in `ValuationConfig.DEFAULT_ACTION_UPLIFT_DELTA`.

**Shrinkage:** Three-level with κ₁=5, κ₂=10; n=0 cells use parent/root with inflated σ.

**No oracle access.** No `revive.simulation.oracle` or `latent` imports.

---

## Cost model

| Cost | Source |
|------|--------|
| Direct `c(a)` | `DEFAULT_ACTION_COSTS_PAISE` via M6 `nominal_cost_paise` |
| Incentive `d(i,a)` | `ValuationConfig.incentive_tier_paise` from candidate `incentive_tier` |
| Fatigue `F(i,a)` | `contacts_last_7d/30d`, channel intrusiveness, value band |

---

## Fatigue model

```
F = contacts_7d × 0.5 + contacts_30d × 0.1 + channel_intrusiveness
    × (1.15 if V ≥ ₹1000)
fatigue_cost = bankers_round(λ_f × F)
```

Uses `ContextObject.fatigue` only — not oracle `fatigue_sensitivity`.

---

## Counterfactual mechanism

1. Estimate shared `p(i,∅)` once per opportunity.
2. For each M6 candidate, estimate `p(i,a)`.
3. Compute uplift, gross, costs, ENRV.
4. Return `ValuationResult` with independent `CandidateValuation` rows.

No winner selection. Candidates sorted by `action_code` for deterministic serialization only.

---

## Observable features

From `features.py` and docs/11 §4.4:

- Customer: segment, prior_self_recovery_rate, success_rate
- Opportunity: risk_class, value_at_risk, degradation_flag
- Diagnosis: top cause code
- Temporal: time_to_window_close
- Receivable: ageing_days
- Fatigue: contacts_last_7d/30d
- Action: code, channel, incentive_tier

---

## Leakage controls

| Control | Test |
|---------|------|
| Oracle import guard | `assert_decision_path_does_not_import_oracle()` |
| Hidden-state invariance | `test_valuation_integrity.py` |
| Future-outcome invariance | `test_future_leakage_invariance` |
| Prediction ≠ realized | No `realized_outcome` on `CandidateValuation` |
| No ranking | Source inspection on `price.py` |

---

## Model versioning

| Field | Value |
|-------|-------|
| `valuation_version` | `0.7.0-m7` |
| `strategy_version` | `strat_m7_dev` |
| `valuation_id` | `sha256(candidate_id:strategy_version)` |

Reproducible given same inputs, config, and strategy version.

---

## Uncertainty

- `σ` from Beta posterior spread on `p(a)` and `p(∅)`.
- `sigma_u = sqrt(σ_a² + σ_∅²)` (conservative independence).
- `enrv_lo` / `enrv_hi` from uplift interval + incentive cost bounds.
- Point ENRV does not add optimism from uncertainty.

---

## Package layout

```
revive/recovery/valuation/
├── config.py      # ValuationConfig, PROVISIONAL defaults
├── features.py    # Observable priors
├── cells.py       # Cell keys, shrinkage
├── predictor.py   # p(i,a), p(i,∅)
├── costs.py       # c, d, F
├── enrv.py        # ENRV component sum
├── money.py       # Banker's rounding
├── models.py      # CandidateValuation, ValuationResult
├── price.py       # price_candidates() entry
└── __init__.py
```

**Entry point:** `price_candidates(opportunity, context, diagnosis, candidate_set, now_micros)`

---

## Tests

| File | Coverage |
|------|----------|
| `test_valuation_enrv.py` | CF-1, CF-7, CF-8, integer money, multiple candidates |
| `test_valuation_integrity.py` | Oracle guard, invariance, determinism, no ranking |
| `test_valuation_edge_cases.py` | Negative ENRV, intervals, model version |

**Results:** 137 tests passing (15 new M7 tests).

---

## Provisional parameters

| Parameter | Value | Status |
|-----------|-------|--------|
| `prior_weight` | 10 | PROPOSED (docs/35) |
| `κ₁`, `κ₂` | 5, 10 | PROPOSED |
| Action uplift deltas | `DEFAULT_ACTION_UPLIFT_DELTA` | PROVISIONAL dev priors |
| Incentive tiers | TIER_0–3 paise | PROVISIONAL |
| `λ_f` | 1.0 | PROPOSED |
| `m` | 1.0 | ASSUMPTION |
| `ε` | 0 (provisional) | ADR-011 DRAFT |

---

## ADR dependencies

| ADR | Status | Impact |
|-----|--------|--------|
| ADR-005 | Beta-Binomial default | Implemented |
| ADR-006 | No deep models | Honored |
| ADR-011 | ε threshold | **DRAFT** — `epsilon_paise_provisional=0` centralized; benchmark freeze blocked |

---

## Known limitations

- Development priors only — no official benchmark calibration (M13).
- Cell store / posterior updates deferred to learning engine (M21+).
- Expanded cell dimensions (amount_band, ageing_bucket, history_band) partially used in priors but not full 6-tuple cells yet.
- Interval propagation documented; not full closed-form in spec.

---

## Deviations

None from canonical ENRV formula. B3 `revive/benchmark/pricing.py` remains separate baseline heuristic.

---

## Deferred decisions

- Official strategy version sealing
- Thompson sampling exploration budget
- Full 6-dimension cell cross-product
- ADR-011 ε resolution

---

## Next milestone

**M8/M9 — Portfolio allocation** (WHERE should limited recovery effort go?)

M7 ends when REVIVE can say: *“For every feasible recovery action, this is the defensible expected incremental value.”*

---

## Acceptance criteria

```
[x] Candidate valuation engine exists
[x] Documented action-probability model implemented
[x] No-action reference implemented correctly
[x] Expected recovery / incremental uplift implemented
[x] Intervention costs incorporated
[x] Fatigue cost incorporated
[x] ENRV implemented exactly as documented
[x] Integer-money arithmetic preserved
[x] Uncertainty represented
[x] Model provenance recorded
[x] Candidate valuations generated independently
[x] No action ranking
[x] No portfolio allocation
[x] No execution
[x] No benchmark headline
[x] No oracle access
[x] No latent-feature access
[x] No future lookahead
[x] Prediction separated from realized outcome
[x] LLM not required
[x] Tests pass
[x] M7 checkpoint exists
```
