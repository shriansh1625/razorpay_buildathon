# Track 03 evidence

Official bar: **detect revenue at risk → determine the right intervention →
execute a bounded recovery workflow**, with **measured money recovered across a
batch**, **compliant escalation**, **stopping rules**, and an **audit trail**.

No extra invented criteria.

| Requirement | Implementation | Test | UI |
|---|---|---|---|
| **DETECT REVENUE AT RISK** | `revive/recovery/sentinel/` — Revenue Sentinel classifies economic leakage into opportunities | `tests/recovery/test_sentinel_recall.py`, `tests/recovery/test_sentinel_integrity.py` | Control Room opportunities · `#/opportunities` |
| **DETERMINE INTERVENTION** | Context + diagnosis → candidate catalogue → ENRV → Lagrangian allocation | `tests/recovery/test_candidate_generation_RR-FUNC-020.py`, `tests/recovery/test_valuation_enrv.py` | Analyze · Recovery Lab · recommendation |
| **BOUNDED EXECUTION** | 12-gate PolicyPack; `execute_authorization` requires `AUTHORIZED`; simulated adapters | `tests/execution/test_authorization_requirement.py`, `tests/execution/test_idempotency.py` | Guardrails · Authorization · Execution |
| **BATCH MEASUREMENT** | Cycle over the opportunity pool; incremental vs natural vs cost; Control Room aggregates this sandbox batch | `tests/measurement/`; `tests/product/test_overview.py` | Control Room money pillar (sandbox). Official M-10 in Benchmark Lab |
| **ESCALATION** | Gate → `REQUIRES_HUMAN_APPROVAL` or `BLOCKED`; no adapter call | `tests/policy/test_authorization_demo.py` | Prepared blocked: `opp_WST4PPPH81VPNTNC18K0YGRAW9` |
| **STOPPING RULES** | Stopping evaluator; fired rules override high ENRV | `tests/policy/test_authorization_demo.py::` stopping assertions; `test_stopping_overrides_high_enrv` | Guardrails · stopping block |
| **AUDIT TRAIL** | `AuditJournal` — intent before irreversible result | `tests/execution/test_integrity.py::test_audit_intent_before_result` | `#/audit` · receipt `audit_reference` |

**Process (Razorpay):** public repository · 5-minute pitch · architecture.

| Process item | Where | Status in this working tree |
|---|---|---|
| Public repository | GitHub `shriansh1625/razorpay_buildathon` | **P0 open** — logged-out 404; origin lacks `revive/product/` |
| 5-minute pitch | `submission/pitch/` | Script packaged; video file not produced here |
| Architecture | `docs/07-system-architecture.md`, `docs/43-operating-architecture.md` | Written |

Official **measured** evidence for the engine: 600 frozen cells
(`docs/42-official-benchmark.md`). Sandbox batch money is a demonstration of the
same engine, not those cells.
