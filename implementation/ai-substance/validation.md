# P12 — Final AI validation report

**Date:** 2026-08-28  
**Scope:** Product sandbox only · official benchmark untouched  
**Commit:** none (local validation freeze)

---

## P0 — Secret handling

| Check | Result |
|---|---|
| Exposed chat key treated as compromised | **DOCUMENTED** — owner must rotate in Groq console |
| Key in Git / README / frontend / tests | **NONE** |
| Key source | `GROQ_API_KEY` environment variable only (`revive/product/intelligence/config.py`) |
| API responses leak key | **NO** — covered by `test_ai_diagnosis_endpoint_never_leaks_key` |
| Error messages leak key | **NO** — `test_groq_error_never_contains_api_key` |

Documentation references only: “Groq API key must be supplied through `GROQ_API_KEY`.”

---

## AI contract audit (`revive/product/intelligence/`)

| Mechanism | Actual behavior |
|---|---|
| Timeout | 12.0s (`REQUEST_TIMEOUT_S`) |
| Retry | 2 retries (`MAX_RETRIES`), 0.25s × attempt backoff |
| Structured output | Groq `json_schema` strict + `parse_proposal()` validation |
| Invalid schema / cause / action | → `AI_UNAVAILABLE` + deterministic fallback |
| Cache | One entry per opportunity; cleared on `POST /api/recovery-run` |
| Fallback without key | `DETERMINISTIC_FALLBACK`, no crash, no fake Groq label |

---

## Trust boundaries (tests)

| Boundary | Test | Result |
|---|---|---|
| Economic | `test_economic_boundary_ai_proposal_does_not_override_engine` | AI A01 · engine A09 · engine wins |
| Safety / policy | `test_safety_boundary_ai_cannot_override_blocked_opportunity` | Blocked opp stays BLOCKED |
| Authorization | `test_authorization_boundary_no_execution_when_blocked` | No execution object on trace |
| Execution path | `test_intelligence_module_has_no_execution_imports` | No adapter/simulator imports |
| Endpoint isolation | `test_ai_diagnosis_endpoint_does_not_execute` | POST diagnosis does not execute |

---

## Failure matrix

| Mode | Status | Safe? |
|---|---|---|
| Missing `GROQ_API_KEY` | `DETERMINISTIC_FALLBACK` | Yes |
| Provider / HTTP error | `AI_UNAVAILABLE` | Yes |
| Invalid cause / action | `AI_UNAVAILABLE` | Yes |
| Malformed JSON | `AI_UNAVAILABLE` | Yes |
| Blocked + AI proposal | Engine state unchanged | Yes |

---

## Latency (local, no live Groq in CI)

| Path | Measurement |
|---|---|
| Deterministic fallback × 20 | < 2.0s (`test_fallback_latency_bounded`) |
| Cache hit | No second `diagnose_opportunity` call (`test_ai_diagnosis_cache_prevents_repeat_calls`) |
| Live Groq | Owner validates with rotated key; 12s cap prevents Control Room hang |

Demo note: first Analyze on an opportunity may await Groq (≤12s). Repeat views use server cache.

---

## UI / API evidence

| Surface | Trust boundary visible? |
|---|---|
| Workspace `#/opportunity/{id}` | **AI diagnosis** panel separate from **PAYVANTA economic decision** |
| Control Room | Intelligence chip (status only) |
| System `#/system` | Provider · model · execution authority **None** |
| Receipt | `intelligence` block when diagnosis cached |
| Audit | `AI_DIAGNOSIS_COMPLETED` in `intelligence_events` |

---

## Benchmark isolation

```bash
git diff -- revive/benchmark/official/
git diff -- artefacts/benchmark/official-cloud-final/
```

Both: **no output**. No Groq references under `revive/benchmark/`.

---

## Language discipline

| Correct | Incorrect |
|---|---|
| Sandbox: optional Groq contextual diagnosis | “600 AI evaluations” |
| Official: frozen deterministic engine, `LLM_OFF` | “LLM-powered benchmark” |
| `intelligence.engine_llm_used: false` | Claiming engine uses LLM |

---

## Remaining manual steps

1. Rotate compromised Groq key externally
2. Live browser pass with rotated key (Analyze → AI panel → economic decision)
3. Record 5-minute pitch video (AI moment ~0:40)
4. Commit/push when owner approves
