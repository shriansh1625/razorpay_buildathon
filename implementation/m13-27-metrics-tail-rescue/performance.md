# M13.27 Performance

## Primary target: `compute_policy_metrics` tail

| Cell | Executions | Old tail (measured/estimated) | New tail (measured) |
|------|------------|-------------------------------|---------------------|
| seed=1 ABUNDANT REVIVE | 339,890 | **4137.6 s** reference unauthorized cross-scan (measured on same population) | **0.321 s** wall / **0.313 s** CPU (`abundant-metrics-tail.json`) |
| seed=1 BALANCED REVIVE (128 cycles) | ~6k | reference ≈ optimized (ms) | sub-ms |

## Before/after microbench (blocked-authorization stress)

Population: 4k authorizations (⅓ `BLOCKED`), 3.5k succeeded executions — scales to ABUNDANT dimensions.

| Implementation | Wall (s) | Speedup |
|----------------|----------|---------|
| Reference `any()` cross-scan | 0.173 | 1× |
| Optimized indexed | 0.001 | **~169×** |

## Full cell context (unchanged pipeline)

| Metric | M13.26 ABUNDANT |
|--------|-----------------|
| Cell wall (cycles only) | ~1363 s |
| Cloud observed | ~9900 s (~2h45m) |

M13.27 removes the metrics-tail pathology; remaining cloud gap vs local cycle wall is hardware / environment, not repeated auth×exec scanning.

## Tests enforcing performance

`tests/benchmark/test_m13_27_metrics_tail_performance.py::test_abundant_metrics_tail_bounded` — full ABUNDANT population must complete metrics aggregation in **< 5 s**.
