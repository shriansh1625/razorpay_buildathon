# PAYVANTA — Implementation Decisions (M0)

**Purpose:** Record implementation choices that are consistent with the spec but not fully prescribed. Deviations from the spec go in `deviations.md` (created when needed) and require ADRs in `docs/31-decision-records.md`.

**Label key:** KNOWN | ASSUMED | PROPOSED | SIMULATED | FUTURE | UNKNOWN

---

## 1. Architectural authority (audit reference)

| Domain | Authoritative document |
|--------|------------------------|
| Product definition | `docs/00-project-charter.md` §3, `docs/02-product-vision.md` |
| Scope | `docs/03-scope-boundaries.md` |
| Requirements | `docs/05-functional-requirements.md` |
| State machine | `docs/34-state-machine.md` |
| Metrics | `docs/37-metrics-dictionary.md` |
| Data model | `docs/17-data-model.md` |
| Guardrails | `docs/13-policy-and-guardrails.md` |
| Stopping rules | `docs/14-stopping-rules.md` |
| Benchmark | `docs/20-benchmark.md`, `docs/21-evaluation.md` |
| Implementation rules | `docs/32-implementation-contract.md` |

---

## 2. P0 numeric defaults (ASSUMED — from `docs/40-open-questions.md`)

Adopt unless sensitivity analysis or product owner rejects.

| Parameter | Value | Source | ADR at M1? |
|-----------|-------|--------|------------|
| ε (min ENRV) | 0 paise | OQ-01 PROPOSED | Record as impl ADR-011 |
| Approval value threshold | ₹5000 (500000 paise) | OQ-02 PROPOSED | ADR-011 |
| Approval uncertainty ratio | interval_width / ENRV > 0.5 | OQ-02 PROPOSED | ADR-011 |
| Recovery windows | checkout 48h, payment 14d, sub 14d, recv 90d | OQ-03 PROPOSED | ADR-011 |
| Cycle interval | 15 min virtual | OQ-15 PROPOSED | ADR-011 |
| Near-zero metric denominator | < 1 paise | OQ-04 PROPOSED | ADR-011 |
| max_reconcile_attempts | 3 | ASSUMED (34 §9 UNKNOWN) | ADR-011 |
| Merchant timezone | Asia/Kolkata | README C-3 ASSUMPTION | — |
| Net retention factor m | 1.0 | README C-5 ASSUMPTION | — |
| Fatigue weight λ_f | 1.0 | README C-5 PROPOSED | Config file |

---

## 3. Technology decisions (PROPOSED — align with `docs/07` §5, ADR-010)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Engine language | Python 3.11+ | Spec PROPOSED; numeric ecosystem |
| Package layout | `revive/` monolith package | IC-12 smallest sufficient |
| DB | SQLite file `revive.db` | Spec PROPOSED; reproducible single file |
| Money type | `int` paise wrapper class | RR-NFR-001 |
| ID generation | ULID from seeded PRNG in benchmark | README C-4 PROPOSED |
| Allocator primary | Lagrangian relaxation | ADR-007 |
| Allocator fallback | Greedy by ENRV density | RR-FUNC-038 SHOULD |
| Allocator timeout | 3s per RR-NFR-031 | Spec |
| API framework | FastAPI | ASSUMED — HTTP/JSON not specified |
| UI framework | React + Vite + TypeScript | ASSUMED — spec binds data not framework |
| Test runner | pytest | ASSUMED |
| CLI entry | `revive` via `pyproject.toml` scripts | ASSUMED |

---

## 4. Integration posture

| Integration | Label | Decision |
|-------------|-------|----------|
| Razorpay payments | UNVERIFIED | **SIMULATED** — `PaymentEffectAdapter` reads oracle only |
| SMS / WhatsApp / Email | FUTURE production | **SIMULATED** — `MessageAdapter` |
| Voice | OPTIONAL P2 | **SIMULATED** if built |
| Human approval | HACKATHON-SCOPE | Simulated approver per `docs/20-benchmark.md` §7 for benchmark; UI queue for demo |
| LLM (diagnosis/copy) | OPTIONAL P1 | **FUTURE** in P0 benchmark (`LLM_OFF`); cache dir `llm_cache/` when enabled |

---

## 5. Benchmark defaults (ASSUMED for M13)

| Parameter | Value | Notes |
|-----------|-------|-------|
| Primary profile | BALANCED | `docs/19` §2.3 |
| Seeds per evaluation | 20 minimum | RR-NFR-033 |
| P0 policies | REVIVE, B0, B1, B2, B3 + oracle ref | P1 adds B4–B6 |
| Opportunities per run | 500 (initial) | Tune to meet RR-NFR-030 ≤10s/cycle |
| LLM mode for official runs | LLM_OFF | Reproducibility P-8 |
| Comparison | Paired per-seed M-10 diff | Not pooled percentages |

