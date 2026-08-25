# M13.9 — Final Pre-Official Benchmark Integrity Gate

**Milestone:** M13.9 — Freeze verification only (read-only audit)  
**Date:** 2026-08-23  
**Official benchmark executed:** NO  
**Code modified:** NO  

---

## Executive summary

M13.8 governance recommended **READY TO FREEZE** with a 21-day / 500 / 100 official configuration. This audit verifies whether sealing that configuration today would produce a fair, reproducible Track 03 benchmark.

**Result:** The **architecture and integrity controls are sound**, but the **runtime official configuration does not yet match the proposed freeze package**, and **no ADR or PolicyPack item is formally ACCEPTED/SEALED in code**. Official execution remains correctly blocked.

# FREEZE BLOCKED

---

## 1. Configuration consistency

| Field | M13.8 proposed | Current `official_benchmark_config()` | Match |
|-------|----------------|--------------------------------------|-------|
| `simulation_window_days` | **21** | **30** (`_base_generator_config`) | **NO** |
| `opportunity_count` | 500 | 500 | YES |
| `customer_count` | 100 | 100 | YES |
| `cycle_interval_minutes` | 15 | 15 | YES |
| `seed_set` | 1..20 | 1..20 (`OFFICIAL_SEED_SET`) | YES |
| `profile_set` | all 6 | all 6 (`OFFICIAL_PROFILE_SET`) | YES |
| `PolicyPack.version` | `pol_m13_official_v1` | `pol_m1_draft` (runtime default) | **NO** |
| `PolicyPack.status` | SEALED | DRAFT | **NO** |
| `epsilon_paise` | 100 | **0** | **NO** |
| `B1_schedule_version` | `adr-013_v1` | `adr-013_draft_v1` | **NO** |
| `predictor_version` | `strat_m7_benchmark_v1` | `0.7.0-m7:strat_m7_dev` | **NO** |
| `approver_model_version` | `simulated_v1` | `simulated_v1_provisional` | **NO** |
| `allocator_version` | `0.8.0-m8` | `0.8.0-m8` | YES |
| `metric_version` | `0.12.0-m12` | `0.12.0-m12` | YES |
| `llm_mode` | LLM_OFF | LLM_OFF | YES |
| `allocator_mode` | LAGRANGIAN | LAGRANGIAN | YES |

**Blocker:** There is **not one canonical frozen representation** in code yet. M13.8 proposed config exists only in governance documents; `revive/benchmark/official/config.py` still encodes the superseded 30-day proposal.

---

## 2. Epsilon check (ADR-011)

**M13.8 recommendation:** ε = 100 paise (₹1), aligned with `docs/11` §5.3 noise-filter semantics.

| Check | Result |
|-------|--------|
| Centralized in PolicyPack | YES — allocator/baselines use `policy_pack.epsilon_paise` |
| Alternate hardcoded ε in decision path | **CAUTION** — `ValuationConfig.epsilon_paise_provisional=0` in `revive/recovery/valuation/config.py` (not in PolicyPack hash; used in valuation metadata only, not allocator threshold) |
| Runtime value | **0** (`default_draft_policy_pack`) — not 100 |
| In configuration hash | YES — `official_benchmark_config_hash` includes `epsilon` |
| Changing ε changes hash | VERIFIED |
| Selected from REVIVE performance | NO — M13.8 sweep shows identical B3/REVIVE differing at ε=0 vs ε=100 on 21d config |

**ADR-011 status:** DRAFT — **not ACCEPTED**.

---

## 3. PolicyPack check

**Before sealing (current state):**

| Field | Value | Source | Affects economics |
|-------|-------|--------|-------------------|
| `version` | `pol_m1_draft` | M1 scaffold | Hash identity |
| `status` | DRAFT | `default_draft_policy_pack()` | Blocks official run |
| `epsilon_paise` | 0 | OQ-01 provisional | Candidate eligibility, allocation |
| `gate_sequence` | G1–G12 | docs/13 | Authorization gates |
| `profile` | BALANCED | Pack metadata only | Not benchmark profile matrix |
| `metadata` | `{source: M1-foundation, frozen: false}` | Development | — |

**Proposed at freeze:** `pol_m13_official_v1`, SEALED, ε=100 — **not implemented in codebase**.

No undocumented defaults silently enter official config **once sealed**, but **sealing has not occurred**.

---

## 4. B1 check

- Code: `B1_SCHEDULE_VERSION = "adr-013_draft_v1"`
- Schedule: `revive/benchmark/config.py` `B1_RETRY_SCHEDULE` matches `implementation/adr-013-b1-retry-schedule.md`
- Per-class delays are published, invented, credible status-quo — not weakened for REVIVE
- **ADR-013 status:** DRAFT — not ACCEPTED as `adr-013_v1`

---

## 5. Predictor freeze

| Check | Result |
|-------|--------|
| Version in code | `strat_m7_dev` |
| Oracle features | None — `features.py` uses observable proxies only |
| Latent generator variables | Not used in valuation path |
| Future leakage | No outcome oracle in M7 path |
| Official outcome calibration | Not used |
| Deterministic | Yes — seed-driven priors |
| In config hash | YES (`predictor_version`) |

