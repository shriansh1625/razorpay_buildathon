# M1 Approval Gate

**Review date:** 2026-08-21  
**Reviewer role:** Pre-implementation approval (documentation + plan only)  
**Code written:** None (confirmed)

---

## 1. Gate checklist

| Check | Result |
|-------|--------|
| 46 spec files reviewed (M0) | Pass |
| 76 MUST requirements mapped | Pass — no orphans (`pre-m1-requirement-health.md`) |
| Critical doc contradictions | Pass — only I-01, I-02 cosmetic (`36b`) |
| Economic model single definition | Pass with E-01 ε ambiguity noted |
| Benchmark integrity design | Pass |
| Razorpay claims controlled | Pass — UNVERIFIED/SIMULATED |
| LLM boundary | Pass — P0 deterministic path |
| P0 feasibility | Pass — no RED items |
| Blockers for M1 foundation | **None** |

---

## 2. Issues that do NOT block M1 (block benchmark freeze later)

| ID | Issue | When to resolve |
|----|-------|-----------------|
| E-01 | ε=0 vs ε>0 prose conflict | ADR-011 before benchmark freeze |
| — | Policy pack numerics unspecified (retries, contacts, budgets, costs, H) | PolicyPack v1 at M2/M10 |
| — | B1 retry schedule unpublished | M3 |
| — | Simulated approver model details | M10/M11 |
| — | Generator scale (N opps, virtual days) | M2 |
| — | Demo script B0–B6 vs P0 B0–B3 scope | Plan P1 or extend harness before demo |

---

## 3. Explicit assumptions you accept by approving M1

If you approve M1, you accept that implementation will proceed with:

### Architecture & technology
1. **Cycle-based batch architecture** (ADR-001) — not event-per-payment workflow  
2. **Python 3.11+ monolith + SQLite** (PROPOSED ADR-010)  
3. **FastAPI + React** for API/UI (ASSUMED — not frozen in spec)  
4. **SIMULATED adapters only** — no real Razorpay or messaging providers in P0  

### Economic model
5. **ENRV formula** as in README C-5 / `11` §5 (uplift-based, integer paise)  
6. **m = 1.0** net retention (ASSUMPTION — disclosed upper bound)  
7. **λ_f = 1.0** until sensitivity runs (PROPOSED)  
8. **ε = 0 paise** interim default pending ADR-011 resolution of E-01  
9. **Conservative incentive reservation** (full d reserved, ENRV uses p·d)  

### Time & cycles
10. **15-minute virtual cycle interval** (OQ-15 PROPOSED)  
11. **Recovery windows:** checkout 48h, payment 14d, subscription 14d, receivable 90d (OQ-03 PROPOSED)  

### Benchmark & data
12. **Synthetic generator fidelity UNVERIFIED** — all headline results labelled synthetic  
13. **Constructed scarcity and value/recoverability correlations** in dataset (`19` §5.2)  
14. **≥20 seeds, BALANCED headline profile, LLM_OFF for official runs**  
15. **P0 baselines B0–B3** (B4–B6 deferred to P1 unless you direct otherwise)  
16. **~500 opportunities** initial scale target (`RR-NFR-030`)  
17. **Parameter freeze + config_hash** before any comparative benchmark claim  

### Safety & integrity
18. **12 gates + 11 stopping rules** — no weakening  
19. **Oracle isolation** — decision path never reads oracle partition  
20. **No LLM in money path** (RR-GUARD-020)  
21. **Honest reporting** — F-1…F-6, ABUNDANT profile, seeds lost, adverse findings  

### Approvals & ops
22. **G7 thresholds:** value > ₹5000; uncertainty ratio > 0.5 (OQ-02 PROPOSED)  
23. **max_reconcile_attempts = 3** (ASSUMED until ADR)  
24. **Simulated human approver** in benchmark (not real operators)  

---

## 4. What M1 will and will not do

| M1 will | M1 will not |
|---------|-------------|
| Repo layout, pyproject, pytest scaffold | Business logic for recovery |
| Domain types (Paise, IDs, enums) | Generator or oracle |
| DB schema skeleton per `17` | Allocator, gates, UI |
| Virtual clock + labelled PRNG | Benchmark runs |
| State machine transition tables (tests stubs) | Policy pack final numerics |
| ADR-011 draft for numeric defaults | Razorpay integration |

---

## 5. Risks accepted for the program (not M1 blockers)

| Risk | Severity |
|------|----------|
| Schedule pressure from 76 MUST + 7 UI + 20-seed benchmark | High |
| Policy numeric design affects M-10 more than allocator algorithm choice | High |
| ε ambiguity if unresolved at freeze | Medium |
| Generator–predictor circular tuning if discipline slips | Medium |
| Demo script expects B4–B6 before P1 plan delivers them | Medium |

---

## 6. Recommendation

Material ambiguities exist (**ε conflict**, **unset policy numerics**) but **none prevent M1 foundation work** (types, schema, clock, PRNG, test harness, module boundaries). They **must** be resolved before **M13 comparative benchmark freeze**.

---

# APPROVE M1 WITH EXPLICIT ASSUMPTIONS

**Conditions:**
- Accept assumptions §3 in full  
- Resolve **E-01 (ε)** via ADR-011 before first comparative benchmark  
- Publish **PolicyPack v1** numerics before M10 completion  
- Do not treat any benchmark number as valid until `config_hash` freeze  

**Do not approve M1 if:** you require all numeric defaults finalized before any code — in that case, hold M1 until PolicyPack workshop completes (estimated 1 planning session, no coding).

---

## 7. Documents produced in this gate

| Document |
|----------|
| `pre-m1-assumption-audit.md` |
| `pre-m1-numeric-defaults.md` |
| `pre-m1-p0-feasibility.md` |
| `pre-m1-requirement-health.md` |
| `pre-m1-economic-model-audit.md` |
| `pre-m1-benchmark-integrity.md` |
| `pre-m1-simulation-realism.md` |
| `pre-m1-architecture-minimality.md` |
| `pre-m1-llm-boundary.md` |
| `pre-m1-razorpay-claims.md` |
| `pre-m1-demo-critical-path.md` |
| `M1-approval-gate.md` (this file) |

**No code. No scaffolding. No dependency installs. Hard stop maintained.**
