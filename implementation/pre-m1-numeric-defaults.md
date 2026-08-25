# Pre-M1 Numeric Default Audit

**Rule:** Values listed only if present in specification or `implementation-decisions.md`. Empty cells mean **not numerically specified** — do not invent at audit time.

**Legend — changes benchmark?** Y = likely affects M-10 or guardrail coverage; N = structural/format; C = configurable via policy pack.

---

## 1. Economic / allocation parameters

| Parameter | Current value | Source | Why it exists | Changes benchmark? | Configurable? | User approval? |
|-----------|---------------|--------|---------------|-------------------|---------------|----------------|
| ENRV threshold ε | **PROPOSED 0 paise** (conflicts with `11` §5.3 "ε>0") | OQ-01, `35b` §5.1 | Minimum justified action | **Y** | Yes (`PolicyPack.epsilon`) | **Yes** |
| Net retention m | **ASSUMPTION 1.0** | `README` C-5 | Gross→net on recovery | Y (scales ENRV) | Yes | No (disclose) |
| Fatigue weight λ_f | **PROPOSED 1.0** | `README` C-5, `35b` §11.2 | Converts F to paise | **Y** | Yes | **Yes** (sensitivity) |
| Pacing factor | **PROPOSED 1.0** | OQ-14, `35b` §8.2 | Per-cycle budget cap | Y | Yes | P1 |
| Exploration budget fraction | **PROPOSED 0.05** | OQ-07 | P1 learning | Y | Yes | P1 only |
| Near-zero denominator (metrics) | **PROPOSED <1 paise** | OQ-04, `37` §10 | RR-METRIC-008 | N | Yes | No |
| Tie-break order | `(−ENRV, −V, opp_id)` | `RR-FUNC-034`, `35b` §2 | Determinism | N (unless ties common) | No | No |
| Allocator time budget | **≤3 s** | `RR-NFR-031` | Feasible solve | Y if timeout often | Yes | No |
| Cycle step budget | Bounded (23 steps) | `RR-GUARD-025`, `07` §4 | Termination | N | Yes | No |
| Shadow price method | Lagrangian dual (approx) | `10` §4 | UI/report | N | — | No |

---

## 2. Time parameters

| Parameter | Current value | Source | Why | Changes benchmark? | Configurable? | Approval? |
|-----------|---------------|--------|-----|-------------------|---------------|-----------|
| Cycle interval | **PROPOSED 15 min virtual** | OQ-15, `07` §1.2 | Batch cadence | **Y** | Yes | **Yes** |
| Recovery window — checkout | **PROPOSED 48 h** | OQ-03 | SR-01 | **Y** | Yes | **Yes** |
| Recovery window — payment | **PROPOSED 14 d** | OQ-03 | SR-01 | **Y** | Yes | **Yes** |
| Recovery window — subscription | **PROPOSED 14 d** | OQ-03 | SR-01 | **Y** | Yes | **Yes** |
| Recovery window — receivable | **PROPOSED 90 d** | OQ-03 | SR-01 | **Y** | Yes | **Yes** |
| Horizon H per class | `min(H_class, window−now)` | `11` §2 | Uplift window | **Y** | Yes (policy pack) | **Yes** (with windows) |
| H_class numeric values | **Not specified** | `11` §2 "PROPOSED placeholders" | Same as above | **Y** | Yes | **Yes** |
| Retry cooldown seconds | **Not specified** | `RR-GUARD-004`, `13` G4 | Gate G4 | **Y** | Yes | **Yes** |
| Approval validity period | **PROPOSED** (shorter than window) | `14` §10 | SR-06 | Y | Yes | **Yes** |
| max_reconcile_attempts | **ASSUMED 3** (UNKNOWN in `34`) | `34` §9 | TIMEOUT path | Y | Yes | Before benchmark |

---

## 3. Guardrail / policy caps

| Parameter | Current value | Source | Why | Changes benchmark? | Configurable? | Approval? |
|-----------|---------------|--------|-----|-------------------|---------------|-----------|
| max_retries_per_instrument | **Not specified** | `RR-GUARD-004` | G4, SR-03 | **Y** | Yes | **Yes** |
| max_retries_per_opportunity | **Not specified** | `14` SR-03 | Stopping | **Y** | Yes | **Yes** |
| max_contacts_per_window (G3) | **Not specified** | `RR-GUARD-003` | Contact cap | **Y** | Yes | **Yes** |
| Per-day / 7d / 30d contact caps | **Not specified** | `13` G3 | Four counters | **Y** | Yes | **Yes** |
| SR-04 opportunity contact budget | **PROPOSED** (unnamed N) | `14` SR-04 | Anti drip-feed | **Y** | Yes | **Yes** |
| SR-07 consecutive NO_ACTION N | **PROPOSED** (unnamed) | `14` SR-07 | Economic stop | **Y** | Yes | **Yes** |
| max_discount_pct | **Not specified** | `RR-GUARD-005` | G5 clamp | **Y** | Yes | **Yes** |
| max_discount_paise | **Not specified** | `RR-GUARD-005` | G5 clamp | **Y** | Yes | **Yes** |
| Incentive tier ceilings | **Enum tiers, values not specified** | `11` §3 | G5 | **Y** | Yes | **Yes** |
| Communication windows (hours) | **Not specified** | `RR-GUARD-002` | G2 defer | Y | Yes | **Yes** |
| G12 absolute/relative amount caps | **Not specified** | `RR-GUARD-012` | Sanity | Y | Yes | **Yes** |
| approval_value_threshold | **PROPOSED ₹5000 (500000 paise)** | OQ-02 | G7 | Y | Yes | **Yes** |
| approval_uncertainty_threshold | **PROPOSED interval_width/ENRV > 0.5** | OQ-02 | G7 | Y | Yes | **Yes** |

