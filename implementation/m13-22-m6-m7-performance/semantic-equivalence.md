# M13.22 Semantic Equivalence

## Frozen config

Unchanged: 21d / 500 opps / 100 customers / 15-min / 6 profiles / seeds 1–20 / ε=100 / `pol_m13_official_v1` / B1 `adr-013_v1` / `strat_m7_benchmark_v1` / `simulated_v1` / metrics `0.12.0-m12`.

## Captured before optimization (15 cycles, seed=2 BALANCED)

| Fingerprint | Value |
|-------------|-------|
| M6 | `b9af5e6f94cf16997a1fa4be600130396041ac6c379aa672dbaeb1b2d070879f` |
| M7 | `bda2c8a45a6c6ad460958bf3f4455470b9ee66b0055e45b8bcd4ee198f1f2e4c` |
| metrics_checksum | `37d9db486094b16b614dfa20230c7e229d23df3e147674c330ada324858755cf` |

Post-optimization: **exact match** (`tests/benchmark/test_m13_22_m6_m7.py`).

## Rejected change

`bankers_round_paise` → Python `round()` changed M7 hash. Reverted to `Decimal(str).quantize(ROUND_HALF_EVEN)`.

## Full cell

seed=2 BALANCED REVIVE `cell_result_hash` prefix `d8cd30d5ded34e7c` matches M13.21 profile print; intervention_count=101615.

## Tests

94 passed: recovery M6/M7 suite, execution bridge, identity index, M13.22 fingerprint tests.
