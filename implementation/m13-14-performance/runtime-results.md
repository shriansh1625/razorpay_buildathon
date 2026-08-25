# M13.14 Runtime Results

**Label:** DEVELOPMENT_ONLY — NOT official evidence

## Stress cell (seed=2 BALANCED REVIVE)

| Metric | Before (M13.13) | After (M13.14) |
|--------|-----------------|----------------|
| Wall time | 1058.2 s | 480.1 s |
| Speedup | — | **2.20×** |
| Peak RSS | ~529 MB | ~550 MB |

## Baseline unchanged

Baseline median ~31 s/cell (M13.13) — not re-profiled; M13.14 changes REVIVE path only.

## Projected official 600-cell runtime (development estimate)

Using M13.14 stress-cell REVIVE time (480 s) + M13.13 baseline median (31 s):

| Scope | Hours |
|-------|-------|
| 120 REVIVE cells | **16.0 h** |
| 480 baseline cells | **4.1 h** |
| **600 total (median)** | **~20.1 h** |

Compare M13.13 conservative projection: **40.4 h**

## Representative REVIVE cells (optimized pipeline)

Golden hash preserved for all; see `tests/benchmark/golden/m13_14_seed2_balanced_revive.json`.
