# Single vs Parallel

M13.20 validated workers=1/2/3 semantic equality on representative matrix.

For full 600-cell official run:

- workers=2: recommended balance (Run 4 used this)
- workers=3: semantically safe but CPU contention on 8 GB machine may reduce speedup

Parallelization does not explain 49–57 h ETA — **per-cell algorithmic cost** does.

See `implementation/m13-20-three-worker-validation/validation-report.json`.
