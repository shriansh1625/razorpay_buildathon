# M13.24 Dispatch Fix

## Change

Forward the requested worker count (and stop/resume args) through the stress-cells branch into the existing cell runner.

### `run_stress_benchmark`

Now passes through:

- `workers`
- `stop_after_cell`
- `benchmark_mode`

Still uses `max_cells=cell_count` so `--stress-cells N` remains the same limited development workload.

`workers == 1` → existing sequential `run_cell_benchmark`.
`workers > 1` → existing `run_cell_benchmark_parallel()` in `revive/benchmark/official/cells/parallel.py`.

No second parallel implementation.

### `execute_benchmark`

The `stress_cells is not None` branch now calls:

```text
run_stress_benchmark(..., workers=workers, stop_after_cell=stop_after_cell, benchmark_mode=benchmark_mode)
```

Official mode is unchanged: official runs do not use `stress_cells`.

## Unchanged

- Frozen official config, PolicyPack, epsilon, seeds, profiles, metrics, M8, B3
- `--stress-cells N` cell count and development seed/profile construction
- Parallel group runner, memory gate, fingerprint semantics
