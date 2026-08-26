# M13.27 Equivalence

## Verification matrix

| Check | Result |
|-------|--------|
| Reference vs optimized (empty inputs) | **PASS** |
| Reference vs optimized (seed=1 BALANCED, 128 cycles) | **PASS** |
| Reference vs optimized (seed=1 BALANCED/SCARCE/HOSTILE, 64 cycles) | **PASS** |
| Synthetic 25k auth × 20k exec unauthorized matching | **PASS** |
| Full seed=1 ABUNDANT population deterministic checksum | **PASS** |
| M13.22 seed=2 BALANCED 15-cycle fingerprints | **PASS** (unchanged) |
| Full pytest suite | **344 passed** |

## Fields compared

Exact equality on full `PolicyRunMetrics.to_dict()` including:

- gross/natural/incremental/net recovered paise
- realized_cost_paise
- intervention_count, contact_count
- unauthorized_executions, execution_failures, idempotency_conflicts
- predicted ENRV / recovery error sums
- budget_utilization, resource_utilization
- run_valid, invalid_reasons
- recovery_rate

## Golden / fingerprint status

- M13.22 `metrics_checksum` for seed=2 BALANCED 15-cycle: unchanged
- Cell fingerprints for optimized runs match reference implementation on all tested populations
