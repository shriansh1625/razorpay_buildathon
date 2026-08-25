# M13.18 Execution Bridge Impact

| Component | Performance impact |
|-----------|-------------------|
| `identity_bridge.py` | Was O(selections × opportunities) per cycle — **fixed in M13.21** with cycle-local index |
| `simulated_v1` approver | O(1) per authorization — negligible vs M6/M7 (~7 s M10 total) |
| M11/M12 wiring | Adds ~7.5 s/cell (101k execution attempts, ~84% auth rate) — **required semantics** |
| Baseline pipeline | Re-runs M6/M7 per selected decision — pre-existing; amplified now that execution is live |

Tests passed: `test_m13_18_execution_bridge.py` (13 tests).

**Verdict:** M13.18 functionally required; only identity scan pattern was an avoidable inefficiency.
