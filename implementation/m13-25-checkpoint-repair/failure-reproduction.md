# M13.25 Failure Reproduction

Isolated fixture: `tests/benchmark/test_m13_25_checkpoint_resume.py`

Matrix: 1 seed × (BALANCED, HIGH_NATURAL) × 5 policies = **10 cells**, **2 groups**, `workers=2`.

## Scenarios covered

| Test | Simulated failure |
|------|-------------------|
| `test_reconcile_files_ahead_of_manifest` | 9/10 files, manifest=6 |
| `test_reconcile_manifest_ahead_of_files` | manifest=10, one file deleted |
| `test_corrupt_cell_is_recomputed` | tampered metrics / bad checksum |
| `test_partial_group_four_of_five_resume` | 9 cells done, manifest stuck at 5, missing REVIVE |
| `test_production_failure_shape_resume` | 9/10 files, manifest=6, missing HIGH_NATURAL REVIVE |
| `test_parallel_order_independence` | workers 1/2/3 identical fingerprints |
| `test_interruption_then_resume_parallel` | stop_after_cell=5, resume workers=2 |

All use temp dirs under pytest — **not** `artefacts/cloud-preflight-w8/`.
