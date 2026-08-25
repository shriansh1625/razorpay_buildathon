# M13.12 Optimization Options

## A — Safe fast path (uncoupled resources)

**Status:** NOT IMPLEMENTED

No mathematically proven condition in docs/10 that independent per-opportunity greedy selection is globally optimal when shared capacities bind. Counterexamples exist when a single shared slot forces deferral of a lower-RV opportunity.

## B — Candidate decomposition (uncoupled / coupled split)

**Status:** NOT IMPLEMENTED

Could not prove equivalence without full Lagrangian solve on coupled subset.

## C — Warm start (`lambda_warm_start`)

**Status:** NOT IMPLEMENTED in pipeline

Parameter exists but `revive_pipeline` does not pass prior-cycle lambdas. Cross-cycle warm start risks different iteration trajectories before convergence; would require equivalence proof across changing portfolios.

## D — Precomputation (IMPLEMENTED)

- `_eligible_candidates()` once per item per allocation call
- `item_by_id` map once per `lagrangian_allocate`
- `usage_dict` id-cache cleared at `allocate_portfolio` entry (bounded lifetime)

## E — Sorting / copying (IMPLEMENTED)

- Iterate `pc.usage` tuples directly in `_reduced_value_paise` and `_accumulate_usage` (avoid dict in inner loop)
- Remove per-iteration filtered pick dict copies
- Reuse eligible candidate tuples in `primal_recovery`

## F — Numerical loop (NOT CHANGED)

`k_max`, `iteration_budget`, `duality_tolerance`, step rule unchanged.

## G — Pipeline invocation (ASSESSED)

No duplicate allocate on identical inputs found. Per-cycle portfolio rebuild is required by semantics.

## Implemented package

| Change | File |
|--------|------|
| Eligible-candidate prefilter | `lagrangian.py` |
| Tuple-based reduced value | `lagrangian.py` |
| Usage accumulation without dict copies | `lagrangian.py` |
| `usage_dict` id-cache + `clear_usage_cache()` | `resources.py`, `allocate.py` |
| Reference implementation preserved | `lagrangian_reference.py` |
