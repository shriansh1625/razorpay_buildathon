# AI substance — architecture

**Scope:** PAYVANTA product sandbox only. Official benchmark remains `LLM_OFF`.

## Pipeline

```
OBSERVED CONTEXT
      ↓
AI DIAGNOSIS (Groq GPT-OSS 120B) — optional
      ↓
DETERMINISTIC CANDIDATE VALIDATION (closed ActionCode / CauseCode)
      ↓
ENRV / COUNTERFACTUAL
      ↓
LAGRANGIAN ALLOCATION
      ↓
GUARDRAILS → AUTHORIZATION → BOUNDED EXECUTION → MEASUREMENT → AUDIT
```

## Trust boundary

| Zone | May | May not |
|---|---|---|
| **AI** | Interpret context, propose cause, propose candidates | Authorize, execute, override ENRV |
| **Control** | Guard, stop, authorize, escalate | Invent evidence |
| **Engine** | Execute, measure, audit | Skip gates |

## Code locations

- `revive/product/intelligence/` — Groq client, schema, diagnosis orchestration
- `revive/product/server.py` — `POST /api/opportunity/{id}/ai-diagnosis` (cached)
- `revive/product/ui/app.js` — AI diagnosis panel vs PAYVANTA economic decision

## Official benchmark

No Groq calls from `revive/benchmark/official/`. Frozen experiment unchanged.
