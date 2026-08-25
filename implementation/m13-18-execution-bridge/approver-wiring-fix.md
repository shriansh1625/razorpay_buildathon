# Approver — Wiring Fix (M13.18)

## Module

`revive/policy/simulated_approver.py`

## Model

`simulated_v1` — frozen deterministic approver:

- Uses `g7_approval_triggers()` (shared with `revive/policy/gates.py`)
- If no triggers → returns `None` (G7 allows without approval state)
- If triggers → deterministic draw from `stream(seed, "approver")` keyed by `idempotency_key`
- Rate: `SIMULATED_V1_APPROVAL_RATE = 0.85`
- Rejects on observable `risk_flags`, `merchant_halt`, `value_written_off`

## Integration

Before `authorize_execution()` in:

- `revive/benchmark/official/baseline_pipeline.py`
- `revive/benchmark/official/revive_pipeline.py`
- `revive/benchmark/official/performance/profiling.py`

Uses `authorize_context_with_simulated_approval()` with `OFFICIAL_APPROVER_VERSION`.

## Preserved

- G7 gate logic unchanged
- No auto-approve bypass
- No oracle access
