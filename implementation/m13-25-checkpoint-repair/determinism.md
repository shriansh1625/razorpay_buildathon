# M13.25 Determinism

## Requirement

Identical final aggregate and per-cell `metrics_checksum` for:

- uninterrupted workers=1
- parallel workers=1 / 2 / 3
- resume after partial/interrupted states

## Result

`test_parallel_order_independence` and all resume tests — **PASS**

Aggregate fingerprint and cell checksum maps match reference uninterrupted run.
