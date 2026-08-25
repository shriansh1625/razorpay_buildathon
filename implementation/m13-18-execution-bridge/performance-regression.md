# Performance Regression (M13.18)

## Scope

No intentional performance optimization in M13.18.

## Changes

- Natural-key lookup per baseline selection (O(1) index)
- simulated_v1 draw per authorization candidate (O(1) hash)

## Test suite

`tests/benchmark/test_m13_14_performance.py` — 29 passed (including cycle-cache equivalence after profiling sync)

## Official benchmark

Not rerun — wall-time impact deferred to corrected official run.

Expected: negligible vs prior broken run (prior run already spent full cycle time with zero useful execution for baselines; REVIVE spent ~570s/cell on auth that never executed).
