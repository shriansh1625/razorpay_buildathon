# PAYVANTA — final project description

## Problem

Merchants lose revenue across failed payments, abandoned checkouts, mandate failures, and overdue invoices. Much of it would recover naturally. Blind retries and blast campaigns waste capacity and customer patience. The question is not “send another message” but **where the next unit of recovery effort produces incremental net value** under policy and resource limits.

## Solution

PAYVANTA is an autonomous revenue recovery operating system. It detects typed revenue-at-risk opportunities, diagnoses cause from observable evidence, compares interventions against a **do-nothing baseline**, selects under simultaneous constraints, gates execution through deterministic controls, measures incremental net recovery across a batch, and writes an auditable decision trail.

## Agentic / AI role (honest)

| Claim | Reality |
|---|---|
| LLM in runtime | **No** — `llm_used=False`, official `LLM_OFF` |
| Track 03 “agent” | **Yes** — bounded recovery cycle that detects, decides, and acts within guardrails |
| Intelligence | Deterministic **decision system**: taxonomy diagnosis, counterfactual ENRV, Lagrangian allocation |
| Autonomy | Orchestrated pipeline cannot skip guardrails or execute without AUTHORIZED |

Track 03 AI Revenue Recovery is satisfied through **decision intelligence under uncertainty**, not chatbot theatrics.

## Bounded execution

Recommendation ≠ permission. PolicyPack gates, stopping rules, and authorization sit between optimisation and adapters. Blocked opportunities (`opp_WST4PPPH81VPNTNC18K0YGRAW9`) demonstrate escalation without execution.

## Measurement

- **Per decision:** receipt + measurement block (incremental vs natural vs cost)
- **Sandbox batch:** Control Room money pillar (SANDBOX · seed 14)
- **Official engine evaluation:** M-10 vs B0 across 600 frozen cells when evidence mounted

## Audit

Hash-chained journal. `ACTION_INTENT` recorded before irreversible effects. UI `#/audit` · `GET /api/audit`.

## Benchmark

20 seeds × 6 profiles × 5 policies = **600 official cells**. Frozen configuration. `BENCHMARK_VALID` when `artefacts/benchmark/official-cloud-final/` is mounted. Does **not** prove universal superiority or production fitness.

## Repository

https://github.com/shriansh1625/razorpay_buildathon

```bash
pip install -e ".[dev]"
revive control-room
```

## Submission assets

| Asset | Path |
|---|---|
| Architecture | `docs/43-operating-architecture.md` |
| Track 03 evidence | `docs/track3-evidence.md` |
| AI honesty | `docs/why-ai.md` · `implementation/final-submission/AI-SUBSTANCE-GATE.md` |
| 5-minute script | `submission/pitch/FINAL-5-MINUTE-SCRIPT.md` |
| Judge answers | `submission/pitch/JUDGE-ANSWER-BOOK.md` |
