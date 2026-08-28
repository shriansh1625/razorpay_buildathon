# Track 03 evidence

Official bar: **detect revenue at risk → determine the right intervention →
execute a bounded recovery workflow**, with **measured money recovered across a
batch**, **compliant escalation**, **stopping rules**, and an **audit trail**.

No extra invented criteria.

| Requirement | Implementation | Test | UI | API |
|---|---|---|---|---|
| **DETECT REVENUE AT RISK** | `revive/recovery/sentinel/` — Revenue Sentinel classifies economic leakage into opportunities | `tests/recovery/test_sentinel_recall.py`, `tests/recovery/test_sentinel_integrity.py` | Control Room opportunities · `#/opportunities` | `GET /api/snapshot` |
| **DETERMINE INTERVENTION** | Context + diagnosis → candidate catalogue → ENRV → Lagrangian allocation | `tests/recovery/test_candidate_generation_RR-FUNC-020.py`, `tests/recovery/test_valuation_enrv.py` | Analyze · Recovery Lab · recommendation | `GET /api/opportunity/{id}` |
| **BOUNDED EXECUTION** | 12-gate PolicyPack; `execute_authorization` requires `AUTHORIZED`; simulated adapters | `tests/execution/test_authorization_requirement.py`, `tests/execution/test_idempotency.py` | Guardrails · Authorization · Execution | `overview.guardrails` |
| **BATCH MEASUREMENT** | Cycle over the opportunity pool; incremental vs natural vs cost; Control Room aggregates this sandbox batch | `tests/measurement/`; `tests/product/test_overview.py` | Control Room money pillar (sandbox). Official M-10 in Benchmark Lab | `GET /api/product/overview` |
| **ESCALATION** | Gate → `REQUIRES_HUMAN_APPROVAL` or `BLOCKED`; no adapter call | `tests/policy/test_authorization_demo.py` | Prepared blocked: `opp_WST4PPPH81VPNTNC18K0YGRAW9` | `authorization_state` |
| **STOPPING RULES** | Stopping evaluator; fired rules override high ENRV | `tests/policy/test_authorization_demo.py::` stopping assertions; `test_stopping_overrides_high_enrv` | Guardrails · stopping block | `guardrails.stopping_fired` |
| **AUDIT TRAIL** | `AuditJournal` — intent before irreversible result | `tests/execution/test_integrity.py::test_audit_intent_before_result` | `#/audit` · receipt `audit_reference` | `GET /api/audit` |
| **MEANINGFUL AI / AGENT** | Bounded recovery agent: diagnosis (`rank_causes`) → ENRV → Lagrangian allocation → gated execution. **No LLM.** Decision intelligence + orchestration satisfy Track 03 “agent” honestly. | `tests/recovery/test_valuation_enrv.py`, allocator tests, `tests/product/test_overview.py` (`intelligence.llm_used=false`) | Workspace Analyze · Recovery Lab · Guardrails · `#/system` intelligence block | `GET /api/product/overview` → `intelligence`, `track03` |

**Process (Razorpay):** public repository · 5-minute pitch · architecture.

| Process item | Where | Status |
|---|---|---|
| Public repository | https://github.com/shriansh1625/razorpay_buildathon | **Public** — PAYVANTA product on `main` |
| 5-minute pitch | `submission/pitch/FINAL-5-MINUTE-SCRIPT.md` | Script ready; **video not yet recorded** |
| Architecture | `docs/43-operating-architecture.md` | Published |

Official **measured** evidence for the engine: 600 frozen cells
(`docs/42-official-benchmark.md`). Sandbox batch money is a demonstration of the
same engine, not those cells.
