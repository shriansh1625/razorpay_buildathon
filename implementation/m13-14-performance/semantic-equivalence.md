# M13.14 Semantic Equivalence

**Label:** DEVELOPMENT_ONLY

## Golden cell

| Field | Value |
|-------|-------|
| seed | 2 |
| profile | BALANCED |
| policy | REVIVE |
| golden file | `tests/benchmark/golden/m13_14_seed2_balanced_revive.json` |

## Fingerprints

| Check | Result |
|-------|--------|
| Optimized path vs reference (no cache) | **Match** |
| Reference vs M13.13 feasibility stress cell | **Match** (`d313e5216bd6a1ba…`) |
| M8 allocation vs reference implementation | **Match** (M13.12 regression) |

## Cache invalidation rules

| Cache | Scope | Invalidation |
|-------|-------|--------------|
| CycleViewCache | single cycle | new cycle / new observable view |
| method_failure_rates (within cache) | single cycle | with CycleViewCache |
| M7 A00 reuse | single candidate | N/A (no cache; direct reuse) |

Stale cache would change context assembly → different diagnoses/valuations → caught by golden cell test.
