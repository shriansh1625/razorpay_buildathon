# Pre-M1 Economic Model Audit (ENRV)

**Authority chain:** `README` C-5 → `09-decision-engine.md` → `11-counterfactual-engine.md` §5 → `37-metrics-dictionary.md` (M-10)

**Rule:** Report ambiguities; do not modify frozen docs.

---

## 1. Canonical formula (single definition)

For opportunity `i`, action `a`:

```
u(i,a)     = p(i,a) − p(i,∅)                                    [uplift]

gross(i,a) = u(i,a) · V(i) · m                                  [expected incremental gross, paise]

ENRV(i,a)  = gross(i,a)
             − c(a)                                              [unconditional direct cost]
             − p(i,a) · d(i,a)                                   [expected incentive cost]
             − λ_f · F(i,a)                                      [fatigue externality]

ENRV(i,∅)  = 0                                                  [by definition]
```

**Consistency across docs:** **CONSISTENT** (`36b` §2). Same formula in README, 09, 11, 10 (allocation uses stored ENRV).

---

## 2. Term-by-term verification

| Term | Definition | Can be negative? | Notes |
|------|------------|------------------|-------|
| **Uplift u** | P(recover\|a) − P(recover\|∅) over horizon H | **Yes** | Must not clip (`RR-FUNC-025`) |
| **Value V** | Recoverable amount at risk (paise), not gross invoice | No (≥0) | Excludes written-off/disputed (`11` §5.1) |
| **m** | Merchant net retention on recovered gross | (0,1] default 1.0 | ASSUMPTION — reported ENRV is upper bound |
| **c(a)** | Message/retry/voice/human direct cost | ≥0 | **Unconditional** — paid even if fail |
| **d(i,a)** | Incentive if success | ≥0 | Enters as **p(i,a)·d(i,a)** in ENRV |
| **F(i,a)** | Fatigue externality units | ≥0 | Function of contact history, channel, value |
| **λ_f** | Paise per fatigue unit | ≥0 | Policy dial; not learned (`RR-GUARD-022`) |

**Ledger vs ENRV:** Reservation uses full `d(i,a)` conservatively (`10` §3.3) while ENRV uses expected `p·d` — intentional; slack reported.

---

## 3. NO_ACTION semantics

| Property | Spec |
|----------|------|
| Always in candidate set | `RR-FUNC-020`, `A00` |
| ENRV | **Exactly 0** (`CF-1`) |
| Resource usage | 0 |
| Wins when | All other candidates have ENRV ≤ ε, or allocator chooses ∅, or gates deny all |
| Reason codes | Closed set (`35b` §6): ECONOMIC, POLICY, ALLOCATION, TIMING, NO_UPLIFT |
| Measurement | M-15 share; M-19 missed value if oracle disagrees |

**NO_ACTION is economically meaningful**, not absence of decision.

---

## 4. Can ENRV be negative?

**Yes**, for real actions when:

- u ≤ 0 and c > 0, or  
- costs + fatigue exceed gross uplift  

**Selection rule:** Allocator only selects candidates with **ENRV > ε** (and gates ALLOW). Negative-ENRV candidates remain in store for audit (`CF-10`, M-20).

**For NO_ACTION:** ENRV = 0, never negative.

---

## 5. Tie-breaking

| Level | Rule | Source |
|-------|------|--------|
| Across opportunities | `(−ENRV, −value_at_risk_paise, opportunity_id)` | `RR-FUNC-034` |
| Within opportunity (display) | `(−ENRV, action_code)` | `35b` §2.2 |
| Execution order | `opportunity_id` ULID sort | `35b` §2.2 |

Deterministic given seeded ULIDs.

---

## 6. Uncertainty treatment

| Element | Mechanism |
|---------|-----------|
| σ from predictor | Beta-Binomial posterior spread |
| ENRV interval | Derived from σ on p(a) and p(∅); `enrv_lo`, `enrv_hi` |
| Degraded context | Inflates σ → wider interval → more G7 approvals |
| Uses | Reporting, G7 approval — **not** added to ENRV point estimate |
| Exploration | Thompson sampling under separate budget (P1) — not optimism in exploitation |

