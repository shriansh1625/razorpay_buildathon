# M13.12 Semantic Regression

## Golden fixtures

`tests/allocation/golden/`:

- `single_high_enrv.json`
- `contact_binding.json`
- `official_epsilon.json`

Each stores input hash + full `AllocationResult.to_dict()`.

## Reference comparison

`revive/allocation/lagrangian_reference.py` — frozen pre-M13.12 implementation.

## Test coverage (`tests/allocation/test_m13_12_performance.py`)

| Test | Result |
|------|--------|
| Golden fixtures | PASS |
| Reference vs optimized `allocate_portfolio` | PASS (allocation_hash + to_dict) |
| Official-scale 7 representative cells | PASS |
| Direct lagrangian + primal equivalence | PASS |
| Performance smoke (lagrangian worst cycle) | PASS |

## Equivalence surface

- Selected / deferred / no-action outcomes
- `candidate_id`, `action_code`, `enrv_paise`, `reduced_value_paise`
- `binding_resource`, `reason_code`, `explanation`
- `allocation_hash`
- `shadow_prices`, `allocator_mode`, `duality_gap`
- Resource usage in `AllocationResult`

## Full suite

**260 tests passing** (13 new M13.12 tests)
