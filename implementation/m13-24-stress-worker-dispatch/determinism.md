# M13.24 Determinism

Same 10-cell development stress workload (`--stress-cells 10`), workers 1 / 2 / 8.

Requirement: exact equality of cell `metrics_checksum`, aggregate fingerprint, and planned cell count.

## Result

`tests/benchmark/test_m13_24_stress_worker_dispatch.py::test_stress_cells_worker_fingerprints_identical` — **PASS**

| Workers | cells_planned | Dispatch | Aggregate fingerprint vs workers=1 | Cell checksums vs workers=1 |
|---------|---------------|----------|------------------------------------|-----------------------------|
| 1 | 10 | sequential | reference | reference |
| 2 | 10 | `parallel workers=2` | identical | identical |
| 8 | 10 | `parallel workers=8` | identical | identical |

Host CPU count: 12 (`validate_workers(8)` accepted).

Metadata:

- workers=2 → `workers=2`
- workers=8 → `workers=8`

Progress includes `parallel workers=N groups=...` for N > 1 and does **not** include that line for N = 1.
