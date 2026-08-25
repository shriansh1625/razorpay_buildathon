# M7 Analysis — Valuation

## Call volume

~5.55M `estimate_action_probability` + `compute_enrv` per cell.

## Natural probability

`price_candidates` already computes `p(i,∅)` **once per opportunity** and reuses it for every action. Confirmed.

`estimate_natural_probability` previously called `observable_natural_prior` twice with identical arguments — now once.

## Predictor / shrinkage

Development cells use `n_observed=0` and identical cell/parent/root priors. Fast path uses **one** `beta_from_prior` then the same mix formula `(k1*p+k2*p)/(k1+k2)` so floats match the three-call version.

## Cost / fatigue

Per-candidate channel intrusiveness is action-dependent — not collapsed. Direct cost is `nominal_cost_paise` lookup.

## ENRV money

`bankers_round_paise` is `Decimal(str(value)).quantize(ROUND_HALF_EVEN)`. Replacing with Python `round()` **changes M7 fingerprints** (tried and reverted). This remains the largest M7 cost that cannot be removed without semantic change.

## Config

`ValuationConfig` rebuilt 753k times (dict copies). Now cell-scoped via `ReviveRunState.valuation_cfg()`.

## Cache declarations

| Cache | Scope | Key | Lifetime | Invalidation |
|-------|-------|-----|----------|--------------|
| `ValuationConfig` | cell | PolicyPack | run state | new cell |
| shrinkage equal-prior mix | none (pure function) | priors | call | n/a |

Predictor remains observable-only, deterministic, no oracle.