**Recommendation from M13.8:** FREEZE as `strat_m7_benchmark_v1` — **not applied in code**.

---

## 6. Approver freeze

- Version in code: `simulated_v1_provisional`
- `revive/policy/authorize.py`: gate/stopping evaluation on decision context — **no policy_id / B3 / REVIVE branches**
- Deterministic, policy-driven (`PolicyPack` + `PolicyRules`)
- No oracle access in authorization path
- **Not frozen** — provisional suffix remains

---

## 7. Seed freeze

```text
OFFICIAL_SEED_SET = tuple(range(1, 21))  # seeds 1..20
```

| Check | Result |
|-------|--------|
| Fixed sequence | YES |
| No duplicates | YES |
| Same for all policies | YES (runner uses same `config.seed_set`) |
| Selected post-hoc | NO evidence of cherry-picking |
| Count ≥ documented 20 | YES |

---

## 8. World fairness

Verified in `revive/benchmark/official/runner.py`:

```text
World W(seed, profile)  → generate_shared_world once per cell
├── B0  → clone_shared_world → run
├── B1  → clone_shared_world → run
├── B2  → clone_shared_world → run
├── B3  → clone_shared_world → run
└── REVIVE → clone_shared_world → run
```

- `world_cache` keyed by `(seed, profile)` — one generation per cell
- Policies do **not** regenerate independent worlds
- `clone_shared_world` deep-copies observable world; oracle partition is shared read-only truth
- Calibration integrity: `dataset_hash_identical`, `clone_preserves_opportunity_count` — PASS

---

## 9. Oracle fairness

`revive/simulation/oracle/resolve.py`:

- `resolve_outcome(partition, opportunity_id, action_code, ...)` — **no policy parameter**
- Static integrity: `assert_decision_path_does_not_import_oracle()` — PASS
- Baseline modules oracle isolation — PASS

**No policy-specific outcome branches found** — not a freeze blocker.

---

## 10. Portfolio-thesis validity (21-day choice)

Reconfirmed from M13.7/M13.8 (outcome-independent):

| Metric | 30-day (code today) | 21-day (M13.8 proposed) |
|--------|---------------------|-------------------------|
| Portfolio conflicts (mean) | 0.0 | 15,635 |
| B3/REVIVE differing (mean) | 0.2 | 37.4 |
| Multi-resource binding | retry-only | retry, message, human, contact |

**Justification for 21 days:** Documented recovery windows, DS-4 scarcity, portfolio competition — **not** because REVIVE wins.

**Blocker:** 21-day horizon is **recommended but not wired** into `official_benchmark_config()`.

---

## 11. Track 03 coverage

Generator (`docs/19` failure mix) includes all five risk classes:

- `PAYMENT_FAILURE`, `CHECKOUT_ABANDONMENT`, `SUBSCRIPTION_FAILURE`, `RECEIVABLE_OVERDUE`, `MANDATE_HEALTH`

All six profiles exercised in official matrix design. Aggregate benchmark coverage sufficient per specification.

---

## 12. Safety coverage

Official pipeline includes:

- 12 gates (`PolicyPack.gate_sequence` G1–G12) via `evaluate_gates`
- Stopping rules via `evaluate_stopping_rules`
- `REQUIRE_APPROVAL` path / authorization states (STALE, EXPIRED, BLOCKED)
- Capacity exhaustion → DEFERRED in allocator
- Contact limits (per-customer `contact_allowance`)
- Idempotency / execution store in M11 path
- HOSTILE profile for adversarial injection
- Falsification F-1…F-6 pre-registered in `falsification.py`

Sufficient for Track 03 judging bar **when benchmark runs** — not a freeze blocker.

---

## 13. Measurement integrity

| Layer | Role | Oracle access |
|-------|------|---------------|
| M7 valuation | Counterfactual ENRV | None |
| M11 execution | Bounded adapter outcomes | Oracle at execution boundary only |
| M12 measurement | Attribution + M-10 | Uses execution results, not M7 predictions as outcomes |

`MEASUREMENT_VERSION = 0.12.0-m12` — frozen string in official config hash.

---

## 14. Benchmark metric lock

- Primary: **M-10 Incremental Net Recovered Revenue** (`m10_incremental_net_paise` in `metrics.py`, `aggregate.py`)
- Falsification F-1 uses paired M-10 vs baselines
- No additional metrics added to favor REVIVE in this audit

---

## 15. Reproducibility

| Component | Status |
|-----------|--------|
| Labeled PRNG streams | YES (`revive/rng/streams.py`) |
| `generator_version` in hash | YES |
| `config_hash` deterministic | YES |
| LLM in official mode | OFF |
| Network dependency | None in benchmark path |
| Byte-identical reproduction | `reproduce_benchmark()` exists (development validated) |

---

## 16. Configuration hash (without running benchmark)

**Current code state** (draft pack, 30-day):

```text
hash_prefix: 4ae002a4854c707f
```

**Simulated proposed M13.8 package** (21-day, SEALED, ε=100, frozen versions):

