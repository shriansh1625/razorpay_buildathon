# Proposed Official Configuration (NOT EXECUTED)

Immutable fields proposed for sealing:

```text
benchmark_version: 0.13.0-m13
generator_version: 0.2.0-m2
horizon_days: 21
opportunity_count: 500
customer_count: 100
cycle_length_minutes: 15
profiles: ['BALANCED', 'HIGH_NATURAL', 'SCARCE', 'ABUNDANT', 'HOSTILE', 'DEGRADED']
seed_selection: 1..20 fixed
PolicyPack_version: pol_m13_official_v1 (proposed)
PolicyPack_status: SEALED (at freeze)
epsilon_paise: 100 (proposed, ADR-011)
B1_schedule: adr-013_draft_v1 → adr-013_v1
predictor_version: 0.7.0-m7:strat_m7_dev → strat_m7_benchmark_v1
allocator_version: 0.8.0-m8
approver_version: simulated_v1_provisional → simulated_v1
metrics_version: 0.12.0-m12
allocator_mode: LAGRANGIAN
llm_mode: LLM_OFF
policy_set: B0, B1, B2, B3, REVIVE
```

**Rejected:** Configuration A (30-day window) — fails portfolio thesis validity.
