# Claim → evidence matrix

Every public claim names a source. UI copy that is not a measured figure may be
static. Measured money, cell counts, and validation states are not.

| Claim | Actual source | Implementation | Test | UI | API |
|---|---|---|---|---|---|
| PAYVANTA is a revenue recovery OS | Product session + Control Room | `revive/product/` | `tests/product/test_overview.py` | `#/control` | `GET /api/product/overview` |
| Environment is SANDBOX | Session fixture | `revive/product/session.py` | `test_overview_matches_sandbox_snapshot` | topbar · `#/system` | `overview.environment.kind` |
| Detect revenue at risk | Sentinel | `revive/recovery/sentinel/` | `tests/recovery/test_sentinel_recall.py` | Control Room · Opportunities | `GET /api/snapshot` |
| Determine the right intervention | Candidates + ENRV + allocator | `revive/recovery/candidates/`, `.../valuation/`, `revive/decision/` | `tests/recovery/test_valuation_enrv.py`, allocator tests | Recovery Lab | `GET /api/opportunity/{id}` |
| Bounded execution | Authorization required | `revive/execution/`, `revive/policy/authorize.py` | `tests/execution/test_authorization_requirement.py` | Execution · Receipt | `overview.guardrails.execution_integrity` |
| Cannot execute without AUTHORIZED | Gate | `execute_authorization` | `test_authorization_requirement.py` | Guardrails | opportunity `authorization_state` |
| Duplicate execution blocked | Idempotency key | `revive/execution/` | `tests/execution/test_idempotency.py` | Receipt | `execution.idempotency_key` |
| Stopping rules | Policy stopping evaluator | `revive/policy/` | `tests/policy/test_authorization_demo.py` | Guardrails | `guardrails.stopping_fired` |
| Compliant escalation | `REQUIRES_HUMAN_APPROVAL` | `revive/policy/authorize.py` | `tests/policy/test_authorization_demo.py` | blocked opportunity | `authorization_state` |
| Audit trail | Journal before/around effects | `revive/audit/` | `tests/execution/test_integrity.py::test_audit_intent_before_result` | `#/audit` | `GET /api/audit` |
| Batch measurement | Cycle runner + measurement | `revive/measurement/` | `tests/measurement/`, product session | Control Room money pillar | `overview.financial` |
| Incremental net (sandbox) | Engine on this session | `control_room.hero` | `test_overview_matches_sandbox_snapshot` | `#/control` | `financial.incremental_net_recovery` |
| Incremental net (official) | M-10 vs B0 | `docs/21-evaluation.md`, cell artefacts | `test_cell_lookup_abundant_revive_seed_14` | `#/benchmark/matrix` | `GET /api/benchmark/official/cell/{seed}/{profile}/{policy}` |
| 600 official cells | Frozen tree | `artefacts/benchmark/official-cloud-final/` | `test_verify_evidence_passes` | `#/benchmark` | `GET /api/benchmark/official/contract` |
| BENCHMARK_VALID · blocked=false | `validation.json` + manifest | official evidence reader | `test_summary_provenance_fields` | `#/benchmark/evidence` | official summary |
| Official evidence is read-only | HTTP 405 on writes | `PayvantaHandler._reject_official_write` | `tests/product/test_submission_redteam.py` | Benchmark Lab | POST/PUT/PATCH/DELETE `/api/benchmark/official*` |
| Sandbox ≠ official cell | Integrity flags | `overview.integrity` | `test_overview_matches_sandbox_snapshot` | `#/system` | `sandbox_is_not_official_evidence` |
| LLM is off | Diagnosis + official config | `diagnose.py` `llm_used=False`; `LLM_MODE_OFFICIAL` | diagnosis tests; official config | System / why-ai | `overview.intelligence.llm_used` |
| Frozen experiment hash | Manifest | `DECLARED_FROZEN_EXPERIMENT` | verification `frozen_experiment_hash` | Forensics | `contract.frozen_experiment_hash` |

Do not claim: scientifically proven, production proven, guaranteed recovery,
600 cells prove superiority, two LLM agents in this build.