```text
hash_prefix: 23280c719e81cd7f
```

Hashes **differ** — confirms proposed freeze would change official identity.

**Hash sensitivity verified** for: epsilon, horizon, predictor, approver, B1 schedule — all change hash.

---

## 17. Official execution lock

```text
execute_benchmark(mode=BenchmarkMode.OFFICIAL)
→ blocked=True, runs=0
```

`check_freeze_prerequisites()` returns **7 blockers** on current config:

1. ADR-011 not ACCEPTED (PolicyPack not SEALED)
2. PolicyPack status=DRAFT
3. ADR-013 B1 schedule DRAFT
4. ADR-012 scale not ACCEPTED
5. Approver provisional
6. Generator not formally frozen
7. Predictor strat_m7_dev

**Guard remains enabled** — verified.

---

## 18. No code changes after freeze (documented rule)

Once the official configuration is sealed and execution begins:

# CODE + CONFIGURATION ARE FROZEN.

Any change to benchmark-sensitive components requires:

# NEW BENCHMARK VERSION.

(recorded in `docs/20-benchmark.md` RR-BENCH-008 spirit; enforced via `config_hash` + genesis artefact)

---

## 19. Final freeze checklist

```text
[ ] ADR-011 accepted          — DRAFT; ε=0 in runtime
[ ] ADR-012 accepted          — RECOMMENDATION only; code still 30-day
[ ] ADR-013 accepted          — DRAFT (adr-013_draft_v1)
[ ] PolicyPack sealed         — DRAFT (pol_m1_draft)
[ ] Predictor frozen          — strat_m7_dev (not strat_m7_benchmark_v1)
[ ] Approver frozen           — simulated_v1_provisional
[ ] Generator frozen          — ADR-012 pending; horizon mismatch
[ ] Seeds frozen              — [x] 1..20 defined in OFFICIAL_SEED_SET
[ ] Metrics frozen            — [x] MEASUREMENT_VERSION in hash
[ ] Configuration hash generated — [x] computed (proposed ≠ current)
[ ] World-sharing verified    — [x] one world per seed/profile
[ ] Oracle isolation verified — [x] static + resolve_outcome neutral
[ ] No strategy-specific outcomes — [x]
[ ] No future leakage in M7     — [x]
[ ] 21-day horizon justified    — [x] evidence (M13.8); [ ] wired in code
[ ] Track 03 scenario coverage  — [x]
[ ] Safety scenarios verified   — [x] gates/stopping in pipeline
[ ] Reproducibility verified    — [x]
[ ] Official benchmark gate enforced — [x] blocked=True
```

---

## 20. Exact blockers (do not auto-fix)

1. **Official config code ≠ M13.8 proposed config** — horizon 30 vs 21; must align code with accepted ADR-012 before seal.
2. **ADR-011 not ACCEPTED** — ε remains 0 at runtime; recommend 100 paise pending human acceptance.
3. **ADR-012 not ACCEPTED** — recommendation document only (`implementation/adr-012-benchmark-scale.md`).
4. **ADR-013 not ACCEPTED** — B1 schedule version still `adr-013_draft_v1`.
5. **PolicyPack not SEALED** — no `pol_m13_official_v1` factory; `default_draft_policy_pack()` used at runtime.
6. **Predictor not frozen** — `strat_m7_dev` in `STRATEGY_VERSION`.
7. **Approver not frozen** — `simulated_v1_provisional`.
8. **Human acceptance pending** — M13.8 governance complete but ADRs are recommendations, not ACCEPTED status.

---

## 21. Proposed configuration for sealing (after blockers resolved)

When blockers are cleared, seal **exactly**:

```text
benchmark_version:        0.13.0-m13
generator_version:        0.2.0-m2
horizon_days:             21
opportunity_count:        500
customer_count:           100
cycle_length_minutes:     15
profiles:                 BALANCED, HIGH_NATURAL, SCARCE, ABUNDANT, HOSTILE, DEGRADED
seed_selection:           1..20 fixed
PolicyPack:               pol_m13_official_v1 (SEALED)
epsilon_paise:            100
B1_schedule:              adr-013_v1
predictor:                0.7.0-m7:strat_m7_benchmark_v1
allocator_version:        0.8.0-m8
approver:                 simulated_v1
metrics_version:          0.12.0-m12
allocator_mode:           LAGRANGIAN
llm_mode:                 LLM_OFF
policy_set:               B0, B1, B2, B3, REVIVE
```

---

## 22. What is ready (integrity, not freeze)

- Benchmark architecture fairly compares policies on identical worlds
- Oracle is policy-neutral
- Official execution cannot run until freeze completes
- 21-day configuration is **evidence-backed** for portfolio thesis testing
- Seed set and metric definitions are suitable
- No tuning for REVIVE advantage detected in this audit

---

# FREEZE BLOCKED

Human acceptance and code alignment with the M13.8 proposed package are required before sealing. Do **not** run `revive benchmark --mode official` until this checklist is complete.

**STOP** — await explicit human review and freeze implementation (separate milestone).
