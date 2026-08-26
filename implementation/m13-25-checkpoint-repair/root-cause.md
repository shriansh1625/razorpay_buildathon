# M13.25 Root Cause

## Observed cloud failure

Preflight `--workers 8 --output artefacts/cloud-preflight-w8`:

| Expected | Actual |
|----------|--------|
| 30 cell JSON files | 29 (+ manifest) |
| Missing | `seed-001/ABUNDANT/REVIVE.json` |
| Manifest | `cells_completed=26`, `cells_total=30` |
| `last_completed_cell` | index=10, HIGH_NATURAL REVIVE |

Resume with the same command printed `parallel workers=8 groups=6 cells_planned=30` but did not finish the missing cell for hours; checkpoint stayed at 26.

## First divergence (proved)

**Class F + stale manifest:** resume scheduling uses **valid persisted cell files** for pending groups (correct), but the **checkpoint manifest was never reconciled** with on-disk truth at startup.

Parallel parent updated the manifest **only after a worker returned and `verify_group_persisted` passed** (full 5-policy group). Workers persist cells **one at a time** inside the group. A crash or kill after B0–B3 but before REVIVE yields:

- 4 durable cell files in the ABUNDANT group
- parent never ran group completion checkpoint
- manifest stuck at the last **fully completed** group count (26)
- `last_completed_cell` can reference an older group (index 10) while `cells_completed` is higher — **internally inconsistent**

On resume:

1. ABUNDANT group is correctly re-queued (4/5 valid).
2. Manifest still reports 26 until the missing REVIVE completes.
3. Without startup reconciliation, operators and progress tooling see a stale count even when 29/30 files exist.

**Not the primary bug:** trusting manifest instead of files for **skip** decisions — skip already uses `is_cell_valid`. The defect is **manifest drift** and lack of authoritative repair at startup/finalization.

## Production shape mapping (10-cell repro)

| Cloud | Repro fixture |
|-------|----------------|
| 30 cells | 10 cells (1 seed × 2 profiles × 5 policies) |
| manifest 26, files 29, missing REVIVE | manifest 6, files 9, missing HIGH_NATURAL REVIVE |
| resume completes 30/30 | resume completes 10/10, identical aggregate |

## What it is not

- PolicyPack / epsilon / generator change
- Incorrect pending-group detection (partial groups were already re-queued)
- Deliberate manifest edit on production artifacts
