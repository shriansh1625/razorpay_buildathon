# M13.15 Performance Results

**Label:** DEVELOPMENT_VALIDATION_ONLY — NOT official evidence

## Development matrix (seed=1, 2 profiles, 10 cells)

| Workers | Wall time | Speedup |
|---------|-----------|---------|
| 1 | 34.0 s | — |
| 2 | 19.3 s | **1.76×** |

Fingerprints: **identical**

## M13.14 reference (2 isolated REVIVE cells, prior cell-level worker)

| Workers | Wall time | Speedup |
|---------|-----------|---------|
| 1 | 1524 s | — |
| 2 | 542 s | **2.81×** |

M13.15 uses **group-level** parallelism (5 policies share one world per worker) — correct semantics for official benchmark.

## Projected official benefit

With M13.14 per-cell runtime (~480 s REVIVE stress) and group-level 2-worker parallelism across 120 seed/profile groups, expect material wall-clock reduction vs sequential — exact official timing requires explicit user invocation.