---

## 4. Resource budgets / capacities (SCARCE profile)

| Parameter | Current value | Source | Why | Changes benchmark? | Configurable? | Approval? |
|-----------|---------------|--------|-----|-------------------|---------------|-----------|
| incentive_budget (period) | **Not specified** | `10` §3, `19` DS-4 | Scarcity | **Y** | Yes | **Yes** |
| message_capacity_email/sms/whatsapp | **Not specified** | `10` §3 | Scarcity | **Y** | Yes | **Yes** |
| retry_slots | **Not specified** | `10` §3 | Scarcity | **Y** | Yes | **Yes** |
| human_review_slots | **Not specified** | `10` §3 | Scarcity | **Y** | Yes | **Yes** |
| voice_minutes | **Not specified** (P2 action) | `10` §3 | Optional resource | P2 | Yes | P2 |
| contact_allowance per customer | **Not specified** | `10` §3.1 | Per-customer contention | **Y** | Yes | **Yes** |

---

## 5. Action costs

| Parameter | Current value | Source | Why | Changes benchmark? | Configurable? | Approval? |
|-----------|---------------|--------|-----|-------------------|---------------|-----------|
| c(a) direct costs per action | **Not specified** | `11` §3, `13` pack | ENRV term (2) | **Y** | Yes (policy pack) | **Yes** |
| d(i,a) incentive amounts per tier | **Not specified** | `11` §3 | ENRV term (3) | **Y** | Yes | **Yes** |
| F(i,a) fatigue function params | **PROPOSED structure; params not numeric** | `35b` §11.1 | ENRV term (4) | **Y** | Partially | **Yes** |
| Shrinkage κ₁, κ₂ | **Not specified** | `11` §4.3 | Predictor | Y | Yes (strategy) | Before benchmark |
| prior_weight (cells) | **PROPOSED 10** | OQ-05 | P1 learning | P1 | Yes | P1 |
| min_obs shrinkage | **PROPOSED 20** | OQ-06 | P1 learning | P1 | Yes | P1 |

---

## 6. Benchmark / scale parameters

| Parameter | Current value | Source | Why | Changes benchmark? | Configurable? | Approval? |
|-----------|---------------|--------|-----|-------------------|---------------|-----------|
| Seeds per evaluation | **≥20 PROPOSED** | `RR-NFR-033`, `20` §3.1 | Dispersion | Y (variance) | CLI/config | No |
| Opportunities per run | **PROPOSED ~500** (few hundred–few thousand) | `19` §2.4, `RR-NFR-030` | Batch + perf | **Y** | Generator config | Before M13 |
| Virtual days / cycle count | **Not specified** | `19` §2.4 UNKNOWN | Windows play out | **Y** | Generator | **Yes** |
| Customer count | **PROPOSED fewer than opportunities** | `19` §2.4 | Per-customer contention | Y | Generator | Before M2 |
| Primary profile | **BALANCED** | `19` §2.3 | Headline | **Y** | CLI | No |
| Profiles reported | 6 named | `19` §2.3 | Honesty | Y | CLI | No |
| Baselines P0 | **B0–B3** | `32` §2 | Comparison | **Y** | Harness | **Yes** (vs demo B0–B6) |
| LLM mode official runs | **LLM_OFF** | `implementation-decisions`, `20` §5.1 | Reproducibility | Y | CLI | No |
| Cycle perf target | **≤10 s / 500 opps** | `RR-NFR-030` | NFR | N | Scale down if fail | No |
| Full run per seed | **≤3 min** | `RR-NFR-032` | NFR | N | — | No |
| Multi-seed session | **≤60 min total** | `RR-NFR-033` | NFR | N | Parallel seeds | No |

---

## 7. B1 baseline schedule (must be published)

| Parameter | Current value | Source | Why | Changes benchmark? | Configurable? | Approval? |
|-----------|---------------|--------|-----|-------------------|---------------|-----------|
| B1 FIXED_RETRY schedule | **Not specified** | `20` BF-9, `15` §7.1 ref | Credible baseline | **Y** | Baseline config | **Yes — before M3** |

---

## 8. Metrics / evaluation numerics

| Parameter | Current value | Source | Why | Changes benchmark? | Configurable? | Approval? |
|-----------|---------------|--------|-----|-------------------|---------------|-----------|
| M-10 definition | Paired REVIVE−best baseline per seed | `37`, `21` | Primary metric | Defines headline | No | No |
| M-16,M-17,M-18,M-22 must be 0 | Hard gate | `RR-METRIC-004` | Invalidates run | Y | No | No |
| Calibration bins | **PROPOSED equal-width deciles** | OQ-09 | M-24 | P1 | Yes | P1 |
| Bootstrap CI | Optional; seed count noted as small | `20` §3.4 | Reporting | N | — | No |

---

## Critical gap

**Most policy-pack numerics (retries, contacts, budgets, costs, H_class) are structurally required but not assigned values in the frozen spec.** They must be chosen at M2/M10, frozen in `config_hash` before comparative benchmark (`RR-BENCH-008`). **This is expected** per `40-open-questions.md` but is the largest numeric risk for benchmark outcomes.

---

## Recommended freeze checkpoint (before M13 comparative runs)

1. Publish complete `PolicyPack v1` with all caps, costs, windows, H, ε (resolved), SR-07 N, SR-04 N  
2. Publish generator profile parameters for BALANCED + SCARCE + ABUNDANT  
3. Publish B1 retry schedule  
4. Hash → `config_hash`  
5. Run sensitivity on ε, λ_f, windows at ±50% per `40` §3  
