# M13.15 Checkpoint Safety

**Label:** DEVELOPMENT / OFFICIAL infrastructure only

## Rules

1. Workers write **only** atomic cell JSON files (`CellStore.write_cell`)
2. **Main process** updates `checkpoint-manifest.json` after each group completes
3. `cells_completed` = count of valid cells in planned matrix (not completion order)
4. `last_completed_cell` = highest cell index in the completed group
5. Resume skips valid cells/groups regardless of parallel completion order

## Config guard

Workers reject execution if recomputed `official_benchmark_config_hash()` ≠ expected hash.

Existing `assert_checkpoint_config_compatible()` unchanged for resume.

## Failure propagation

Worker exceptions propagate to main process as `RuntimeError` — benchmark does not silently mark failed cells valid.
