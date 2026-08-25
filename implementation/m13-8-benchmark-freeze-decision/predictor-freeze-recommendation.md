# Predictor Freeze Recommendation

Current: `strat_m7_dev` (`revive/recovery/valuation/config.py`)

| Check | Status |
|-------|--------|
| Oracle features | None — observable inputs only |
| Future leakage | None in valuation path |
| Deterministic | Yes — seed-driven generator + fixed strategy |
| Dev vs official separation | Official uses frozen version string in config_hash |

**Recommendation:** FREEZE as `strat_m7_benchmark_v1` at benchmark seal.
Record `VALUATION_VERSION:STRATEGY_VERSION` in official config.
