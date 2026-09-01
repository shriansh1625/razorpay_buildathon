# PAYVANTA — final project description

## Problem

Merchants lose revenue across failed payments, abandoned checkouts, mandate failures, and overdue invoices. Much of it would recover naturally. Blind retries and blast campaigns waste capacity and customer patience. The question is not “send another message” but **where the next unit of recovery effort produces incremental net value** under policy and resource limits.

## Project objectives (~110 words)

PAYVANTA is a bounded revenue recovery system for merchant revenue operations. It detects typed revenue at risk, prices each intervention against doing nothing (incremental net recovery, not gross collections), allocates under capacity and policy constraints, and executes only after deterministic guardrails and authorization. Optional Groq GPT-OSS 120B interprets sandbox context and proposes causes and candidates; it has no execution authority. The same engine is evaluated separately across a frozen 20×6×5 official experiment (600 cells, LLM_OFF). This submission does not claim live Razorpay integration, production fitness, or universal superiority.

## Agentic / AI role (honest)

| Layer | LLM? | Role |
|---|---|---|
| **Sandbox product** | Optional Groq | Contextual diagnosis + candidate **proposal** — no execution authority |
| **Engine / official benchmark** | No — `llm_used=false`, `LLM_OFF` | ENRV, allocation, guardrails, execution |
| **Track 03 agent** | Yes | Bounded recovery cycle: detect → decide → act within guardrails |

AI proposes. The economic engine selects. Controls authorize. Nothing executes without AUTHORIZED.

## Bounded execution

Recommendation ≠ permission. PolicyPack gates, stopping rules, and authorization sit between optimisation and adapters. Blocked opportunity `opp_WST4PPPH81VPNTNC18K0YGRAW9` demonstrates escalation without execution.

## Measurement

- **Per decision:** receipt + measurement block (incremental vs natural vs cost)
- **Sandbox batch:** Control Room money pillar (SANDBOX · seed 14)
- **Official engine evaluation:** M-10 vs B0 across 600 frozen cells when evidence mounted

## Audit

Hash-chained journal. Intent recorded before irreversible effects. UI `#/audit` · `GET /api/audit`.

## Benchmark

20 seeds × 6 profiles × 5 policies = **600 official cells**. Frozen configuration. `BENCHMARK_VALID` when `artefacts/benchmark/official-cloud-final/` is mounted. Does **not** prove universal superiority or production fitness. Official experiment did **not** use Groq.

## Repository

https://github.com/shriansh1625/razorpay_buildathon

```bash
pip install -e ".[dev]"
revive control-room
```

Optional AI: `$env:GROQ_API_KEY = "<rotated-key>"` (server-side env only — never commit).

## Submission assets

| Asset | Path |
|---|---|
| P15 release report | `submission/P15-FINAL-RELEASE-REPORT.md` |
| Architecture | `docs/43-operating-architecture.md` |
| Track 03 evidence | `docs/track3-evidence.md` |
| AI honesty | `docs/why-ai.md` · `implementation/ai-substance/` |
| 5-minute script | `submission/pitch/FINAL-5-MINUTE-SCRIPT.md` |
| Judge answers | `submission/pitch/JUDGE-ANSWER-BOOK.md` |
| Video checklist | `submission/pitch/VIDEO-RECORDING-CHECKLIST.md` |
