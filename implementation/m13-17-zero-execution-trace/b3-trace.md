# B3 Trace — seed=1 BALANCED (official frozen config)

## Cell evidence

File: `artefacts/benchmark/official/cells/seed-001/BALANCED/B3.json`

All recovery metrics `0`, `intervention_count: 0`, `run_valid: true`.

## Pipeline trace

| Stage | Count |
|-------|------:|
| B3 baseline SELECTED (non-A00) | **100,902** |
| Selected opp_id in sentinel detect set | **0** |
| Dropped at sentinel lookup | **100,902** |
| Authorizations | 0 |
| Executions | 0 |

## B3-specific checks

### Raw ENRV selections

B3 greedy ENRV **does select** at decision layer on official config. Mid-cycle single-cycle selected count: **134** (official scale) vs M13.5 calibration snapshot **36** (calibration scale) — scale differs, but both are nonzero at decision layer.

### ε=100 effect

Official PolicyPack ε=100 paise is used in B3 `decide_cycle` via `BaselineCycleContext.epsilon_paise`. This affects which actions B3 selects, but is **not** the zero-execution cause — selections exist; they never reach M10.

### M9 / benchmark pipeline discard

B3 baseline path **does not use M8/M9**. Selections are produced by `run_baseline_cycle()` directly. Discard happens in `run_baseline_cycle_full()` before any `AllocationDecision` or `seal_allocation()` call.

### PolicyPack / threshold

No evidence that official ε=100 causes zero selections. Evidence shows **nonzero selections, zero sentinel ID matches**.

## M13.5 calibration comparison

M13.5 mid-cycle B3 snapshot (calibration scale, draft pack):

- `selected_count: 36`
- `total_enrv_selected_paise: 4,492,227`

That snapshot measured **`run_baseline_cycle` only** — not `run_baseline_cycle_full`. Calibration never tested the sentinel bridge.

At official scale mid-cycle: B3 selected **134** decisions, **0** with IDs present in sentinel output.
