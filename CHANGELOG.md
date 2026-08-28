# Changelog — PAYVANTA

## Final submission (2026-08-28)

### Product

- **PAYVANTA Control Room** — sandbox UI + stdlib HTTP API (`revive control-room`)
- **Recovery workflow** — detect → diagnose → counterfactual → optimize → guard → authorize → execute → measure → audit
- **Prepared demo state** — SANDBOX · seed 14; success `opp_CQ6VCH7HPPW9WG284G5EFRMDN0`; blocked `opp_WST4PPPH81VPNTNC18K0YGRAW9`
- **Machine-readable overview** — `GET /api/product/overview` for human and AI evaluators

### Safety & bounded execution

- 12-gate PolicyPack; execution requires `AUTHORIZED`
- Stopping rules override high ENRV
- Idempotent execution; hash-chained audit (`ACTION_INTENT` before effect)
- Official benchmark endpoints reject POST/PUT/PATCH/DELETE

### Benchmark evidence (read-only)

- Official 600-cell experiment contract exposed via Benchmark Lab
- M-10 incremental net vs B0; ABUNDANT × REVIVE × seed 14 drilldown
- `artefacts/benchmark/official-cloud-final/` gitignored; mount locally to verify

### Performance engineering (not M-10 score changes)

| Milestone | Result |
|---|---|
| M13.24 | Parallel worker dispatch repaired |
| M13.25 | Checkpoint reconciliation hardened |
| M13.26 | ABUNDANT/REVIVE forensic profiling |
| M13.27 | Metrics-tail ~4137.6s → ~0.321s local / ~0.39s cloud |
| Cloud validation | Cell ~9900s → ~627.3s; checksum verified |

### AI honesty

- `llm_used=False`; official benchmark `LLM_OFF`
- Decision intelligence is deterministic; no chatbot in shipped runtime
- `docs/why-ai.md` explains agentic orchestration vs LLM

### Public reproducibility

- Public repository: https://github.com/shriansh1625/razorpay_buildathon
- Fresh clone: `pip install -e ".[dev]"` → `revive control-room`
- 34 product tests in `tests/product/`
