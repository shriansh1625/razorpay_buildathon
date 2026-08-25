# M13.12 Hotspot Analysis

## Confirmed bottleneck

`lagrangian_allocate()` inner loop:

```text
for k in 1..k_max (40):
  for each opportunity (up to ~500):
    for each candidate (up to ~6):
      _reduced_value_paise()
      sort_key_candidate()
  _total_usage() / _contact_violation()
```

At worst observed cycle: **427 opps × ~6 candidates × 40 iterations ≈ 102,000** `_best_action_for_opportunity` calls per allocate invocation.

With **2016 cycles/cell**, allocate_portfolio alone was ~96 s per REVIVE cell (seed=2, BALANCED) before optimization.

## Computational explosion

| Factor | Official-scale observed |
|--------|-------------------------|
| Cycles per cell | 2016 |
| Portfolio items per cycle | 251–500 |
| Candidates per cycle | 783–2554 |
| Lagrangian iterations | 40 (fixed) |
| Inner-loop ops per iteration | O(items × eligible_candidates) |

REVIVE cell wall time (~7–8 min reported) is dominated by **repeated full-pipeline cycles**, with **lagrangian_allocate** as the largest single function inside `allocate_portfolio` (~28% of 50-cycle profile cumulative time; M6/M7 paths are also significant but out of M13.12 allocator scope).

## Pre-optimization micro-hotspots (per call)

1. `_best_action_for_opportunity` — repeated candidate scan every iteration
2. `_reduced_value_paise` — 1.76M calls / 50 cycles; `usage_dict()` dict copy each time
3. `usage_dict` — 2.35M calls / 50 cycles
4. Filtered dict copies `{oid: pc for ...}` passed to `_total_usage` / `_contact_violation` each iteration
5. `sort_key_candidate` — tie-break comparisons

## Memory

No world retention in allocator path. Pre-optimization: ephemeral dict churn from `usage_dict()` and per-iteration pick maps.

## Candidate G (pipeline)

- `lambda_warm_start` is **not** passed from `revive_pipeline` — no cross-cycle warm start in production path
- `begin_cycle()` resets per-cycle resource counters; portfolio rebuilt each cycle
- Empty portfolio returns early in `run_revive_cycle`
- Singleton portfolios still invoke full solver (acceptable; rare at scale)
