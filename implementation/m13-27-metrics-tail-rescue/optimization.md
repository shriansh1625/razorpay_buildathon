# M13.27 Optimization

File: `revive/benchmark/official/metrics.py`

## A. Authorization index (primary fix)

One pass over executions builds the set of authorization IDs with at least one `SUCCEEDED` execution:

```python
succeeded_auth_ids: set[str] = set()
for execution in executions:
    ...
    if stage == ExecutionStage.SUCCEEDED:
        succeeded_auth_ids.add(execution.authorization_id)

unauthorized_executions = sum(
    1
    for authorization in authorizations
    if authorization.authorization_state != AuthorizationState.AUTHORIZED
    and authorization.authorization_id in succeeded_auth_ids
)
```

Semantically identical to the prior `any(...)` scan; complexity **O(|executions| + |authorizations|)**.

## B. Single pass over executions

Merged:

- `contact_count`
- `execution_failures`
- `idempotency_conflicts`
- `succeeded_auth_ids`

Inlined the subset of `safety_event_counts` used by policy metrics (blocked/cancelled count not used here).

## C. Single pass over measurements

Merged ENRV/recovery sums and `duplicate_effects` into one loop (batch totals still from `aggregate_batch`).

## D. Forensics harness

Restored production `compute_policy_metrics` in `forensics.py` (removed M13.26 dev bypass).

## Not changed

- Metric definitions
- Decimal/money paths
- M6/M7/M8/recovery semantics
- Benchmark configuration
