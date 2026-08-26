# M13.27 Root Cause

## Production call graph

```
run_cell_benchmark (cells/runner.py)
  └─ _run_single_policy_cell
       └─ run_policy_on_world (policy_runner.py)
            └─ run_revive_cycle × 2016
            └─ compute_policy_metrics (metrics.py)   ← metrics tail
                 ├─ aggregate_batch(measurements)
                 ├─ per-measurement sums / duplicate_effects
                 ├─ per-execution contact + safety counters
                 ├─ unauthorized_executions  [HOT — was O(auth × exec)]
                 └─ budget/resource utilization
       └─ CellStore.write_cell(metrics.to_dict())
```

Other production callers of `compute_policy_metrics`:

- `revive/benchmark/official/cells/parallel_worker.py` (worker cell completion)
- `revive/benchmark/official/performance/profiling.py` (stage profiling metadata)
- `revive/benchmark/official/performance/golden.py` (golden capture)

## Measured hot path (pre-fix)

In `compute_policy_metrics`, the guardrail counter:

```python
metrics.unauthorized_executions = sum(
    1 for a in authorizations
    if a.authorization_state != AuthorizationState.AUTHORIZED
    and any(
        e.authorization_id == a.authorization_id
        and e.execution_stage == ExecutionStage.SUCCEEDED
        for e in executions
    )
)
```

For each non-`AUTHORIZED` authorization this rescans the full execution list. Worst-case complexity is **O(|authorizations| × |executions|)**.

At ABUNDANT official scale (~404k authorizations, ~340k executions) this cross-scan is unbounded in the metrics tail and matches M13.26 cloud evidence: cycles finish, process stays at ~100% CPU in post-cycle production work.

Secondary repeated work (lower order but still removed):

- Separate passes over `executions` for `contact_count` and `safety_event_counts`
- Four separate passes over `measurements` for ENRV/recovery sums plus duplicate count

## Not the cause

- M6/M7/M8 pipeline (bounded; measured separately in M13.26)
- Cell JSON persistence (checksum write is O(metrics dict size))
- Decimal/float changes (not touched)
