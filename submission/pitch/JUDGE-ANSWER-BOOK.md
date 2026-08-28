# Judge answer book

15–30 second answers. Use product evidence, not abstraction.

---

## Why should I care?

Merchants lose revenue in fragments — failed payments, abandoned carts, mandate failures. Most of it would recover naturally. PAYVANTA finds **incremental** net recovery: where the next unit of effort actually pays off under constraints. Control Room shows the batch; Benchmark Lab shows the engine evaluated across 600 official cells.

---

## Why isn’t this a retry engine?

A retry engine fires on a schedule. PAYVANTA compares **do nothing** vs interventions on **incremental net recovery**, allocates under scarce capacity, and stops when guardrails say no. Baseline B1 in the official experiment is the fixed-retry policy — we measure against that and B0 do-nothing.

---

## Why isn’t this just a dashboard?

Dashboards display state. PAYVANTA **closes the loop**: diagnose → counterfactual → optimize → guard → authorize → execute → measure → audit. The blocked opportunity `opp_WST4PPPH81VPNTNC18K0YGRAW9` proves the system refuses unsafe actions.

---

## Why isn’t this just a chatbot?

Because the job is not to talk about recovering money — it is to safely recover it. Optional Groq diagnosis proposes causes and candidates in the sandbox; there is no chat UI. Controls gate execution. Official engine path: `llm_used=false`.

---

## Where is actual autonomy?

Autonomy is **bounded orchestration**: the cycle proposes interventions and runs batch allocation. It cannot skip guardrails, cannot execute without AUTHORIZED, cannot retry without a fresh gate pass. That is autonomy inside deterministic bounds.

---

## What happens when the recommendation is wrong?

Counterfactuals show alternatives and do-nothing. Guardrails and stopping rules can block a high ENRV. Authorization can deny. Measurement attributes actual vs predicted. Audit records intent before effect. Wrong does not mean uncontrolled.

---

## What stops unsafe execution?

12-gate PolicyPack · stopping rules · authorization · idempotency · no adapter on BLOCKED. Red-team tests reject writes to official evidence. Show Guardrails on the blocked opp.

---

## Where is the money?

Control Room money pillar: incremental net recovery for this sandbox batch. Official M-10 per cell vs B0 in Benchmark Lab when evidence is mounted. Integer paise throughout.

---

## How is “incremental” defined?

Incremental net recovery = uplift attributable to intervention minus cost and fatigue, versus natural recovery. M-10 in the official experiment = `NetRecovered(policy) − NetRecovered(B0)` on the same seed and profile.

---

## How was the batch measured?

Sandbox: cycle runner aggregates detected → diagnosed → authorized → executed → measured across the opportunity pool. Official: frozen 20×6×5 experiment with paired M-10. Three layers: sandbox operation, official evaluation, receipt/audit per decision.

---

## What proves the result?

1. Decision receipt + audit reference (one decision)  
2. Sandbox batch aggregates (one run)  
3. 600 official cells with `BENCHMARK_VALID`, frozen hash, per-cell checksum (engine evaluation)

We say **measured**, not **proven superiority**.

---

## Why AI?

Track 03 is AI Revenue Recovery. PAYVANTA uses **two layers**:

1. **Sandbox (optional):** Groq `openai/gpt-oss-120b` for contextual diagnosis and candidate **proposals** — no execution authority.
2. **Engine / official benchmark:** Deterministic ENRV, allocation, guardrails — `llm_used=false`, official `LLM_OFF`.

The economic engine and controls remain authoritative. See `docs/why-ai.md` and workspace **AI diagnosis** vs **PAYVANTA economic decision**.

---

## Where exactly is AI?

| Layer | Where | Evidence |
|---|---|---|
| Groq diagnosis (sandbox) | `revive/product/intelligence/` | `POST /api/opportunity/{id}/ai-diagnosis` · workspace panel |
| Deterministic engine | `diagnose.py`, `enrv.py`, `lagrangian.py`, `trace.py` | Recovery Lab · Guardrails · official benchmark |
| Overview | `GET /api/product/overview` | `ai` block + `intelligence.engine_llm_used: false` |

---

## Why not LLM direct execution?

Reasoning and financial authority are different trust domains. Intelligence proposes; deterministic policy, guardrails, and authorization retain execution authority. AI failure → deterministic fallback — never auto-authorize.

---

## What happens if AI fails?

Missing key, timeout, HTTP error, or invalid schema → **DETERMINISTIC FALLBACK** or **AI_UNAVAILABLE**. Product continues. No execution from failed AI. Tests: `tests/product/test_intelligence.py`.

---

## Why not rules?

Rules enforce boundaries. The AI layer adds contextual interpretation and candidate proposals in the sandbox. The economic engine prices and validates paths; guardrails and authorization decide execution.

---

## What can execute? / What cannot?

**Can:** AUTHORIZED actions via bounded adapters. **Cannot:** BLOCKED, unapproved, stopping violations, duplicates — no adapter call.

---

## What happens when uncertain?

`UNCLASSIFIED` diagnosis, guardrail blocks, human approval gates — all recorded in audit without execution.

---

## How are stopping rules enforced?

Policy stopping evaluator overrides high ENRV. Visible in Guardrails on blocked opp.

---

## How is idempotency handled?

Idempotency keys on execution; duplicates rejected. Test: `tests/execution/test_idempotency.py`.

---

## What does 600 cells prove / NOT prove?

**Proves:** engine evaluated under frozen 20×6×5 design. **Does not prove:** superiority, production fitness, guaranteed recovery.

---

## What is production-ready?

Architecture and measurement semantics are demonstrated. Live Razorpay integration is out of scope — sandbox only.

---

Detection hooks, intervention catalogue, guardrail gates, measurement semantics, audit schema. Live rails and merchant accounts are **not** in this sandbox submission.

---

## What is sandbox-only?

Simulated adapters, synthetic population, Control Room batch figures. Official evidence is a separate frozen tree.

---

## What was actually hard?

Parallel worker dispatch propagation (M13.24). Checkpoint drift under partial groups (M13.25). ABUNDANT profile scaling / Lagrangian hot path (M13.26). Metrics-tail O(n²) scan (M13.27). Cloud validation before the 600-cell run.

---

## 30-second project description

PAYVANTA is an autonomous revenue recovery system that detects revenue at risk, compares recovery interventions against a do-nothing baseline, executes only within deterministic controls, measures incremental net recovery across a batch, and records the result in an auditable trail. Its engine is independently evaluated across 600 official experiment cells.

---

## 10-second project description

PAYVANTA finds slipping revenue, chooses the economically justified recovery action, executes only inside bounds, measures the incremental net result, and proves the engine across 600 official cells.