---

## 6. Metric authority resolution

| Issue | Decision |
|-------|----------|
| I-01 M-14 naming | Use **`M-14 Guardrail-block profile`** per `docs/37-metrics-dictionary.md`. Wasted spend = **`M-23`**. |
| Headline metric | **`M-10` Incremental Net Recovered Revenue** only |

---

## 7. Action catalogue (P0 minimum)

From `docs/05` §9 Tier 1 — implement at M6:

- `NO_ACTION` (A00)
- `RETRY_NOW`, `RETRY_SCHEDULED`
- `PAYMENT_LINK`, `ALT_METHOD_PROMPT`
- `MSG_EMAIL`, `MSG_SMS`
- `INCENTIVE_DISCOUNT` (G5 clamped)
- `RECEIVABLE_REMINDER`
- `ESCALATE_HUMAN`

Defer to P1: WhatsApp, dunning, mandate retry, promise-to-pay. Defer to P2: `VOICE_CALL`.

Full enum: `docs/11-counterfactual-engine.md` §3.

---

## 8. Contradictions resolved for implementation

| Topic | Docs | Resolution |
|-------|------|------------|
| M-14 name | README vs 37 | **37 wins** (I-01) |
| State count | 34 §1.1 text vs table | **15 states** (I-02) |
| Fallback allocator tier | 05 SHOULD vs plan P1 visibility | **Implement in P0** as safety (RR-FUNC-039 requires feasible solution); shadow price reporting P1 |
| Baseline count P0 | Contract says B0–B3; 20 doc lists B0–B6 | **P0: B0–B3**; add B4–B6 in P1 without changing harness interfaces |
| Risk classes | Some docs say 4 vs 5 | **5 classes** in data model (`docs/17` includes degradation as flag, 5 risk_class enums in `12`) — detect 4 core + degradation flag `RR-FUNC-006` P1 |

---

## 9. What we will NOT decide without approval

- Changing ENRV formula or objective
- Removing or weakening any gate
- Adding risk classes or action codes outside spec
- Editing frozen `docs/` content
- Claiming real Razorpay or production integration
- Hard-coding benchmark results

---

## 10. Next ADRs to add during implementation

| ADR | Topic | When | Status |
|-----|-------|------|--------|
| ADR-011 | Frozen numeric config (ε, windows, thresholds) | End of M1 | **DRAFT** — `implementation/adr-011-epsilon-threshold.md`; ε=0 provisional |
| ADR-012 | Generator scale (N opportunities, T cycles) | M2 | **Pending** — dev defaults recorded in M2 checkpoint |
| ADR-013 | B1 FIXED_RETRY published schedule | M3 | **DRAFT** — `implementation/adr-013-b1-retry-schedule.md` |
| ADR-014 | UI/API framework choices (if diverging from PROPOSED) | M15/M16 | Pending |

Seed ADRs ADR-001…010 remain in `docs/31-decision-records.md`.

---

## 11. M1 implementation notes (2026-08-21)

| Item | Decision |
|------|----------|
| PRNG stream labels | Closed set in `revive/rng/streams.py` |
| Entity IDs | 26-char Crockford component + prefix (M1 simplification of ULID) |
| PolicyPack | `DRAFT` only; benchmark blocked until `SEALED` |
| Oracle isolation | `outcome_oracle_partition` table + `revive/integrity/boundaries.py` |
| FastAPI / React | Not installed in M1 — deferred to API/UI milestones |

---

## 12. M2 implementation notes (2026-08-21)

| Item | Decision |
|------|----------|
| Generator version | `0.2.0-m2` (`revive/simulation/config.py`) |
| Dev scale | 40 customers, 80 opportunities, 30 virtual days |
| Official benchmark scale | **Not frozen** — ADR-012 pending |
| PRNG streams | Extended per `docs/19 §2.1` + generator sub-streams |
| Oracle pre-draw | Fixed at generation (`OR-2`); `resolve_outcome` at execution |
| Profile enum | All six `docs/19 §2.3` profiles implemented |
| Risk class naming | M1 enums retained (`SUBSCRIPTION_FAILURE`, `RECEIVABLE_OVERDUE`) |
| Dataset output | `artefacts/datasets/` via `revive generate-dataset` |

---

## 13. M3 implementation notes (2026-08-21)

