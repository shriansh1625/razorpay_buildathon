# M13.24 Root Cause

## Observation

```text
revive benchmark --mode development --workers 8 --stress-cells 10 --output artefacts/cloud-test-w8
```

CLI accepted `--workers 8`. Completed output:

```text
mode=DEVELOPMENT
workers=1
```

No `parallel workers=8 groups=...` line.

## Control flow

```text
cli.py
  args.workers → execute_benchmark(..., workers=args.workers, stress_cells=args.stress_cells)
    runner.execute_benchmark
      if stress_cells is not None:          # TRUE for this command
          run_stress_benchmark(...)         # workers NOT passed
      else:
          run_cell_benchmark(..., workers=workers)
            if workers > 1:
                run_cell_benchmark_parallel(...)   # emits parallel workers=N
```

Exact sequential trap:

1. `revive/cli.py` — `--workers` default 1, parsed as 8, passed into `execute_benchmark`.
2. `revive/benchmark/official/runner.py` lines 120–131 — **`if stress_cells is not None`** calls `run_stress_benchmark` with config, pack, hash, cells_root, cell_count, progress. **`workers` is omitted.**
3. `revive/benchmark/official/cells/runner.py` `run_stress_benchmark` — called `run_cell_benchmark(..., max_cells=cell_count)` with **`workers` defaulting to 1**.
4. `run_cell_benchmark` — `if workers > 1` is false, so the sequential loop runs.
5. Sequential metadata sets `"workers": 1`.
6. `execute_benchmark` builds:

   ```python
   metadata={
       "workers": workers,          # 8 from CLI
       **execution_metadata,        # overwrites with cell_result.metadata workers=1
   }
   ```

   CLI prints `result.metadata.get("workers", 1)` → **1**.

## What this is not

- Official-mode worker clamp
- `validate_workers` rejecting 8
- A change to stress-cell planning (`max_cells=N` still limits workload)
- PolicyPack / epsilon / seed / profile semantics
