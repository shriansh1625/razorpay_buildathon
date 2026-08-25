# M13.15 Worker Model

**Label:** DEVELOPMENT / OFFICIAL infrastructure only

## Work unit

One worker executes one **(seed, profile)** group:

```
(seed=1, BALANCED)
  ├─ generate ONE shared world
  ├─ B0  (clone world)
  ├─ B1
  ├─ B2
  ├─ B3
  └─ REVIVE
```

Policies within a group run **sequentially** on independent world clones — same semantics as M13.11 sequential runner.

## Parallelism boundary

| Parallel OK | NOT parallel |
|-------------|--------------|
| `(seed=1, BALANCED)` vs `(seed=1, HIGH_NATURAL)` | B0 vs REVIVE within same group |
| `(seed=2, SCARCE)` vs `(seed=3, HOSTILE)` | Shared world across policies |

## Implementation

- `plan_benchmark_groups()` — partition planned cells
- `run_seed_profile_group()` — process worker (`cells/parallel_worker.py`)
- `run_cell_benchmark_parallel()` — orchestrator (`cells/parallel.py`)

Main process:

1. Skips fully valid groups (resume)
2. Submits pending groups to `ProcessPoolExecutor`
3. Updates checkpoint after each group completes
4. Aggregates from store in canonical cell order