| Item | Decision |
|------|----------|
| Baseline package | `revive/benchmark/baselines/` |
| P0 baselines | B0–B3 only; B4–B6 deferred P1 |
| B3 ENRV | Observable heuristic in `pricing.py` until M7 StrategyVersion |
| Cycle runner | `revive/benchmark/runner.py` — dev validation only |
| Integrity | Baselines included in oracle import guard |

---

## 14. M4 implementation notes (2026-08-21)

| Item | Decision |
|------|----------|
| Sentinel package | `revive/recovery/sentinel/` |
| Detection input | `ObservableWorldView` only; ignores generator opportunities and hidden degradation windows |
| Natural keys | docs/12 §6 (not generator `risk_class:customer:index`) |
| Recovery windows | OQ-03 provisional in `SentinelConfig` |
| Degradation | Observable failure-rate spike (C-03); no hidden cohort labels |
| Checkout fingerprint | `session_id` until a cart fingerprint exists on domain records |

---

## 15. M5 implementation notes (2026-08-21)

| Item | Decision |
|------|----------|
| Context package | `revive/recovery/context/` (C-04) |
| Diagnosis package | `revive/recovery/diagnosis/` (C-05 deterministic path) |
| Cause taxonomy | docs/12 §8.1 `CauseCode` enum; mapping table in `diagnosis/mapping.py` |
| Confidence | Bands only (`LOW`/`MED`/`HIGH`); no numeric confidence on `Diagnosis` |
| Evidence kinds | `FACT` / `PATTERN` / `LIKELY_CAUSE` / `UNKNOWN` on `ContextEvidence` |
| LLM | Not implemented in M5 (`allow_llm=False`); deterministic-only |
| History windows | Provisional in `ContextConfig` (90d customer, 90m degradation reuse) |
| Pipeline | `understand(opp, view, now) = diagnose(assemble_context(...))` |
| Pipeline | `understand(opp, view, now) = diagnose(assemble_context(...))` |
| M6 boundary | No candidates, ENRV, counterfactuals, or action references |

---

## 16. M6 implementation notes (2026-08-22)

| Item | Decision |
|------|----------|
| Candidates package | `revive/recovery/candidates/` (C-06 feasibility only) |
| Action vocabulary | docs/11 `ActionCode` A00–A14 |
| Availability states | `AVAILABLE`, `INELIGIBLE`, `TEMPORARILY_UNAVAILABLE`, `IMPOSSIBLE` |
| Cause-aware enumeration | `rules.py` from docs/12 §8.3 + risk-class base sets |
| Resource templates | `catalogue.py` from docs/11 §3 |
| Nominal cost | `DEFAULT_ACTION_COSTS_PAISE` — not ENRV |
| Capacity | Optional `CandidateCapacityContext` for TEMPORARILY_UNAVAILABLE |
| M7 boundary | No p_action, uplift, ENRV, ranking, or selection |

---

## 17. M7 implementation notes (2026-08-23)

| Item | Decision |
|------|----------|
| Valuation package | `revive/recovery/valuation/` (C-07 counterfactual engine) |
| ENRV formula | Canonical docs/11 §5 component sum — `enrv.py` |
| Predictor | Beta-Binomial cells + shrinkage; observable development priors |
| Natural recovery | Shared `p(i,∅)` per opportunity; uplift = `p(a) − p(∅)` |
| NO_ACTION | ENRV = 0 exactly (CF-1); components all zero |
| Money | Integer paise; banker's rounding in `money.py` |
| Costs | M6 nominal cost + tier incentives + observable fatigue |
| Uncertainty | σ from Beta posterior; `enrv_lo`/`enrv_hi` intervals |
| ε | `epsilon_paise_provisional=0` centralized (ADR-011 DRAFT) |
| Entry | `price_candidates(opp, context, diagnosis, candidate_set, now)` |
| M8 boundary | No allocation, ranking, selection, or execution |

---

## 18. M8 implementation notes (2026-08-23)

| Item | Decision |
|------|----------|
| Allocator package | `revive/allocation/` (C-12 portfolio allocator) |
| Primary mode | Lagrangian relaxation + primal recovery (docs/10 §5.1) |
| Fallback | `ENRV / normalized_resource_cost` — not raw ENRV (B3 diff) |
| Resources | Six families from M6 requirements; incentive at full `d(i,a)` |
| Shadow prices | `LAGRANGIAN_DUAL` or `GREEDY_ESTIMATE` |
| Entry | `allocate_portfolio(items, resource_state, now, cycle_id, policy)` |
| ε | From `PolicyPack.epsilon_paise` — ADR-011 still DRAFT |
| M10 boundary | No gates, execution, or benchmark claims |

