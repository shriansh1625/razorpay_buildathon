# Baseline Identity — Fix (M13.18)

## Module

`revive/recovery/sentinel/identity_bridge.py`

## Mechanism

1. Derive sentinel canonical `natural_key` from observable world opportunity + linked refs (same functions as M4 `detect()`).
2. Index sentinel opportunities by `natural_key` (unique; raises on duplicate).
3. Resolve baseline `decision.opportunity_id` → world opp → natural_key → sentinel `DetectedOpportunity`.
4. World mutations (M11/M12) continue using generator `opportunity_id` (`bd.opportunity_id` / `world_opp_id`).

## Integration point

`revive/benchmark/official/baseline_pipeline.py` — replaced `opp_by_id.get(bd.opportunity_id)` with `resolve_sentinel_for_world_opportunity_id(...)`.

## Invariant

`assert_baseline_identity_invariant()` — strict mode: exactly one sentinel match or diagnostic error.

## Not used

- Fuzzy ID matching
- Position-based matching
- Official-mode special cases
