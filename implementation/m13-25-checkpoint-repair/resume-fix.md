# M13.25 Resume Fix

## Code changes

| File | Change |
|------|--------|
| `cells/store.py` | `reconcile_checkpoint`, `sync_checkpoint_from_persisted`, `last_completed_cell`, `CheckpointReconciliation` |
| `cells/runner.py` | Reconcile at startup; attach report to metadata |
| `cells/parallel.py` | Parent `sync_checkpoint_from_persisted` after each verified group + before aggregate |

## Unchanged

- Official/preflight config, PolicyPack, epsilon, metrics, M8, B3
- Pending-group detection (`is_cell_valid` per cell)
- `verify_group_persisted` fail-closed group completion
- Production artifact directory `artefacts/cloud-preflight-w8/` (not modified)

## Operator effect

Resuming a partial preflight in a **new** output directory (after fix) will:

1. Reconcile manifest to valid file count on entry
2. Schedule only groups with missing/invalid cells
3. Finish with manifest == valid count == planned total
