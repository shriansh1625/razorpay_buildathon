# 04 · AI evaluator + staff AI engineer

Official page framing: *“Think you can build real AI?”* Track 03 why-now: *“AI can now close the loop.”*  
The Track 03 **bar** does **not** require an LLM. It requires an **agent** that detects, chooses, executes, measures. This section scores that tension honestly.

---

## What would impress me

- A machine-readable `GET /api/product/overview` that matches the UI (local only; not on origin).
- Deterministic authority: no LLM number moves money (`docs/README.md` C-7; official `LLM_MODE_OFFICIAL = "LLM_OFF"`).
- Counterfactual ENRV vs do-nothing is actual valuation, not a chatbot rationale.
- Allocator is an algorithm with constraints, not “the model said so.”
- Official experiment is 600 cells, frozen hash, read-only HTTP 405 on writes.

## What would make me skeptical

- `revive/recovery/diagnosis/diagnose.py`: **Root Cause Analyst** always sets `llm_used=False`. `DiagnosisConfig.allow_llm: bool = False  # M5 deterministic-only; LLM deferred`.
- Diagnosis is `revive/recovery/diagnosis/rules.py` — mapped reason codes and if/else ranking.
- `docs/08-agent-architecture.md` claims **two LLM-invoking agents** (C-05 Root Cause Analyst, **C-10 Copy Composer**). Copy Composer has **no Python module**. C-05 does not invoke an LLM.
- Simulator payload: `"llm_mode": "OFF"`.
- The product UI has **no chatbot** (good for safety) and **no model trace** (bad for “show the AI”).
- Analyze overlay walks 11 English beats that do not correspond to new inference.

## What would make me reject

- Fake LLM confidence, hidden CoT, or user-agent-specific “evaluator” payloads. **Not found.** Overview is a projection of the same snapshot.
- Prompt injection against a judge model. **Not found.**
- Claiming neural diagnosis while `llm_used` is hardcoded false.

## What I need to verify (as an autonomous reviewer)

| Probe | Expected if honest | Origin/main today |
|---|---|---|
| Clone README | How to run the product | Engine-only M10 README |
| `GET /api/product/overview` | Product, SANDBOX, seed, claims | Route does not exist on origin |
| `#/system` | Same facts as API | UI not in origin |
| `revive/recovery/diagnosis/` | Rules + `llm_used=False` | Present on origin (engine is real) |
| Official tree | 600 cells, verified | **gitignored**, not in origin |

An AI evaluator that only reads **GitHub** never sees the Control Room.

---

## Critical question 3 — “mostly deterministic hardcoding”

**Yes. A fair staff engineer would say this.**

Where:

| Layer | What it actually is |
|---|---|
| Detection | Deterministic sentinel over synthetic signals |
| Diagnosis | Closed taxonomy + `rank_causes` |
| Candidates | Enumerated action set |
| “Right intervention” | ENRV + Lagrangian allocator |
| Guard / stop | Gate functions + SR-01…SR-11 |
| Copy / conversation | Not implemented |
| Cycle “agent” | `run_traced_cycle` orchestration |

The **defense** (and it is a good one, if said out loud): Track 03 money actions must be bounded; an LLM that picks discounts would be a *worse* submission. The intelligence is **economic optimization under constraints**.

The **attack**: the internship is branded AI Builder; Track 03’s why-now sentence is about AI closing the loop; example directions include Hinglish voice. A panelist who wanted an LLM agent can score “AI meaningfulness” as weak without violating the written bar.

**Classification:** **P1** (material score risk), not P0 (not a written disqualifier).

---

## Issues

| ID | Sev | Issue |
|---|---|---|
| AI-1 | P1 | Spec claims LLM agents that the code does not run |
| AI-2 | P1 | No implemented Copy Composer; diagnosis never uses LLM |
| AI-3 | P1 | AI evaluator cannot discover the product from origin/main |
| AI-4 | P2 | Analyze cinematic is narrative, not inference |
| AI-5 | P2 | `docs/08` still the best “agent” map — and it is stale |
| AI-6 | P3 | Optional: a *bounded*, schema-closed LLM diagnosis path behind a flag, never on official cells |

---

## Staff engineer one-liner

I would rather ship this allocator than a GPT wrapper on retries. I would still fail the candidate on **honesty of the agent story** until docs/08 and the pitch match `llm_used=False`.
