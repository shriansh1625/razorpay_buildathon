# B2 Trace — seed=1 BALANCED (official frozen config)

## Cell evidence

File: `artefacts/benchmark/official/cells/seed-001/BALANCED/B2.json`

All recovery metrics `0`, `intervention_count: 0`, `contact_count: 0`, `run_valid: true`, ~24 s wall time.

## Pipeline trace

| Stage | Count |
|-------|------:|
| B2 baseline SELECTED (non-A00) | **158,252** |
| Selected opp_id in sentinel detect set | **0** |
| Dropped at sentinel lookup | **158,252** |
| Authorizations | 0 |
| Executions | 0 |
| Measurements | 0 |

## B2-specific checks

B2 (`b2_contact_all`) selects contact actions aggressively when capacity allows. Trace confirms:

- **Selected contacts**: many per cycle at decision layer
- **Contact capacity**: not the limiting factor — pipeline never reaches reservation/authorization
- **Authorization gates**: never invoked
- **Stopping rules**: never invoked
- **Execution eligibility**: never evaluated

The B2 policy *does* produce nonzero `selected_count` at the decision layer (M13.5 calibration: 37 at mid-cycle on calibration scale). Official scale produces even more selections per cycle, but **100% are discarded** at the same sentinel ID bridge as B1.

## First divergence

```
B2 decide_cycle → SELECTED (>0)
baseline_pipeline sentinel lookup → detected is None → continue
→ authorizations = 0 for entire run
```

Same code path as B1: `revive/benchmark/official/baseline_pipeline.py:92-98`.
