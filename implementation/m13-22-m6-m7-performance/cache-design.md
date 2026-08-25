# M13.22 Cache Design

## Allowed scopes used

### Cell — `ReviveRunState` / `BaselineRunState`

- `candidate_cfg()` → `CandidateConfig` from sealed PolicyPack metadata
- `valuation_cfg()` → `valuation_config_for_policy(pack)`
- `rules()` → `PolicyRules` (M13.21)

Key: PolicyPack identity. Lifetime: one policy cell. Invalidation: new `ReviveRunState`.

### Immutable / process constants

- `_CLASS_ACTIONS` feasibility table
- Action catalogue resource templates (pre-existing)
- Crockford alphabet for IDs

## Forbidden (not used)

- World cache
- Global candidate cache
- Global predictor cache
- Cross-cycle reuse of outcomes, realized recovery, or post-execution state
