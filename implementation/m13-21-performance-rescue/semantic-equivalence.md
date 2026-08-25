# M13.21 Semantic Equivalence

Post-optimization REVIVE path must produce identical metrics for identical inputs.

- Cycle-local world index preserves deterministic first-match semantics (duplicate natural_key raises `OpportunityIdentityError`).
- `PolicyRules` cache is immutable per sealed PolicyPack — safe.
- Golden `m13_14_seed2_balanced_revive.json` reflects **pre-execution era** (`intervention_count=0`) — not used as regression target post-M13.18.
- Current equivalence surface: repeated `profile_revive_cell(2, BALANCED)` ⇒ identical `cell_result_hash`.

Test: `tests/benchmark/test_m13_21_identity_index.py`
