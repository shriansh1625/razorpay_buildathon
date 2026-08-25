# M13.15 CLI Design

**Label:** DEVELOPMENT / OFFICIAL infrastructure only

## New option

```
revive benchmark --mode {development,official} [--workers N]
```

| Flag | Default | Meaning |
|------|---------|---------|
| `--workers` | `1` | Parallel seed/profile groups |

## Examples

```bash
revive benchmark --mode development --workers 1
revive benchmark --mode development --workers 2
revive benchmark --mode official --workers 2
```

## Validation

- `1 <= N <= os.cpu_count()`
- Default `1` preserves legacy sequential behavior exactly
- Official mode without `--workers` is identical to `--workers 1`

## Wiring

`revive.cli` → `execute_benchmark(workers=N)` → `run_cell_benchmark(workers=N)` → parallel path when `N > 1`
