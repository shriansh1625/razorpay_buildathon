# B1 Trace — seed=1 BALANCED (official frozen config)

## Cell evidence (immutable)

File: `artefacts/benchmark/official/cells/seed-001/BALANCED/B1.json`

| Field | Value |
|-------|-------|
| `intervention_count` | 0 |
| `contact_count` | 0 |
| `gross_recovered_paise` | 0 |
| `natural_recovered_paise` | 0 |
| `incremental_recovered_paise` | 0 |
| `net_recovered_paise` | 0 |
| `realized_cost_paise` | 0 |
| `run_valid` | true |
| `elapsed_seconds` | ~24 |

## Pipeline trace (read-only re-simulation)

Config: official sealed `pol_m13_official_v1`, ε=100, 500 opps, 100 customers, 21 days, 2016 cycles.

### Per-stage totals (full run)

| Stage | Count |
|-------|------:|
| Baseline B1 `DecisionOutcome.SELECTED` (non-A00) | **117,949** |
| Selected opp_id found in `detect()` output | **0** |
| Dropped at `detected is None` (`baseline_pipeline.py:96-98`) | **117,949** |
| Candidate/valuation resolved | 0 |
| `authorize_execution()` calls recorded | 0 |
| `execute_authorization()` | 0 |
| `measure_execution()` | 0 |

### Mid-cycle snapshot (cycle at day 10.5)

| Metric | Value |
|--------|------:|
| Observable world opportunities | 500 |
| Sentinel-detected opportunities | 341 |
| B1 selected (single cycle) | 134 |
| Selected IDs overlapping sentinel IDs | **0** |

### Root mechanism

1. `run_baseline_cycle()` decides on **world `opportunity_id`** values from `opportunities_from_observable(view)` (`revive/benchmark/runner.py:17-21`).

2. `run_baseline_cycle_full()` resolves execution candidates via **`detect(view, now).opportunities`**, keyed by sentinel-derived IDs (`revive/benchmark/official/baseline_pipeline.py:87-98`).

3. Sentinel assigns `opportunity_id = opportunity_id_for(natural_key)` (`revive/recovery/sentinel/detect.py:312`), which **does not equal** generator world `opportunity_id` (`revive/simulation/generator.py:453`).

4. Observable vs sentinel ID overlap at calibration scale is also **0/40** — the mismatch predates official scale.

### Cycle aggregates (pattern)

Every cycle with B1 selections follows:

- `candidate decisions` > 0
- `selected actions` > 0
- `NO_ACTION` on non-eligible opps
- `allocation` N/A
- `sealed` N/A
- `authorized` **0** (never attempted)
- `execution` **0**

## Conclusion for B1

Actions are selected by B1 policy logic but **vanish at the baseline→sentinel ID bridge** before M10. M10 gates are never evaluated for B1.
