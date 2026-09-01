# AI substance gate — P11

**Date:** 2026-08-28  
**Audit type:** Code + API + docs (no benchmark changes, no LLM injection)

---

## Phase 1 — What is actually shipped?

| Layer | Module | Mechanism | Autonomous? | Intelligent? | Deterministic? |
|---|---|---|---|---|---|
| **Detect** | `revive/recovery/sentinel/` | Revenue Sentinel classifies leakage into typed opportunities | Cycle-driven | Rule + taxonomy | Yes |
| **Diagnose** | `revive/recovery/diagnosis/diagnose.py` | `rank_causes()` taxonomy ranking from observable context | Yes | Contextual ranking | Yes — `llm_used=False` |
| **Candidates** | `revive/recovery/candidates/rules.py` | Closed action catalogue from diagnosis | Yes | Feasibility filtering | Yes |
| **Economics** | `revive/recovery/valuation/enrv.py` | Counterfactual ENRV vs do-nothing | Yes | Uplift × value − cost − fatigue | Yes |
| **Select** | `revive/allocation/lagrangian.py` | Lagrangian portfolio allocation under scarcity | Yes | Constrained optimisation | Yes |
| **Guard** | `revive/policy/` | 12-gate PolicyPack + stopping rules | Yes | Policy evaluation | Yes |
| **Authorize** | `revive/policy/authorize.py` | AUTHORIZED / BLOCKED / REQUIRES_HUMAN_APPROVAL | No bypass | Gate outcome | Yes |
| **Execute** | `revive/execution/` | Bounded adapters; idempotent | Only if AUTHORIZED | Adapter dispatch | Yes |
| **Measure** | `revive/measurement/` | Incremental vs natural vs cost | Post-execution | Attribution | Yes |
| **Audit** | `revive/audit/` | Intent before effect | Automatic | Journal append | Yes |
| **Orchestration** | `revive/product/trace.py` | Full recovery cycle wiring | **Bounded agent loop** | Pipeline coordination | Yes |

**Engine LLM inference:** none (`llm_used=False`). **Sandbox overlay:** optional Groq diagnosis/proposal. Overview reports `official_llm_mode: LLM_OFF`.

---

## Phase 2 — Classification (updated P11.5)

### Product AI layer (Groq)

**Class: A — Meaningful AI diagnosis layer added (sandbox only)**

| Item | Detail |
|---|---|
| Model | `openai/gpt-oss-120b` via Groq |
| Role | Contextual diagnosis + candidate **proposal** |
| Authority | **None** over authorization or execution |
| Fallback | Honest deterministic fallback when key absent or provider fails |
| Benchmark | **Untouched** — still `LLM_OFF` |

### Engine / official path

Unchanged deterministic engine. Official 600-cell evidence frozen.

---

## Phase 4–8 — No LLM injection (deliberate)

Per P11 north star: *do not look more advanced than you are.*

| Option | Verdict |
|---|---|
| Add fake LLM / hardcoded “AI response” | **REJECTED** — credibility failure |
| Set `llm_used=true` without inference | **REJECTED** |
| Insert LLM into frozen benchmark path | **REJECTED** — violates Phase 7 |
| Document deterministic decision intelligence as Track 03 AI | **SELECTED** |

Future sandbox LLM (if ever added) must: pass deterministic validation, never authorize execution, show AI ENABLED vs DETERMINISTIC FALLBACK honestly, stay out of official benchmark semantics.

---

## Phase 9 — AI evaluator 20-second answers

**Why is this AI?**  
Track 03 AI Revenue Recovery is decision intelligence under uncertainty: counterfactual economics, portfolio allocation under scarcity, and bounded autonomous orchestration — not a chatbot. Sandbox may call Groq for diagnosis/proposal only; official engine path remains `LLM_OFF`. See `docs/why-ai.md`.

**Where is AI used?**  
Not an LLM. Intelligence lives in `rank_causes`, `compute_enrv`, `lagrangian_allocate`, and the recovery cycle in `revive/product/trace.py`. API: `GET /api/product/overview` → `intelligence`.

**What if AI proposes unsafe action?**  
Guardrails and stopping rules run after optimisation. Authorization can BLOCK. Adapters never called. Show `opp_WST4PPPH81VPNTNC18K0YGRAW9`.

**Can AI execute money movement directly?**  
No. Intelligence proposes; PolicyPack + authorization permit; execution adapters run only on AUTHORIZED. Invariant in `docs/why-ai.md` §6.

---

## Trust boundary (Phase 19)

```
AI / INTELLIGENCE          CONTROL                 ENGINE
UNDERSTAND · PROPOSE   →   VALIDATE · AUTHORIZE  →  EXECUTE · MEASURE
(diagnosis, ENRV, alloc)    (guardrails, auth)        (adapters, M-10, audit)
```

---

## Recommendation

1. **Do not add fake LLM** for competition optics.  
2. **Strengthen visibility** of decision intelligence in README, pitch AI moment (0:40 Analyze), and judge answers.  
3. **Record 5-minute video** — remaining P1 deliverable.
