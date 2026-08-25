# M13.23 Root Cause

## Observed mismatch (cloud full suite)

`tests/allocation/test_m13_12_performance.py::test_lagrangian_allocate_reference_vs_optimized_direct`

| Path | `lambdas["contact_allowance"]` | Implied constant `contact_v` over 40 steps |
|------|--------------------------------|--------------------------------------------|
| `lagrangian_ref` | `521.1911069863723` | **1** |
| `lagrangian_opt` | `1042.3822139727447` | **2** |

Identity: `λ = contact_v × 50 × Σ_{k=1}^{40} (k+1)^{-0.5}` with `Σ ≈ 10.423822139727442`.
Ratio is **exactly 2**.

## Correct contact accounting (M13.12 / docs/10 §5.1)

Contact dual uses **per-customer excess**, not global `Σ usage[contact_allowance]`:

```text
contact_v = Σ_customer max(0, contacts(customer) − contact_allowance_per_customer)
```

Fixture: 8 A03 picks, customers `i % 3`, allowance **2**:

- `cust_0`: 3 contacts → excess 1
- `cust_1`: 3 contacts → excess 1
- `cust_2`: 2 contacts → excess 0
- **`contact_v = 2`** (correct λ = `1042.3822139727447`)

The optimized path computed this correctly on a clean process. The reference path did not on the cloud full suite.

## First divergence

Not the subgradient formula, step rule, k_max, or reduced-value arithmetic.

**First divergence is `usage_dict(pc)` in the reference hot path.**

- Reference `_reduced_value_paise`, `_total_usage`, `_contact_violation` call `usage_dict(pc)`.
- Optimized M13.12 iterated `pc.usage` tuples directly (immune to the cache).

`usage_dict` was keyed by **`id(pc)`**. CPython reuses ids after GC. After earlier tests (official-scale worlds, allocate_portfolio), a stale mapping can attach to a **new** `PricedCandidate`.

## Reproduction (exact cloud numbers)

Pollute one `cust_0` A03 cache entry so contact is missing:

```text
_USAGE_CACHE[id(pc)] = {"message_capacity": 1}
```

Result:

- `cust_0` contacts 3 → 2, excess 1 → 0
- `contact_v` 2 → **1**
- reference λ = `521.1911069863723`
- optimized λ = `1042.3822139727447`

This is **undercounting in reference** (stale cache), not double-counting in optimized.

## What it is not

- Duplicate `contact_allowance` rows on `pc.usage` (fixture usage is `(("contact_allowance", 1), ("message_capacity", 1))`)
- Adding global contact usage into the contact subgradient
- A wrong test assertion
- A change to epsilon, PolicyPack, B3, k_max, step, or tie-break
