# M13.25 Reconciliation Design

## `reconcile_checkpoint(store, planned, cells_total)`

Called at the start of every `run_cell_benchmark` (sequential and parallel):

1. Read existing manifest (if any)
2. Count valid cells among **planned** cells only (`is_cell_valid` per planned entry — O(n) metadata reads, no world regeneration)
3. Detect drift:
   - `manifest_ahead`: manifest count > valid count, or `last_completed_cell` not valid
   - `files_ahead`: valid count > manifest count
4. Rewrite manifest from file truth via `sync_checkpoint_from_persisted`
5. Return `CheckpointReconciliation` report (stored in run metadata)

## Resume scheduling (unchanged semantics)

Pending parallel groups: any group where valid count < 5.

Workers skip valid cells inside a group; only missing/invalid cells execute.

## Finalization

Parallel parent calls `sync_checkpoint_from_persisted` after each verified group and once more before aggregation.

Sequential runner already checkpoints after each cell write.

## Performance

Reconciliation is O(planned cells) file stat + JSON header validation — no simulation, no directory glob of unrelated paths.
