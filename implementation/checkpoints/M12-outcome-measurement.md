# M12 Checkpoint — Outcome Attribution + Recovery Measurement

**Milestone:** M12 — Outcome Attribution + Recovery Measurement (MEASURE)  
**Date:** 2026-08-23  
**Status:** COMPLETE

---

## Purpose

Authoritative measurement layer converting M7 predictions + M11 execution into **measured recovery** with natural-recovery attribution, incremental accounting, and calibration-ready provenance. No benchmark comparison.

---

## Measurement architecture

```text
ExecutionResult (M11)
        +
CandidateValuation (M7) — read-only
        +
AllocationDecision
        ↓
measure_execution()
        ↓
AttributionSplit (docs/21 §3)
        +
No-action reference (predicted + optional oracle A00)
        ↓
RecoveryMeasurement
        ↓
CycleMeasurement / BatchTotals (aggregation primitives)
```

Package: `revive/measurement/`

---

## Outcome model

`RecoveryMeasurement` separates three worlds:

| World | Fields |
|-------|--------|
| Predicted (M7) | `predicted_*` — never overwritten |
| Realized (M11) | `gross_recovered_paise`, `realized_cost_paise`, etc. |
| Counterfactual | `predicted_no_action_reference_paise`, `realized_no_action_reference_paise` |

Identity AT-3 enforced: `gross = attributed + natural + ambiguous`.

---

## Attribution model

From M11 `RealizedOutcome.attribution_class` (docs/21 §3):

| Class | Bucket |
|-------|--------|
| `ATTRIBUTED` | `attributed_recovered_paise` (M-06) |
| `NATURAL` | `natural_recovered_paise` (M-07) |
| `AMBIGUOUS` | `ambiguous_recovered_paise` (M-09) |

Late recovery (`observed_within_horizon=False`) → zero gross buckets.

Multi-action dedup → `MULTI_ACTION_DEDUP` when recovery already counted on opportunity.

---

## Natural recovery

- `predicted_no_action_reference_paise` = `p(i,∅) · V(i) · m` from M7 valuation
- `realized_no_action_reference_paise` = oracle A00 at evaluator boundary (optional)
- Natural-class recoveries do not receive incremental credit (`incremental_recovered_paise = 0`)
- A00 ENRV=0 preserved; natural recovery may still be non-zero

---

## Incremental recovery

| Field | Semantics |
|-------|-----------|
| `incremental_recovered_paise` | Attributed component (M-06 case-level) |
| `incremental_vs_no_action_paise` | `gross − no_action_reference` (user example semantics) |

Example: V=₹20,000, no-action ref=₹7,000, realized=₹18,000 → incremental_vs_no_action=₹11,000.

---

## Cost accounting

- `predicted_cost_paise` from M7 (`cost + expected_incentive`) — immutable
- `realized_cost_paise` from M11 execution
- `realized_net_value_paise` = `attributed × m − realized_cost`
- Failed executions record cost even when recovery=0

---

## Prediction vs realization

Calibration fields preserved (no recalibration in M12):

- `enrv_prediction_error_paise` = `realized_net − predicted_enrv`
- `recovery_prediction_error_paise` = `gross − predicted_gross`

---

## Multi-action attribution

`OpportunityRecoveryLedger` tracks gross recovery already counted per opportunity.

Second execution with recovery on same opportunity → zero monetary buckets, `MULTI_ACTION_DEDUP`.

Batch aggregation sums without double-counting.

---

## Idempotency

- `measurement_id = H(execution_id, measurement_version)`
- `MeasurementStore` — one measurement per execution_id
- Repeated calls return identical measurement with `duplicate_measurement=True`

---

## Provenance

`MeasurementProvenance` links: execution_id, authorization_id, decision_id, opportunity_id, candidate_id, cycle_id, configuration_hash, valuation/strategy/execution/measurement versions.

---

## Aggregation

| Type | Entry |
|------|-------|
| Cycle | `aggregate_cycle()` |
| Batch | `aggregate_batch()` |
| Safety | `safety_event_counts()` — raw data for M13 guardrails |

No baseline comparison, rankings, or win-rate claims.

---

## Tests

| File | Coverage |
|------|----------|
| `test_measurement_core.py` | Full/partial/no recovery, natural, incremental, costs |
| `test_measurement_idempotency.py` | Idempotent measure, multi-action dedup, batch |
| `test_measurement_integrity.py` | Oracle boundary, no hidden fields in output |

**14 new tests** — full suite **201 passing**.

---

## Results

- [x] Execution outcomes measured
- [x] Gross / attributed / natural / ambiguous split
- [x] Incremental recovery per docs
- [x] Prediction vs realization separate
- [x] Partial recovery supported
- [x] Failed execution cost recorded
- [x] Multi-action no double-count
- [x] Idempotent measurement
- [x] Provenance complete
- [x] Cycle/batch aggregation primitives
- [x] Safety event accounting
- [x] Oracle boundary intact
- [x] No benchmark / learning / UI

---

## Known limitations

- M-10 paired policy comparison deferred to M13
- `realized_no_action_reference_paise` requires oracle partition at measurement boundary
- Fatigue realized uses M7 predicted fatigue_cost (no separate M11 fatigue realization yet)
- Cycle stopped-opportunity counting requires caller-supplied ID set

---

## Provisional parameters

- `DEFAULT_NET_RETENTION = 1.0`
- `DEFAULT_HORIZON_MINUTES = 10080` (7 days)

---

## Deviations

None material.

---

## Deferred decisions

- Official horizon per risk class (policy pack)
- M13 benchmark runner wiring
- Learning/calibration engine

---

## Next milestone

**M13 — OFFICIAL BENCHMARK** (not started). M12 STOP.
