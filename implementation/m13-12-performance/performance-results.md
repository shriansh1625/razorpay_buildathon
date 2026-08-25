# M13.12 Performance Results

## lagrangian_allocate only (representative frozen cells)

Source: `performance-results.json` (5-run mean after warmup)

| Seed | Profile | Cycle | Opps | Candidates | Ref (s) | Opt (s) | Speedup |
|------|---------|-------|------|------------|---------|---------|---------|
| 2 | BALANCED | 0 | 251 | 783 | 0.0165 | 0.0101 | **1.62×** |
| 2 | BALANCED | 1457 | 427 | 2554 | 0.0774 | 0.0463 | **1.67×** |
| 5 | SCARCE | 500 | 282 | 1862 | 0.0505 | 0.0297 | **1.70×** |
| 7 | HIGH_NATURAL | 800 | 317 | 2146 | 0.0609 | 0.0384 | **1.58×** |
| 3 | ABUNDANT | 400 | 268 | 1750 | 0.0536 | 0.0337 | **1.59×** |
| 4 | HOSTILE | 600 | 291 | 1871 | 0.0540 | 0.0353 | **1.53×** |
| 6 | DEGRADED | 700 | 295 | 1934 | 0.0591 | 0.0334 | **1.77×** |

All `allocation_hash_match: true`.

**Mean lagrangian speedup: ~1.63×**

## allocate_portfolio end-to-end (same cells)

Includes primal recovery + hash; matches golden/reference tests.

## 50 REVIVE cycles (seed=2, BALANCED)

| Metric | Pre (baseline profile) | Post (optimized) |
|--------|------------------------|----------------|
| Wall time (3-run mean) | 30.17 s | **9.63 s** |
| Speedup | | **~3.1×** |

Post-optimization includes `usage_dict` caching benefiting primal recovery and repeated candidate lookups across the pipeline.

## Memory

- `clear_usage_cache()` at each `allocate_portfolio` — no cross-cell retention
- Cell-based benchmark runner unchanged (M13.11)

## Official benchmark

**NOT executed.** No recovery superiority claims.

## Remaining runtime

At ~9.6 s / 50 cycles, full 2016-cycle cell ≈ **6.5 min** theoretical (down from ~20+ min pre-optimization). M6/M7 paths remain significant; further speedups require separate milestones.
