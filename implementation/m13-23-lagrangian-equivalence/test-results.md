# M13.23 Test Results

## Required

```text
pytest -q tests/allocation/test_m13_12_performance.py
.............                                                            [100%]
13 passed in 3.39s
```

```text
pytest -q
318 passed in 1696.09s (0:28:16)
```

Cloud baseline was 317 passed / 1 failed (`test_lagrangian_allocate_reference_vs_optimized_direct`). After the fix: **318 passed, 0 failed**.

## Golden allocator regression

`test_golden_fixtures_match` — full `AllocationResult.to_dict()` vs frozen JSON.

| Fixture | allocation_hash | mode | duality_gap | selected | shadow_prices |
|---------|-----------------|------|-------------|----------|---------------|
| `single_high_enrv` | `a77dd9c5…ec0416` | LAGRANGIAN | `0.9999970005758895` | A03 `cand_opp_1_A03` | `{}` |
| `contact_binding` | `df6882e3…73a997` | LAGRANGIAN | `0.9999960007678526` | A05 both opps | `{}` |
| `official_epsilon` | `21ac4d11…71526b` | LAGRANGIAN | `0.9999970005758895` | A04 `cand_opp_off_A04` | `{}` |

**No golden fingerprint changed.**

## Direct reference vs optimized

`test_lagrangian_allocate_reference_vs_optimized_direct` — PASS

- mode, duality_gap, lambdas, relaxed `candidate_id`s, primal assignments, shadow prices identical
- `λ_contact = 1042.3822139727447` on both paths (correct `contact_v = 2`)

Id-cache poison (`_USAGE_CACHE[id(pc)] = {message_capacity: 1}` on one `cust_0` A03) no longer splits 521.19 vs 1042.38.

## Official-scale equivalence

Seven representative cells in `test_official_scale_representative_equivalence` — PASS (`allocation_hash` + full dict).
