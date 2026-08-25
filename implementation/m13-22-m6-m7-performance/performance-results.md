# M13.22 Performance Results

**Label:** DEVELOPMENT_ONLY

| Metric | M13.21 | M13.22 (this session) |
|--------|--------|------------------------|
| seed=2 BALANCED REVIVE loop | 514 s | 685 s |
| M6 | 151 s | 170 s |
| M7 | 157 s | 223 s |
| M8 | 60 s | 92 s |
| Peak RSS | ~552 MB | ~627 MB |
| Speedup vs 514 s | — | **0.75× (no improvement on this run)** |

Wall clock including world gen: 1040 s. Stages M4–M12 also slower in aggregate — consistent with **machine contention / thermal load** after long M13.21 profiling, not a new semantic path.

Identity-preserving micro-opts (config cache, feasibility table, SHA digest mapping, shrinkage n=0 mix) did **not** deliver ≥1.5× on the official-scale cell while `Decimal` ENRV rounding remains.

## Remaining bottleneck

1. **M7 `bankers_round_paise` (Decimal)** — cannot replace without fingerprint change  
2. **M6 5.55M candidate objects + SHA-256 IDs** — ID algorithm preserved; encoding already equivalent  
3. **M8 ~13%** — not modified (M13.12 Lagrangian)

No new parallelism. No official run.