**Ambiguity:** Exact interval propagation formula not fully closed-form in spec — implementation must document derivation in ADR and property-test `CF-9`.

---

## 7. Budget constraints vs ENRV

| Layer | Role |
|-------|------|
| Allocator | Maximizes Σ ENRV subject to resource caps |
| Gates G6 | DEFER if reservation fails |
| Gates G1–G5, G7–G12 | Hard deny/defer/modify — **not** penalty terms in objective |
| ε threshold | Per-action minimum ENRV |

**Gates do not read ENRV for allow/deny** except G5 re-price after clamp and G7 thresholds on V and interval width.

---

## 8. Discount / incentive handling

| Stage | Behavior |
|-------|----------|
| Candidate params | `incentive_tier` enum — not free-form LLM |
| G5 | Clamp to max pct/paise/customer cap → `ALLOW_WITH_MODIFICATION` |
| Re-price | After clamp, recompute ENRV; if ≤ ε → NO_ACTION |
| Cost in ENRV | Expected `p(i,a)·d(i,a)` |
| Ledger | Reserve full `d(i,a)` unconditionally |

**Consistent** across 11, 13, 10.

---

## 9. Communication cost handling

| Cost type | Treatment |
|-----------|-----------|
| SMS/email/link | Fixed c(a) per action code in policy pack |
| Contact allowance | Resource + G3 cap + fatigue F |
| Voice | c(a) + voice_minutes resource (P2 action) |

Channel costs are **not** conditional on success unless specified as incentive.

---

## 10. Expected recovery calculation

| Quantity | Definition |
|----------|------------|
| Expected gross incremental | u · V · m |
| Expected net in ENRV | Above minus costs |
| Observed recovered | From adapter/oracle at execution — **not** ENRV |
| Partial recovery | Reduces V; re-enters pricing (`14` SR-02) |

Predictor estimates **probability**, not amount, unless partial amounts modeled separately (`RR-FUNC-070`).

---

## 11. Incremental recovery (M-10) vs ENRV

| Concept | Scope |
|---------|-------|
| ENRV | **Ex ante** per candidate at decision time |
| M-10 | **Ex post** paired policy comparison: NetRecovered(REVIVE) − NetRecovered(best baseline) per seed |

Net recovered uses same cost model and attribution rules (`21` §5). **M-10 is not sum of ENRV** — it is realized outcomes.

**Baseline relationship:**

- B0 = natural recovery floor  
- REVIVE should beat B3 (greedy ENRV) and ideally B1/B2 on M-10 under SCARCE/BALANCED  
- B5 isolates uplift; B3 isolates allocation  

---

## 12. Identified ambiguities (do not resolve in docs here)

| # | Ambiguity | Authority | Impact | Resolution at implementation |
|---|-----------|-----------|--------|------------------------------|
| E-01 | **ε = 0 (OQ-01) vs ε > 0 strictly (`11` §5.3)** | Conflicting prose | Zero-ENRV actions at ε=0 | ADR-011: pick one; sensitivity |
| E-02 | **H_class numeric values** | PROPOSED placeholders | Uplift window | Freeze in PolicyPack |
| E-03 | **F(i,a) exact function** | Structure in 35b §11.1 | Fatigue term magnitude | Document formula + calibrate on synthetic |
| E-04 | **ENRV interval derivation** | Partial in 11 §7 | G7 triggers | Document + CF-9 tests |
| E-05 | **35b lists A11 as voice in approval families** vs **11 §3 A12=VOICE** | Typo in 35b | G7 family flags | Map A12 voice, A11 extension per 11 |
| E-06 | **m=1.0** | ASSUMPTION | Overstates net vs fees | Disclose in all reports |

---

## 13. Mathematical consistency verdict

**One coherent economic model exists** across the spec. Implementation must:

1. Use integer paise ENRV with component-sum reconstruction (`RR-FUNC-029`)  
2. Never clip negative uplift pre-selection  
3. Keep gates out of the objective  
4. Resolve E-01 before benchmark freeze  

**No blocker for M1** (foundation only). **Benchmark freeze blocked** until E-01, E-02, E-03, policy costs resolved.
