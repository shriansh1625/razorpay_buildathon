# M13.23 Fix

## Change 1 — `usage_dict` cache key

**File:** `revive/allocation/resources.py`

**Before:** `_USAGE_CACHE[id(pc)]`  
**After:** `_USAGE_CACHE[pc.usage]` (immutable usage tuple)

Same usage vector → same mapping. Distinct candidates with the same template share the cache safely. GC id reuse cannot attach a stale mapping to a new object.

## Change 2 — isolate each Lagrangian call

**Files:** `revive/allocation/lagrangian.py`, `revive/allocation/lagrangian_reference.py`

`clear_usage_cache()` at the start of `lagrangian_allocate` (allocate_portfolio already cleared per public call; direct tests did not).

## Change 3 — optimized usage accounting matches reference

**File:** `revive/allocation/lagrangian.py`

`_reduced_value_paise`, `_accumulate_usage`, and `_contact_violation_from_picks` now read `usage_dict(pc)` (dict last-wins per candidate), matching `lagrangian_reference.py`.

No change to:

- subgradient definition (contact still uses per-customer excess)
- step rule, k_max, iteration_budget, duality_tolerance
- objective, constraints, tie-break, primal recovery order
- PolicyPack, epsilon, B3, official benchmark config
- reference algorithm (only cache isolation)

## Semantics preserved

Correct `contact_v` for the failing fixture is **2**. After the fix both paths return `λ_contact = 1042.3822139727447` even if `_USAGE_CACHE` is pre-poisoned with an `id(pc)` entry.