---

## 20. M10 implementation notes (2026-08-23)

| Item | Decision |
|------|----------|
| Policy package | `revive/policy/` (C-13 gate engine) |
| Gates | G1–G12 fixed order — docs/13 §3 |
| Stopping | SR-01–SR-11 — docs/14 §2 |
| Authorization artifact | `ExecutionAuthorization` for M11 |
| G5 incentive | DENY on exceed — no silent clamp (demo MAX_DISCOUNT_EXCEEDED) |
| Entry | `authorize_execution(decision, candidate, valuation, ctx)` |
| No substitution | Blocked A never authorizes B |
| M11 boundary | No adapter execution, no outcome measurement |

---

## 21. M11 implementation notes (2026-08-23)

| Item | Decision |
|------|----------|
| Execution package | `revive/execution/` (C-17 ExecutionAgent) |
| Entry | `execute(AuthorisedAction, ...)` / `execute_authorization(...)` |
| AuthorisedAction | `mint_authorised_action()` — AUTHORIZED only |
| Adapters | `revive.execution.adapters.simulated` — oracle boundary |
| Audit | `AuditJournal` — ACTION_INTENT before effect |
| Idempotency | `ExecutionStore` — claim + SCHEDULED upgrade |
| Ledger | `ReservationLedger.commit()` — COMMITTED status |
| Outcomes | `RealizedOutcome` separate from M7 valuation |
| Delayed A02 | SCHEDULED until virtual time; TTL must cover delay |
| M12 boundary | No measurement horizon, no benchmark claims |

---

## 22. M12 implementation notes (2026-08-23)

| Item | Decision |
|------|----------|
| Measurement package | `revive/measurement/` |
| Entry | `measure_execution(execution, valuation, decision, ...)` |
| Attribution | docs/21 §3 split from M11 `attribution_class` |
| Incremental | `attributed` (M-06) + `incremental_vs_no_action` (gross − ref) |
| No-action ref | Predicted: `p_natural·V·m`; Realized: oracle A00 at eval boundary |
| Dedup | `OpportunityRecoveryLedger` — AT-2 / multi-action |
| Idempotency | `MeasurementStore` per `execution_id` |
| Aggregation | `aggregate_cycle`, `aggregate_batch` — M13 inputs only |
| M13 boundary | No B0–B3 comparison, no win-rate claims |

---

## 23. M13 implementation notes (2026-08-23)

| Item | Decision |
|------|----------|
| Official engine | `revive/benchmark/official/` |
| Entry | `execute_benchmark(mode=OFFICIAL\|DEVELOPMENT)` |
| Freeze gate | `check_freeze_prerequisites()` — official blocked until ADR-011/012/013 + SEALED PolicyPack |
| Config hash | `official_benchmark_config_hash()` stored with every run |
| Shared world | `generate_shared_world()` once per seed/profile; policies clone world |
| REVIVE path | Full M4–M12 via `revive_pipeline.py` |
| Baselines | `baseline_pipeline.py` through same authorize/execute/measure |
| Primary metric | M-10 paired vs B0 per docs/21 §2.1 |
| Validation | `BENCHMARK_VALID` / `BENCHMARK_INVALID` / `BENCHMARK_BLOCKED` |
| Falsification | F-1…F-6 in `falsification.py` |
| Artefacts | `artefacts/benchmark/` — config, manifest, per-run, aggregate, safety |
| Reproduction | `reproduce_benchmark()` + CLI `--reproduce` |
| Official run | **NOT EXECUTED** — freeze incomplete |
| STOP | No learning, UI, voice, pitch after M13 |

---

## 24. M13.5 implementation notes (2026-08-23)

| Item | Decision |
|------|----------|
| Calibration package | `revive/benchmark/calibration/` |
| Entry | `run_calibration_diagnostics()`, CLI `revive calibrate` |
| Scale | 5 seeds × 6 profiles × 40 opportunities (calibration_config) |
| Decision | **NOT READY FOR OFFICIAL FREEZE** |
| Baseline separation | CLEARLY_SEPARATED (30/30 cells) |
| Scarcity | LOW — avg competition 0.95; profile capacities not wired in M13 runner |
| B3/REVIVE | WEAK DISTINCTION (CAUTION) |
| M13 zero M-10 root cause | tiny scale (competition ratio 0.08 at 12 opps) |
| Reports | `implementation/m13-5-benchmark-calibration/` |
| Official benchmark | **NOT RUN** in M13.5 |

---

## 25. M13.6 implementation notes (2026-08-23)

