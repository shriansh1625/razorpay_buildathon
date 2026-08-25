# M13.14 End-to-End Profile

**Label:** DEVELOPMENT_ONLY — NOT official evidence

Cell: seed=2 profile=BALANCED REVIVE

## Total runtime

| Path | Seconds | Minutes |
|------|---------|---------|
| Reference (no cycle cache) | 600.9 | 10.0 |
| Optimized (cycle cache) | 536.4 | 8.9 |
| Speedup | 1.12x | |

Cycles: 2016

## Stage breakdown (reference path, cumulative seconds)

| Stage | Seconds | Share | Class |
|-------|---------|-------|-------|
| M4 | 28.2 | 4.7% | GREEN |
| M5 | 145.1 | 24.2% | YELLOW |
| M6 | 152.7 | 25.4% | RED |
| M7 | 165.4 | 27.5% | RED |
| M8 | 70.6 | 11.8% | YELLOW |
| M9 | 6.6 | 1.1% | GREEN |
| M10 | 6.6 | 1.1% | GREEN |
| M11 | 0.0 | 0.0% | GREEN |
| M12 | 0.0 | 0.0% | GREEN |

## Counters (reference)

```json
{
  "m4_opportunities": 753479,
  "m6_candidates": 5547419,
  "m7_valuations": 5547419,
  "m8_allocations": 2016,
  "m9_decisions": 121120,
  "m10_authorizations": 121120
}
```

## Semantic check

- Reference cell hash: `d313e5216bd6a1ba250596ae2e60d6212c0833c6c8d622acb63ce0d84945ba30`
- Optimized cell hash: `d313e5216bd6a1ba250596ae2e60d6212c0833c6c8d622acb63ce0d84945ba30`
- Match: True
