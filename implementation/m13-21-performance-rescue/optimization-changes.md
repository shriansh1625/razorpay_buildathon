# M13.21 Optimization Changes

1. **`index_world_opportunities_by_natural_key(view)`** — built once per REVIVE cycle; O(N) not O(N×selections).
2. **`PolicyRules` cached** on `ReviveRunState.rules()` and `BaselineRunState.rules()`.
3. **`resolve_world_opportunity_id_by_natural_key(..., world_index=)`** — optional index for backward compatibility.

No changes to: horizon, scale, PolicyPack, ε, M8 algorithm, seeds, profiles, approval semantics.
