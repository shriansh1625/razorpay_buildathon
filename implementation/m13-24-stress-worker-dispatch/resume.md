# M13.24 Resume

## Protocol

1. Uninterrupted: `--mode development --stress-cells 10 --workers 8`
2. Partial: same output dir, `--workers 8 --stop-after-cell 5`
3. Resume: same output dir, `--workers 8 --stress-cells 10`

Require identical final aggregate fingerprint and per-cell `metrics_checksum` vs uninterrupted workers=8.

## Result

`test_stress_cells_workers_eight_resume_matches_uninterrupted` — **PASS**

Partial run planned 5 cells. Resume skipped the persisted cells (`cells_skipped >= 5`) and completed 10.

Workers=2 resume (`test_stress_cells_workers_two_resume_matches_uninterrupted`) also **PASS** (same fingerprints vs uninterrupted workers=2).

`--stop-after-cell` is now forwarded through `run_stress_benchmark`; previously the stress branch ignored it.
