# M13.25 Atomicity

## Per cell

1. Worker/parent writes cell JSON via `atomic_write_json` (`.tmp` then replace)
2. Checkpoint updated **after** the cell is valid (sequential: immediately; parallel: after full group verified on parent)

## Forbidden state

**Manifest claims complete + cell missing/invalid** — prevented by reconciliation: manifest count and `last_completed_cell` are always recomputed from validated files before scheduling.

## Recoverable state

**Cell exists + manifest behind** — repaired at startup (`files_ahead`). Resume schedules only missing cells/groups.

## Parallel note

Multiple workers must not write the same manifest concurrently (Windows file locking). Workers persist cells only; **parent** owns checkpoint manifest updates.
