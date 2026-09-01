# Razorpay submission form — P16 draft

**Do not submit automatically.** Video is still required.

## Project name / title

**PAYVANTA — Autonomous Revenue Recovery Intelligence**

Keep PAYVANTA. Add the category so a time-poor judge does not need the README first line.

## GitHub URL

https://github.com/shriansh1625/razorpay_buildathon

## Project objectives (~110 words)

PAYVANTA is a bounded revenue recovery system for merchant revenue operations. It detects typed revenue at risk, prices each intervention against doing nothing (incremental net recovery, not gross collections), allocates under capacity and policy constraints, and executes only after deterministic guardrails and authorization. Optional Groq GPT-OSS 120B interprets sandbox context and proposes causes and candidates; it has no execution authority. The same engine is evaluated separately across a frozen 20×6×5 official experiment (600 cells, LLM_OFF). This submission does not claim live Razorpay integration, production fitness, or universal superiority.

## 5-minute pitch

Record using `submission/pitch/FINAL-5-MINUTE-SCRIPT.md`. Do not press Run Recovery. Mount official artefacts before opening the matrix.

## Build challenges (M13.25 + M13.27 only)

**Checkpoint / manifest drift (M13.25).** Cells wrote atomically, but the manifest advanced only after a full 5-policy group. A crash left 4/5 cell files with the manifest still behind. Diagnosis: parent-owned checkpoint updates plus startup reconciliation (files-ahead, manifest-ahead, corrupt cell, partial group). Result: resume became a verified invariant, not a hope.

**Metrics-tail scan (M13.27).** Aggregation was O(authorization × execution): an unauthorized cross-scan on large ABUNDANT cells. Diagnosis: indexed aggregation. Semantics unchanged. Local scan ~4137.6s → ~0.321s; a production-shaped cloud cell ~9900s → ~627.3s. That is performance engineering, not an M-10 score change.

## GitHub metadata (manual)

See `submission/GITHUB-METADATA.md`. Do not add `agentic-ai`.
