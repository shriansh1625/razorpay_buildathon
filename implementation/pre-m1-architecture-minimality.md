# Pre-M1 Architecture Minimality Audit

**Question:** Are we building the minimum architecture to prove the thesis?

**Thesis to prove:** Constrained **portfolio allocation by ENRV** beats credible baselines on **incremental net recovery**, with **zero policy violations** and **auditability**.

---

## 1. Component necessity matrix

| Component | Phase | P0? | Necessary? | Simplify? | Complexity |
|-----------|-------|-----|------------|-----------|------------|
| C-01 Signal Ingestor | SEE | Y | Yes — quarantine, dedupe input | No | Low |
| C-02 Revenue Sentinel | SEE | Y | Yes — core detection | No | Med |
| C-03 Degradation Monitor | SEE | P1 | No for P0 | Defer | Med |
| C-04 Context Enricher | UNDERSTAND | Y | Yes — features for p(a), p(∅) | No | Med |
| C-05 Root Cause Analyst | UNDERSTAND | Y | Yes — cause drives candidates | Deterministic-only P0 | Med |
| C-06 Candidate Generator | SIMULATE | Y | Yes — action space | No | Med |
| C-07 Recovery Predictor | SIMULATE | Y | Yes — uplift requires p(a), p(∅) | No (thesis core) | High |
| C-08 Cost Model | SIMULATE | Y | Yes — ENRV | No | Low |
| C-09 Counterfactual Evaluator | SIMULATE | Y | Yes — ENRV assembly | Merge with C-08? Possible but keep separate for tests | Low |
| C-10 Copy Composer | SIMULATE | P1 | No P0 | Defer | Low |
| C-11 Policy Pre-Filter | GUARD | Y | Yes — RR-FUNC-037 | No | Med |
| C-12 Recovery Allocator | PRIORITIZE | Y | **Thesis heart** | No | High |
| C-13 Policy Engine | GUARD | Y | Yes — M-16=0 | No | High |
| C-14 Stopping Rules | GUARD | Y | Yes — Track bar | Could merge into C-13; spec separates | Med |
| C-15 Approval Queue | GUARD | Y | Yes — escalation | Simulated approver P0 | Med |
| C-16 Resource Ledger | GUARD/ACT | Y | Yes — scarcity | No | Med |
| C-17 Execution Agent | ACT | Y | Yes — bounded execution | No | Med |
| C-18 Adapters (sim) | ACT | Y | Yes — oracle boundary | Single sim adapter with handlers | Med |
| C-19 Outcome Observer | VERIFY | Y | Yes — M-10 input | No | Med |
| C-20 Attribution Classifier | VERIFY | Y | Yes — no inflate M-10 | No | Low |
| C-21 Learning Engine | LEARN | P1 | No P0 | Defer | Med |
| C-22 Audit Store | cross | Y | Yes — Track bar | No | Med |
| C-23 Cycle Orchestrator | cross | Y | Yes — batch thesis | No | Med |
| C-24 Benchmark Harness | ext | Y | Yes — proof | No | High |
| C-25 Generator + Oracle | ext | Y | Yes — environment | No | High |
| C-26 Metrics/Report | ext | Y | Yes — M-10 artefact | No | Med |
| C-27 API | surface | Y | Yes — UI | Minimal read API P0 | Low |
| C-28 UI (7 screens) | surface | Y | Yes — demo/judging | Artefact-first | Med–High |

**Agents (3):** C-05 LLM optional; C-10 P1; C-23 orchestrator — **P0 can run with deterministic C-05 + C-23 without LLM**. Agent count is not excess for P0.

---

## 2. Could anything be merged?

| Merge candidate | Verdict |
|-----------------|---------|
| C-08 + C-09 | Optional merge; spec separates for RR-NFR-082 independent testability — **keep separate** |
| C-13 + C-14 | Possible single `guard/` package; two evaluators — **keep logical separation** |
| C-24 + C-26 | Benchmark + report often one module — **acceptable merge in code** |
| Multiple microservices | **Rejected** by spec (`07` §9) |

---

## 3. Non-minimal temptations (do not add)

- Extra agents (Negotiation, Critic, Router) — explicitly rejected in `08`  
- Graph DB — rejected ADR-008  
- Real Razorpay adapter in P0 — out of scope  
- Voice centrepiece — P2/T3  
- LLM in benchmark path — breaks reproducibility  

---

## 4. Minimum proof path vs full P0

**Smallest thesis proof (not sufficient for submission):**

```
Generator → Sentinel → Candidates → Predictor → ENRV → Allocator → Gates → Sim execute → Metrics → B0–B3 compare
```

**Full P0 adds:** 12 gates, 11 SR, audit chain, 7 UI, 76 MUST, 20 seeds — **required by spec**, not by thesis alone.

---

## 5. Verdict

| Question | Answer |
|----------|--------|
| Is 28-component inventory excessive for thesis alone? | Slightly — but **aligned with Track 03 bar** |
| Can P0 defer parts without losing thesis? | C-03, C-10, C-21 (already P1) |
| Is architecture minimal for **judging**? | **Yes, at spec floor** — further cuts violate MUST reqs |
| M1 scope | Foundation only — **not building all 28 in M1** |

**Architecture is the minimum consistent with frozen spec**, not the minimum imaginable recovery script.