| Item | Decision |
|------|----------|
| Repair | `revive/benchmark/capacities.py` — wire `capacity_scarcity_factor` → `ResourceCapacities` |
| Wired into | `policy_runner`, `baseline_pipeline`, calibration scarcity |
| Entry | `run_m13_6_recalibration()`, CLI `revive repair-calibrate` |
| Profile capacity tests | `tests/benchmark/test_profile_capacities.py` |
| Scarcity post-repair | HIGH at 500-op official proposal; MODERATE at 40-op calibration |
| Baseline separation | CLEARLY_SEPARATED at official scale; SCARCE vs ABUNDANT now differ |
| B3/REVIVE | **COLLAPSED** at official scale — identical selections, REVIVE defers only |
| M13.6 decision | **NOT READY FOR FREEZE PREPARATION** |
| Reports | `implementation/m13-6-structural-repair/` |
| Official benchmark | **NOT RUN** in M13.6 |

---

## 26. M13.7 implementation notes (2026-08-23)

| Item | Decision |
|------|----------|
| Audit package | `revive/benchmark/calibration/thesis_audit/` |
| Entry | `run_m13_7_audit()`, CLI `revive thesis-audit` |
| Official 500/100/30d | 0 conflicts, 0 B3/REVIVE differing — collapse confirmed |
| 500/100/21d | 11,766 conflicts, 43 differing — differentiation exists |
| M8 audit | ALIGNED with docs/10 |
| B3 audit | ALIGNED with docs/20 |
| Fallback | 0% at official scale |
| Thesis classification | **THESIS CONFIGURATION-DEPENDENT** |
| Reports | `implementation/m13-7-allocation-thesis/` |
| Official benchmark | **NOT RUN** in M13.7 |

---

## 27. M13.8 implementation notes (2026-08-23)

| Item | Decision |
|------|----------|
| Audit package | `revive/benchmark/calibration/m13_8/` |
| Entry | `run_m13_8_decision()`, CLI `revive freeze-decision` |
| Config A (30d/500/100) | Rejected — 0 conflicts, 27/30 zero-diff cells |
| Config B (21d/500/100) | **Recommended** — mean 15,635 conflicts, 37.4 differing |
| ADR-012 | Recommendation in `implementation/adr-012-benchmark-scale.md` |
| ADR-011 ε | Proposed 100 paise — not auto-accepted |
| ADR-013 B1 | Recommend ACCEPT as-is |
| Seeds | 1–20 fixed rule |
| M13.8 decision | **READY TO FREEZE** (governance complete; ADRs pending acceptance) |
| Reports | `implementation/m13-8-benchmark-freeze-decision/` |
| Official benchmark | **NOT RUN** in M13.8 |

---

## 28. M13.9 implementation notes (2026-08-23)

| Item | Result |
|------|--------|
| Type | Read-only freeze verification audit — no code changes |
| Official config vs M13.8 proposed | **MISMATCH** — code 30d/ε=0/DRAFT; proposed 21d/ε=100/SEALED |
| Official execution | **blocked=True** (verified) |
| World sharing / oracle isolation | PASS |
| Config hash | Computed; proposed ≠ current |
| M13.9 decision | **FREEZE BLOCKED** |
| Artifact | `implementation/m13-9-final-freeze-gate.md` |
| Official benchmark | **NOT RUN** |

---

## 29. M13.10 implementation notes (2026-08-23)

| Item | Result |
|------|--------|
| ADR-011/012/013 | **ACCEPTED** |
| Runtime | 21d, ε=100, `pol_m13_official_v1` SEALED |
| ε authority | PolicyPack → `valuation_config_for_policy()` |
| Freeze manifest | `artefacts/benchmark/official/freeze-manifest.json` |
| CLI | `revive freeze-seal` |
| M13.10 decision | **FREEZE COMPLETE** |
| Official benchmark | **NOT RUN** |

---

## 19. M9 implementation notes (2026-08-23)

| Item | Decision |
|------|----------|
| Decision package | `revive/decision/` (lifecycle integrity) |
| Seal | `seal_allocation()` — immutable `AllocationDecision` + reservations |
| Decision ID | Deterministic hash — reproducible per cycle/opp/config |
| Idempotency key | docs/15 §3.1 derived hash |
| Reconcile | `reconcile_decision()` — VALID/STALE/EXPIRED, no M8 re-run |
| Ledger | `ReservationLedger` — intent only, release on invalidation |
| Store | `DecisionStore` — append-only, supersession, transition log |
| Expiry | PROVISIONAL 15 min virtual TTL |
| M10 boundary | No gates, execution, or benchmark |
