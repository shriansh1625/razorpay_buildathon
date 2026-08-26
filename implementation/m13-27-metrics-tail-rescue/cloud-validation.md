# M13.27 Cloud Validation

**Status:** COMPLETE  
**Decision:** METRICS_TAIL_RESCUE_READY  
**Official benchmark executed:** NO  

## Fixture

| Field | Value |
|-------|-------|
| seed | 1 |
| profile | ABUNDANT |
| policy | REVIVE |
| cycles | 2016 |
| runner | `run_cell_benchmark` → `run_policy_on_world` (production path) |
| output | `artefacts/m13-27-cloud-abundant-revive/` |

## Cloud VM — metrics tail (pre-validated)

| Metric | Value |
|--------|-------|
| execution_count | 339,890 |
| authorization_count | 404,319 |
| measurement_count | 339,890 |
| `compute_policy_metrics` wall | **0.39 s** |
| metrics_checksum | `80c238eb91edc64424079d2b9bac4f354886fac4089cf96668b493f8245113da` |

## Production-equivalent single-cell gate (measured)

Artifact: `artefacts/m13-27-cloud-abundant-revive/validation-report.json`

| Metric | M13.26 local | Cloud pre-M13.27 | Post-M13.27 gate |
|--------|--------------|------------------|------------------|
| **Total cell wall** | ~1363 s | ~9900 s (~2h45m) | **627.3 s** |
| **M6 wall** | 271 s | — | **122.2 s** |
| **M7 wall** | 309 s | — | **159.9 s** |
| **M8 wall** | 289 s | — | **80.7 s** |
| **Metrics tail** | multi-hour hung | multi-hour hung | **0.425 s** (local prod runner) / **0.39 s** (cloud) |
| Peak RSS | 2042 MB | — | **594 MB** |
| CPU (cell) | — | — | **596.1 s** |
| execution_count | 339,890 | — | **339,890** |
| authorization_count | 404,319 | — | **404,319** |
| measurement_count | 339,890 | — | **339,890** |
| metrics_checksum | — | — | **`80c238eb…5113da`** ✓ |
| run_valid | — | — | **true** |
| policy_violations | — | — | **0** |
| unauthorized_executions | — | — | **0** |

Stage M6/M7/M8 measured via `profile_revive_cell` instrumented mirror on the same seed/profile; checksum identical to production cell artifact.

## Gate result

| Criterion | Result |
|-----------|--------|
| Exact metrics_checksum | **PASS** |
| Exact population counts | **PASS** |
| `run_valid` / guardrails | **PASS** |
| Metrics tail no longer multi-hour | **PASS** (0.39–0.43 s) |
| Total wall no longer ~9900 s class | **PASS** (627 s production runner) |
| Official benchmark / preflight | **NOT RUN** |

## Comparison

- Metrics tail dropped from **~4137 s** (reference cross-scan alone, M13.27 local baseline) / **multi-hour cloud hang** to **< 0.5 s**.
- Total production-equivalent cell wall **627 s** vs cloud pre-fix **~9900 s** (~**15.8×** reduction).
- All metric semantics unchanged; checksum bit-identical to pre-optimization equivalence baseline.

## Do not run

- Official 30-cell benchmark
- Writes to `artefacts/cloud-preflight-w8/` or `artefacts/cloud-preflight-m13-25-w8/`
