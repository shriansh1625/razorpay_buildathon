# Scarcity Repair

## Root cause

`capacity_scarcity_factor` from profile parameters was not applied to benchmark `ResourceCapacities` or baseline environment constraints.

## Repair

Implemented `revive/benchmark/capacities.py`:

```text
profile → capacity_scarcity_factor → capacity = base / factor
```

Wired into:
- `policy_runner` (REVIVE + baselines)
- `baseline_pipeline` (BF-4 constraints)
- calibration scarcity diagnostics

## Profile capacity comparison

| profile | retry_slots | message_capacity | incentive_budget |
|---------|---------------|------------------|------------------|
| BALANCED | 50 | 100 | 1000000 |
| SCARCE | 20 | 40 | 400000 |
| ABUNDANT | 250 | 500 | 5000000 |

Post-repair scarcity (40-op calibration): **MODERATE SCARCITY**
Post-repair scarcity (500-op official scale): **HIGH SCARCITY**
