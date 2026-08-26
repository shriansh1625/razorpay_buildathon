# M13.25 Performance

## Reconciliation cost

O(planned cells) — one `is_cell_valid` per planned cell (read + validate JSON metadata). No world regeneration, no full tree scan beyond planned paths.

For preflight n=30 or official n=600: negligible vs cell execution time.

## Parallel checkpoint

Parent-only manifest writes avoid cross-process file locking (required on Windows). Workers retain incremental cell persistence without touching the manifest.
