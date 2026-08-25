# M13.14 Optimization Plan

**Label:** DEVELOPMENT_ONLY

## Implemented (M13.14)

### 1. CycleViewCache (M5 primary)

- **Scope:** one REVIVE cycle; invalidated each `begin_cycle()` when observable view or `now_micros` changes.
- **Key:** `(id(view), now_micros)`
- **Precomputes:** customer/instrument/checkout/subscription/mandate/invoice indexes; transactions-by-customer; contact stats by customer; degraded payment methods; merchant failure rate; method failure rate memoization.
- **Correctness:** indexes are over immutable observable snapshot at cycle start; world mutations occur only after M11 for selected assignments.

### 2. M7 A00 natural probability reuse

- Reuses already-computed `natural_prob` for A00 candidates instead of redundant `estimate_natural_probability()` call.
- **Correctness:** identical mathematics; A00 branch of `estimate_action_probability` is a pure recompute.

### 3. M8 (M13.12 — unchanged)

- Lagrangian allocator optimizations retained; reference hash regression in tests.

## Investigated, not changed

| Area | Finding |
|------|---------|
| M4 detect | Runs once per cycle; full world scan inherent to sentinel semantics |
| M6 generate | Per-opportunity rule evaluation required; config resolved per opp (minor) |
| M9–M12 | Small share of total runtime at official scale |
| Cross-cycle warm start | Unsafe without formal proof; not implemented |
| Global caches | Prohibited by M13.14 semantics rule |

## Parallel execution (development only)

- `run_cells_parallel(workers=1|2)` for independent REVIVE cells
- Separate output paths and process isolation
- Fingerprint equality required vs sequential

## Remaining hotspot after M13.14

M8 Lagrangian allocation + M7 valuation loop volume (opportunities × candidates × cycles) — see `hotspot-analysis.md` after profiling completes.
