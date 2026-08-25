# M13.23 Semantic Equivalence

## Direct Lagrangian (failing cloud test)

Fixture: 8 opportunities, `cust_{i%3}`, A03 + A00, epsilon=100, default capacities.

| Field | Reference | Optimized | Match |
|-------|-----------|-----------|-------|
| mode | `LAGRANGIAN` | `LAGRANGIAN` | yes |
| duality_gap | `None` (contact dual remains positive) | `None` | yes |
| `λ_contact` | `1042.3822139727447` | `1042.3822139727447` | yes |
| other λ | 0 | 0 | yes |
| relaxed picks | all A03 | all A03 | yes |
| primal assignments | identical `to_dict()` | identical | yes |
| shadow prices | identical | identical | yes |

Poisoned `id(pc)` cache entry no longer desynchronizes the two paths.

## Golden fixtures (hashes unchanged)

| Fixture | `allocation_hash` | mode | duality_gap | shadow_prices |
|---------|-------------------|------|-------------|---------------|
| `single_high_enrv` | `a77dd9c504e773e876e99f0b222cc748f41836783d8468e77b1d23ba81ec0416` | `LAGRANGIAN` | `0.9999970005758895` | `{}` |
| `contact_binding` | `df6882e36cb78e62b852283703add95e6dd1c55e44911dbd57f4df536273a997` | `LAGRANGIAN` | `0.9999960007678526` | `{}` |
| `official_epsilon` | `21ac4d11d8fb177f5d59619f9b22728c501672b4d76e384feb7840c15771526b` | `LAGRANGIAN` | `0.9999970005758895` | `{}` |

`test_golden_fixtures_match` compares full `AllocationResult.to_dict()` to these files. **No golden fingerprint changed.**

Selected candidates / tie-break keys are unchanged (same `candidate_id`, `action_code`, `reason_code`, `reduced_value_paise`).

## Official-scale representative cells

`test_official_scale_representative_equivalence` (seeds/profiles/cycles from M13.12) compares `allocation_hash` and full result dicts. All passed after the fix.

## Not changed

Frozen official experiment: 21d, 500 opps, 100 customers, PolicyPack `pol_m13_official_v1`, ε=100, B1 `adr-013_v1`, B3, k_max=40, step_scale=50.
