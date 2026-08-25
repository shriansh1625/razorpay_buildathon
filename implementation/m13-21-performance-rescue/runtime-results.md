# M13.21 Runtime Results

| Case | Policy | Wall (s) |
|------|--------|----------|
| A | seed=2 BALANCED REVIVE | 514 (profile loop) |
| B | seed=1 BALANCED REVIVE | 690 (Run 4 telemetry) |
| C | seed=1 HIGH_NATURAL REVIVE | 697 (Run 4 telemetry) |
| D | seed=1 SCARCE REVIVE | 447 (Run 4 telemetry) |
| B1 seed=1 BALANCED | baseline | 397 |
| B2 seed=1 BALANCED | baseline | 435 |
| B3 seed=1 BALANCED | baseline | 97 |

Projected 600-cell @ workers=2 using Run 4 seed=1 mix: **~45–55 h** (consistent with observed ETA).

M13.14 projection (~20 h) assumed 480 s REVIVE + 31 s baseline median with **zero execution overhead**.
