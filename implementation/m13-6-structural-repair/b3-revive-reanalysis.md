# B3 vs REVIVE Re-analysis

**Classification (official scale):** COLLAPSED

**Rationale:** avg_diff_rate=0.000, strong=0, acceptable=0, weak=0, scarce_avg_diff=0.00

## Sample cells (500 opps)

| seed | profile | differing | b3_enrv | revive_enrv | b3_retry | revive_retry | deferred |
|------|---------|-----------|---------|-------------|----------|--------------|----------|
| 1 | BALANCED | 0 | 1502372 | 1502372 | 50/50 | 50/50 | 196 |
| 1 | HIGH_NATURAL | 0 | 1667648 | 1667648 | 50/50 | 50/50 | 201 |
| 1 | SCARCE | 0 | 764146 | 764146 | 20/20 | 20/20 | 237 |
| 1 | ABUNDANT | 0 | 2573662 | 2573662 | 172/250 | 172/250 | 33 |
| 1 | HOSTILE | 0 | 1299938 | 1299938 | 41/41 | 41/41 | 207 |
| 1 | DEGRADED | 0 | 1502372 | 1502372 | 50/50 | 50/50 | 196 |
| 2 | BALANCED | 0 | 1661174 | 1661174 | 50/50 | 50/50 | 205 |
| 2 | HIGH_NATURAL | 0 | 1642512 | 1642512 | 50/50 | 50/50 | 209 |
| 2 | SCARCE | 0 | 767967 | 767967 | 20/20 | 20/20 | 241 |
| 2 | ABUNDANT | 0 | 2754993 | 2754993 | 171/250 | 171/250 | 23 |
| 2 | HOSTILE | 0 | 1423373 | 1423373 | 41/41 | 41/41 | 216 |
| 2 | DEGRADED | 0 | 1661174 | 1661174 | 50/50 | 50/50 | 205 |

## Why B3 and REVIVE match

At official scale (500 opps, 30-day window, profile capacities wired):
- Greedy B3 saturates retry capacity with the same highest-ENRV actions.
- Portfolio allocator selects identical actions; REVIVE defers lower-value opps but does not swap winners under observed shadow prices.
- Scale sensitivity (21-day window, variable customer counts) shows differing allocations at 100–750 opps — differentiation is config-dependent, not absent globally.

Same world, same M7 valuations, profile-adjusted capacities.
No M8 objective changes.
