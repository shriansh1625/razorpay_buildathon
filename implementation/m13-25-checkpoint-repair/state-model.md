# M13.25 State Model

## Authoritative completion

A planned cell is **complete** iff its JSON exists and passes `CellStore.validate_cell_record`:

1. file exists and parses
2. `config_hash`, `policy_pack_hash`, `schema_version`, `metric_version` match store context
3. `metrics_checksum` matches metrics body
4. `(seed, profile, policy_id)` identity matches file + metrics

## Checkpoint manifest (derived)

`checkpoint-manifest.json` is a **cache** of progress:

- `cells_completed` = count of valid planned cells on disk
- `cells_total` = planned run size
- `last_completed_cell` = highest-index valid planned cell

It must never claim completion for a cell that is not durably valid.

## Drift classes

| Class | Files | Manifest | Repair |
|-------|-------|----------|--------|
| Files ahead | N valid | M < N | Raise manifest to N |
| Manifest ahead | N valid | M > N | Lower manifest to N; schedule missing work |
| Invalid last cell | last cell not valid | any | Treat as manifest ahead |
| Corrupt cell file | invalid JSON/checksum | counted if stale | Cell invalid → recompute |

## Group model

A seed/profile **group** is complete iff all five policy artifacts (B0…REVIVE) are valid.

Parallel execution may persist cells incrementally within a group; until all five validate, the group remains pending.
