# Pre-M1 P0 Feasibility Review

**Scope:** P0 capabilities from `implementation/implementation-plan.md` / `32-implementation-contract.md` §2  
**Ratings:** GREEN = safe & necessary; YELLOW = necessary with implementation risk; RED = threatens schedule or benchmark quality

---

## P0 capability matrix

| P0 Requirement | Complexity | Dependencies | Risk | Testability | Demo importance | Recommended implementation | Rating |
|----------------|------------|--------------|------|-------------|-----------------|---------------------------|--------|
| **P0.1 Synthetic environment** | High | M1 schema, PRNG, clock | Generator gaming; oracle leak | High (DS-11/12, AI-6) | Medium (implicit in benchmark) | Seeded generator + oracle partition + manifest/hash | **YELLOW** |
| **P0.2 Baselines B0–B3** | Medium | M2, execution path | B1 schedule credibility | High (deterministic replay) | High (beat 6) | Same harness; swap ranking function only | **GREEN** |
| **P0.3 Detection (4 classes)** | Medium | DOMAIN tables, signals | Dedup edge cases | High (recall vs ground truth) | High (beat 2) | C-01/C-02 deterministic rules | **GREEN** |
| **P0.4 Candidate actions** | Medium | Action catalogue, diagnosis | Large rule table surface | High (≥3 per opp) | High (beat 3) | Rule table by class×cause | **GREEN** |
| **P0.5 Counterfactual / ENRV** | High | Predictor, cost model | ε ambiguity; calibration | High (hand fixtures CF-1–12) | Critical (beat 3–4) | Beta-Binomial p(a), p(∅); integer ENRV | **YELLOW** |
| **P0.6 Recovery allocation** | High | Pricing, policy pre-filter, ledger | Time budget; optimality gap | High (constraint exhaustion) | Critical (beat 4) | Lagrangian ≤3s + greedy fallback | **YELLOW** |
| **P0.7 Guardrails (12 gates)** | High | Policy pack, ledger, state | Many edge cases; numeric gaps | High (T-POL-*) | Critical (beat 5) | Single C-13 engine; ordered G1–G12 | **YELLOW** |
| **P0.8 Stopping rules SR-01–11** | Medium–High | Policy pack, state machine | Coverage across benchmark | High (per-rule tests) | High (beat 5) | C-14 deterministic; double eval | **GREEN** |
| **P0.9 Execution simulator** | Medium | Gates, ledger, audit | Idempotency races | High (T-FUNC-060+) | High (beat 7) | C-17 + sim adapters → oracle | **GREEN** |
| **P0.10 Outcome measurement** | Medium | Adapters, clock H | Attribution edge cases | High (partial, NATURAL) | High (beat 3 outcome) | C-19/C-20; no oracle in metrics path for M-10 | **GREEN** |
| **P0.11 Batch benchmark** | High | Full pipeline + baselines | 20 seeds × policies runtime | High (RR-NFR-020) | Critical (beat 6) | CLI freeze→generate→run→verify→report | **YELLOW** |
| **P0.12 Incremental metric M-10** | Medium | Benchmark harness | Mis-specified pairing | High (formula tests) | Critical | Independent evaluator vs runtime | **GREEN** |
| **P0.13 Audit trail** | Medium | All phases | Chain break on crash | High (T-SAF-008) | High (beat 5) | Append-only SHA-256; audit before effect | **GREEN** |
| **P0.14 Seven UI screens** | Medium–High | API + artefacts | Schedule sink if early | Medium (integration) | High (all beats) | Read-only SPA on precomputed runs | **YELLOW** |

---

## Supporting MUST clusters (within P0)

| Cluster | Key IDs | Rating | Notes |
|---------|---------|--------|-------|
| Diagnosis/context | RR-FUNC-010–015, 011–012 | **GREEN** | Deterministic path first |
| Decision semantics | RR-FUNC-040–043 | **GREEN** | Data model heavy |
| Architectural guardrails | RR-GUARD-020–026 | **GREEN** | Enforce by structure + tests |
| NFR determinism | RR-NFR-001–006, 020–021 | **GREEN** | Foundational in M1 |
| NFR safety | RR-NFR-040–043, 050–053 | **YELLOW** | Crash-injection labor |
| RR-UI-001–008 | 8 screens + disclosure | **YELLOW** | 7 screens + banners |

---

## RED items

**None at P0 capability level.** No P0 item should be removed.

---

## YELLOW items — why they are not RED

| Item | Risk | Mitigation |
|------|------|------------|
| Synthetic environment | Oracle leak / easy dataset | AI-6 test; publish `distributions.json`; SCARCE+ABUNDANT profiles |
| ENRV stack | Spec ε conflict; miscalibration | ADR-011; property tests; report calibration even if weak |
| Allocator | NP-hard; 3s limit | Greedy fallback RR-FUNC-039; record `allocator_mode` |
| Guardrails | Unspecified numeric caps | Single PolicyPack v1 frozen before benchmark |
| Benchmark harness | 20 seeds × 8 policies runtime | Parallel seeds; LLM_OFF; profile subset for dev |
| UI | 7 screens | Bind to artefacts; no live recompute (RR-NFR-034) |

---

## Schedule threat summary

| Threat | Severity | When it hits |
|--------|----------|--------------|
| Building UI before M13 | High | Weeks 1–2 if mis-ordered |
| Incomplete PolicyPack numerics | High | M10/M13 |
| Generator without scarcity/natural recovery | Critical | M2 — invalid benchmark |
| Skipping B4–B6 for demo narrative | Medium | Demo script vs P0 scope — plan B4–B6 for P1 or minimal stub |

---

## Verdict

**P0 is feasible within hackathon scope** if milestone order is respected and PolicyPack numerics are frozen before comparative benchmark. No RED capabilities; **6 YELLOW** areas need disciplined execution, not scope cuts.
