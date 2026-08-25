# Pre-M1 Material Assumption Audit

**Phase:** M0 → M1 approval gate  
**Scope:** Assumptions that can materially affect benchmark, economics, architecture, or scope  
**Rule:** No frozen `docs/` edits — report only

---

## Classification key

| Label | Meaning |
|-------|---------|
| **KNOWN** | Stated by brief or definition internal to REVIVE |
| **DOCUMENTED** | Explicit in spec with label |
| **PROPOSED** | Engineering choice with stated default |
| **ASSUMED** | Needed to proceed; adopted in `implementation-decisions.md` |
| **UNKNOWN** | No decision; blocks measurement if unset |
| **FUTURE** | Explicitly out of P0 scope |

---

## Assumption register

| ID | Assumption | Source | Classification | Impact | Proposed default | Alternative | Approval required? |
|----|------------|--------|----------------|--------|------------------|-------------|------------------|
| A-01 | Primary objective is ENRV (uplift-based), not gross recovery | `README` C-5, ADR-002 | **KNOWN** | Defines all scoring | — | Rejected objectives in charter §4.1 | No |
| A-02 | Currency is INR integer paise only | `README` C-2 | **KNOWN** | All money math | — | Multi-currency (FUTURE) | No |
| A-03 | Merchant is India-domiciled; timezone `Asia/Kolkata` | `README` C-3 | **ASSUMPTION** | Quiet hours, salary-cycle features | Asia/Kolkata | UTC-only | No (documented assumption) |
| A-04 | Net retention factor `m = 1.0` | `README` C-5, `11` §5.1 | **ASSUMPTION** | ENRV upper bound vs real net | 1.0 | Merchant-specific `<1` | No — disclose in reports |
| A-05 | Fatigue weight `λ_f = 1.0` | `README` C-5, `35b` §11.2 | **PROPOSED** | Contact-heavy vs contact-light policies | 1.0 | 0 (no fatigue term), >1 conservative | **Yes** — sensitivity at ±50% |
| A-06 | ENRV threshold `ε` | OQ-01, `35b` §5.1 | **PROPOSED** | How many actions qualify | **0 paise** | ε>0 conservative | **Yes** — **conflicts with `11` §5.3 text requiring ε>0** |
| A-07 | Recovery windows per class | OQ-03, `35b` §10 | **PROPOSED** | SR-01, horizon H | checkout 48h; payment 14d; sub 14d; recv 90d | Shorter/longer windows | **Yes** — freeze before benchmark |
| A-08 | Horizon H per class tied to windows | `11` §2, `35b` §10 | **PROPOSED** | Uplift measurement window | `H = min(H_class, window_close − now)` | Fixed H independent of window | No if derived rule kept |
| A-09 | Cycle interval 15 min virtual | OQ-15, `07` §1.2 | **PROPOSED** | Contention, decay, pacing | 15 min | 1 min (degenerates to per-event) | **Yes** — affects multi-cycle behavior |
| A-10 | Batch architecture (not event-driven) | ADR-001 | **DOCUMENTED** | Entire product thesis | Cycle-based | Per-event workflow | No (frozen ADR) |
| A-11 | `p(i,∅)` estimated per opportunity, not constant | `RR-FUNC-023`, `11` §4.1 | **DOCUMENTED** | Uplift validity | Feature-based cell model | Constant p∅ (invalidates thesis) | No |
| A-12 | Predictor = Beta-Binomial cells + shrinkage | ADR-006, `11` §4.2 | **PROPOSED** | Calibration, ENRV quality | Hierarchical cells | Logistic regression | No for P0 |
| A-13 | Prior pseudo-observations for cells | OQ-05, `35` §2.2 | **PROPOSED** | P1 learning only | 10 | 5 / 20 | No for P0 (learning P1) |
| A-14 | Allocator = Lagrangian + greedy fallback | ADR-007 | **PROPOSED** | M-10, shadow prices | Lagrangian ≤3s then greedy | Greedy-only | No |
| A-15 | Six resource families bind allocation | `10` §3, `07` §6.3 | **DOCUMENTED** | ≥4 constraints requirement | incentive, msg×channel, retry, human, contact/customer | Fewer resources | No |
| A-16 | Gates are hard constraints, not penalties | ADR-009 | **DOCUMENTED** | M-16 must be 0 | DENY not negotiable | Soft penalty in objective | No |
| A-17 | Oracle fixed at generation; policy never reads it | `19` OR-2, `AI-6` | **DOCUMENTED** | Benchmark integrity | Separate partition | Inline outcomes | No |
| A-18 | Generator fidelity is UNVERIFIED | `19` header, ADR-008 | **DOCUMENTED** | External validity | Synthetic only | Real data | No — must disclose |
| A-19 | Natural recovery share is non-trivial | `19` DS-3, `HIGH_NATURAL` profile | **DOCUMENTED** | B0 floor, uplift test | Profile-tuned rates | p∅≈0 (breaks CF-7) | No — but generator params need design |
| A-20 | Scarcity is constructed (demand > capacity) | `19` DS-4, §5.2 | **DOCUMENTED** | Allocation testability | SCARCE + BALANCED profiles | Abundant-only batch | No |
| A-21 | Value vs recoverability negatively correlated in subset | `19` §5.2 | **PROPOSED** | REVIVE vs B4 differentiation | Deliberate construction | Independent (weakens B4 contrast) | No — disclose as invented |
| A-22 | Baselines B0–B3 P0; B4–B6 P1 | `32` §2 P0/P1 | **ASSUMED** | Headline comparison set | B0–B3 + oracle ref | Full B0–B6 in P0 | **Yes** — demo script references B0–B6 |
| A-23 | ≥20 seeds for evaluation | `RR-NFR-033`, `00` §9 | **DOCUMENTED** | CI / dispersion claims | 20 seeds | Fewer seeds (weaker claim) | No |
| A-24 | Benchmark path: no network, no uncached LLM | `RR-NFR-092`, `RR-NFR-035` | **DOCUMENTED** | Reproducibility | LLM_OFF + cache for ablations | Live LLM in benchmark | No |
| A-25 | Simulated adapters only (no Razorpay production) | `36`, `OS-02` | **DOCUMENTED** | Integration claims | SIMULATED | Real API (UNVERIFIED) | No |
| A-26 | Approval thresholds | OQ-02 | **PROPOSED** | M-18, demo beat 5 | V>₹5000; interval/ENRV>0.5 | Higher thresholds | **Yes** |
| A-27 | Simulated human approver in benchmark | `20` §7 (referenced), `07` §4 step 14 | **PROPOSED** | Escalation without real humans | Documented response model | Manual demo only | **Yes** — model must be published |
| A-28 | max_reconcile_attempts | `34` §9 | **UNKNOWN** | TIMEOUT_UNKNOWN path | **3** (ASSUMED) | 1 / 5 | No for M1; yes before benchmark |
| A-29 | SR-07 consecutive NO_ACTION cycles `N` | `14` SR-07 | **PROPOSED** (param unnamed) | Stopping coverage | Must be set in policy pack | Higher N = longer pursuit | **Yes** — freeze with config_hash |
| A-30 | Policy pack numeric caps (retries, contacts, discounts) | `13` §2 structure | **UNKNOWN** | Guardrails, B1 schedule | Must be invented at M2/M10 | — | **Yes** — not numerically specified in docs |
| A-31 | Action direct costs `c(a)`, tiers `d(i,a)` | `11` §3 | **UNKNOWN** (structure only) | ENRV ranking | Policy-pack parameters | — | **Yes** — freeze before measurement |
| A-32 | Opportunity count ~500 per run | `RR-NFR-030`, `19` §2.4 | **PROPOSED** | Runtime, contention realism | 500 | 200–5000 | No for M1 |
| A-33 | Python 3.11 + SQLite monolith | `07` §5, ADR-010 | **PROPOSED** | Dev velocity, determinism | As spec | Postgres microservices | No for hackathon |
| A-34 | FastAPI + React UI | `implementation-decisions.md` | **ASSUMED** | Not in frozen spec | FastAPI/React | Other stacks | No |
| A-35 | LLM optional P1; diagnosis/copy only | ADR-003, `RR-GUARD-020` | **DOCUMENTED** | P0 path has deterministic fallback | LLM_OFF in benchmark | LLM_FULL required | No |
| A-36 | Learning engine P1; cannot write policy | `RR-GUARD-022`, `35` §7 | **DOCUMENTED** | Safety architecture | Posterior update only | End-to-end RL (rejected) | No |
| A-37 | Train/eval seed split for tuning | `19` §8.3 | **DOCUMENTED** | Anti-overfitting | Disjoint seed sets | Tune on reported seeds (forbidden) | No |
| A-38 | Demo requires 7 screens + pre-run benchmark | `26` §0 | **DOCUMENTED** | Schedule pressure | All 7 | Subset UI | No |
| A-39 | Partial recovery does not trigger SR-02 | `14` SR-02 | **DOCUMENTED** | Multi-cycle loops | Reduce V, re-price | Immediate stop | No |
| A-40 | Conservative incentive reservation (full d, not p·d) | `10` §3.3 | **DOCUMENTED** | Budget utilization vs safety | Reserve d unconditional | Expected reservation | No |
| A-41 | `ENRV(i,∅)=0` by definition | `README` C-5 | **KNOWN** | NO_ACTION semantics | 0 exactly | — | No |
| A-42 | Negative uplift retained, not clipped | `RR-FUNC-025`, `11` CF-10 | **DOCUMENTED** | Honest NO_ACTION / harmful action cases | Keep negative u | Clip at 0 (invalid) | No |
| A-43 | Razorpay API surface UNVERIFIED | `36` entire doc | **DOCUMENTED** | No production integration | Adapter + simulator | Real endpoints | No |
| A-44 | Benchmark compares paired per-seed M-10 | `20` §3.3, `21` | **DOCUMENTED** | Headline statistic | Median paired diff | Pooled % (forbidden) | No |
| A-45 | ABUNDANT profile must be reported even if flat | `RR-BENCH-009`, `19` §8.2 | **DOCUMENTED** | Honesty | Include in report | Hide weak profile | No |
| A-46 | Audit hash chain is system of record | ADR-005 | **DOCUMENTED** | Demo beat 5, M-58 | SHA-256 chain | App tables authoritative | No |
| A-47 | ε strict positivity vs ε=0 default | `11` §5.3 vs OQ-01 | **UNKNOWN** | Zero-ENRV actions at ε=0 | Resolve via ADR-011 | ε=1 paise minimum | **Yes — material ambiguity** |
| A-48 | Five risk classes in generator vs four in RR-FUNC-001 | `19` §5.1 vs `05` | **DOCUMENTED** | Detection scope | 4 core + optional 5th/pre-failure P2 | Merge classes | No — map MANDATE_HEALTH to P2 |
| A-49 | Config freeze before comparative measurement | `RR-BENCH-008`, `19` §8.3 | **DOCUMENTED** | Invalidates post-hoc tuning | config_hash | Iterative tuning | No |
| A-50 | Byte-identical artefacts at same seed | `RR-NFR-020` | **DOCUMENTED** | Build-blocking test | Full determinism | Statistical equivalence | No |

---

## Highest-impact assumptions requiring explicit acceptance before benchmark freeze

1. **A-06 / A-47** — ε default (0 vs strictly positive)  
2. **A-07, A-09, A-29, A-30, A-31** — Policy pack numerics not fully specified  
3. **A-21** — Deliberate negative value/recoverability correlation (honest but synthetic)  
4. **A-27** — Simulated approver behavior model  
5. **A-22** — P0 baseline scope vs demo script B0–B6 expectation  

---

## Summary counts

| Classification | Count |
|----------------|------:|
| KNOWN | 4 |
| DOCUMENTED | 28 |
| PROPOSED | 12 |
| ASSUMED | 4 |
| UNKNOWN | 4 |
| FUTURE | 0 (listed only where referenced) |

**Material UNKNOWN items blocking benchmark freeze (not M1):** A-28, A-29, A-30, A-31, A-47
