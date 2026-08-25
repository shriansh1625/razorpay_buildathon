# Six-Profile Validation (seed=1, 15 cycles)

**Label:** DEVELOPMENT_ONLY — not a full-cell official matrix.

| Profile | M4 opps (cyc0) | M6 hash | M7 hash | 15-cycle metrics | interventions |
|---------|----------------|---------|---------|------------------|---------------|
| BALANCED | 209 | `9d13749d…` | `65d6e346…` | `2f41c2f2…` | 770 |
| HIGH_NATURAL | 221 | `8e408bfb…` | `59bf5779…` | `5a8c3634…` | 771 |
| SCARCE | 221 | `8e408bfb…` | `59bf5779…` | `4b9b5f73…` | 304 |
| ABUNDANT | 220 | `5114375c…` | `bf30c0bb…` | `2b7403bc…` | 1835 |
| HOSTILE | 224 | `aa6c0762…` | `1e0a72c0…` | `4e2ea660…` | 622 |
| DEGRADED | 209 | `9d13749d…` | `65d6e346…` | `52acc843…` | 770 |

Seed=2 BALANCED 15-cycle M6/M7 hashes **matched pre-optimization capture**.

B1/B2/B3 share `generate_candidates` / `price_candidates`; recovery + allocation tests passed. No baseline-only slowdown introduced in shared infrastructure.

Raw: `six-profile-fingerprints.json`
