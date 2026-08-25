# M13.21 Regression Analysis

## Question

Why M13.14 ~480 s/cell but Run 4 groups ~18–30 min and ETA ~49–57 h?

## Answer

1. **480 s M13.14 cell had no M11/M12 work** (broken execution bridge).
2. **Live cells add ~7 s M11/M12** — small vs M6/M7 (~307 s combined).
3. **B1/B2 baselines now execute** — ~400 s each for seed=1 BALANCED (M6/M7 repeated per selection in baseline path).
4. **Group time = sum of 5 policies** — seed=1 BALANCED ≈ 27 min measured.
5. **600 cells / 2 workers / ~27 min per group average** ⇒ tens of hours, not ~19 h.

## Fixed inefficiency

Per-assignment O(N) `resolve_world_opportunity_id_by_natural_key` scans — removed via cycle-local index.

## Not fixed (by design)

M6/M7 dominance; baseline per-decision M6/M7 recompute; genuine execution/audit persistence.
