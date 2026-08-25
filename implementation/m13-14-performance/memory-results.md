# M13.14 Memory Results

**Label:** DEVELOPMENT_ONLY

| Metric | M13.13 | M13.14 |
|--------|--------|--------|
| Peak RSS (stress cell) | ~529 MB | ~551 MB |
| Material growth across groups | No | No (cycle cache scoped per cycle) |

CycleViewCache adds ephemeral per-cycle indexes; freed each `begin_cycle()`. No global mutable caches.

Memory remains safe on 8 GB hardware.
