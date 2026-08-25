# First Divergence — Official seed=1 BALANCED

Read-only trace. Official artifacts untouched.

## Summary

| Policy | Last stage with nonzero work | First stage where work becomes zero | Evidence |
|--------|------------------------------|-------------------------------------|----------|
| B0 | Policy decision (by design) | N/A — no selections | `selected_count=0` always |
| B1 | Baseline policy decision | Sentinel bridge in `baseline_pipeline.py` | 117,949 selections → 0 reach auth |
| B2 | Baseline policy decision | Sentinel bridge in `baseline_pipeline.py` | 158,252 selections → 0 reach auth |
| B3 | Baseline policy decision | Sentinel bridge in `baseline_pipeline.py` | 100,902 selections → 0 reach auth |
| REVIVE | M8 allocation + M9 seal | M10 G7 approval gate | 121,107 authorizations → 0 authorized → 0 executions |

## B1 example (representative)

```
decisions (baseline SELECTED)     = 117,949
allocation (N/A for baselines)    = —
sealed (N/A — baselines skip M9)  = —
sentinel lookup match             = 0
authorization attempts            = 0
execution                         = 0
measurements                      = 0
cell intervention_count           = 0
```

## REVIVE example

```
M4 sentinel opportunities/cycle  > 0 (aggregate ~5.6/cycle)
M6 candidates                     > 0
M7 ENRV-positive                  > 0
M8 selected                       > 0 (~60/cycle avg over full run)
M9 sealed decisions               > 0 (one per M8 selection)
M10 authorized                    = 0
M10 REQUIRES_HUMAN_APPROVAL       = 121,107 (100%)
M11 executions                    = 0
M12 measurements                  = 0
cell intervention_count           = 0
```

## Official artifact confirmation

`artefacts/benchmark/official/cells/seed-001/BALANCED/*.json` — all policies:

- `intervention_count: 0`
- `contact_count: 0`
- all recovery paise fields `0`
- `run_valid: true`

This is not M-10-only collapse. Execution never occurs.
