# M13.21 Regression Root Cause

**Label:** DEVELOPMENT_FORENSIC_ONLY — NOT OFFICIAL BENCHMARK EVIDENCE

## Measured facts

| Source | seed=2 BALANCED REVIVE | M11/M12 |
|--------|------------------------|---------|
| M13.14 optimized profile | 536 s | **0 s** (zero execution) |
| M13.21 post-rescue profile | 514 s (loop) | 4.6 s + 2.9 s |
| Run 4 partial (seed=1 BALANCED) | 690 s telemetry | live execution |

## Root causes (ordered)

1. **Apples-to-oranges baseline** — M13.14 ~480 s headline measured cells with **no successful M11/M12 execution** (all `intervention_count=0` in golden). Post-M13.18 cells do real work by design.

2. **Dominant stages unchanged** — M6+M7 ≈ 60% in both eras. Not an M8 regression.

3. **Group duration math** — One seed/profile group = 5 policies. seed=1 BALANCED ≈ 27 min (B0 28s + B1 397s + B2 435s + B3 97s + REVIVE 690s). Groups ~18–30 min are **expected**, not an anomaly.

4. **ETA ~49–57 h** — 600 cells × ~measured average cell time ÷ 2 workers ⇒ tens of hours. M13.13/M13.14 ~19–20 h projection assumed 480 s REVIVE + ~31 s baseline **without live baseline execution**.

5. **Implementation bug (fixed)** — `resolve_world_opportunity_id_by_natural_key` scanned all opportunities per authorization (~121k×/cell). Replaced with cycle-local index.

## Official Run 4

Stopped. Marked `PARTIAL_NON_EVIDENCE` at `artefacts/benchmark/official-run4/PARTIAL_NON_EVIDENCE.json`. Do not resume.
