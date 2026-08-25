# CPU Analysis

M6/M7 bound — Python CPU saturated on single REVIVE worker during profile.

Parallel workers=2/3 improve wall time for independent seed/profile groups but **do not reduce per-cell CPU work**. Observed 3-worker full-run slowdown vs 2-worker is CPU contention on ~8 GB / limited cores — consistent with M13.20 memory-safe but contention-limited scaling.

Classification: **(A) CPU saturated** on hot path per worker; parallel speedup limited by core count.
