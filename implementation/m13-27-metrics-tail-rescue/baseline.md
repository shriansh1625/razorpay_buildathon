# M13.27 Baseline

Fixture: **seed=1, profile=ABUNDANT, policy=REVIVE**, official frozen scale (2016 cycles).

Captured before optimization via production pipeline population (`_run_revive_cycles` full cell).

## Population

| Field | Value |
|-------|-------|
| cycles | 2016 |
| measurements | 339,890 |
| executions | 339,890 |
| authorizations | 404,319 |
| intervention_count | 339,890 |
| unauthorized_executions | 0 |
| run_valid | true |

## Performance (pre-fix behavior)

| Metric | Value |
|--------|-------|
| Cell pipeline wall (M13.26 forensic) | ~1363 s |
| `compute_policy_metrics` tail (ABUNDANT population) | **4137.6 s** reference unauthorized scan alone; **0.321 s** optimized |
| `metrics_checksum` | `80c238eb91edc64424079d2b9bac4f354886fac4089cf96668b493f8245113da` |

## Equivalence anchor

Reference implementation preserved in `tests/benchmark/test_m13_27_metrics_tail_performance.py::_compute_policy_metrics_reference`.

Full ABUNDANT population: optimized output matches reference on all scalar fields and `metrics_checksum` (deterministic repeated run test).
