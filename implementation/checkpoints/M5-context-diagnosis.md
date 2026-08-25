# M5 Checkpoint — Context + Diagnosis

**Milestone:** M5 — Context + Diagnosis (UNDERSTAND)  
**Date:** 2026-08-21  
**Status:** COMPLETE

---

## Purpose

Given an M4 `DetectedOpportunity`, assemble observable context and produce a structured, action-agnostic diagnosis explaining **why** revenue appears at risk. M5 does not select recovery actions, compute ENRV, or allocate effort.

---

## Inputs

| Input | Source |
|-------|--------|
| `DetectedOpportunity` | M4 Sentinel (`detect()`) |
| `ObservableWorldView` | M2 observation interface |
| `now_micros` | Virtual clock |
| Optional `cycle_id` | Downstream cycle identity |

---

## Outputs

| Output | Location | Schema |
|--------|----------|--------|
| `ContextObject` | `revive/recovery/context/models.py` | Customer, fatigue, instrument, payment, checkout, subscription, receivable, temporal, degradation sub-contexts + evidence |
| `Diagnosis` | `revive/recovery/diagnosis/models.py` | `ranked_causes[]`, `unclassified`, bands only, evidence refs, provenance |

Entry points:

- `assemble_context(opportunity, view, now_micros) -> ContextObject`
- `diagnose(opportunity, context, view, now_micros, cycle_id) -> Diagnosis`
- `understand(opportunity, view, now_micros, cycle_id) -> Diagnosis` (context + diagnosis)

---

## Context sources

| Category | Observable fields |
|----------|-------------------|
| Customer | segment, tenure, value band, payment success/failure counts, success rate, prior contacts |
| Fatigue | contacts_last_7d/30d, fatigue band (from opportunity contact history in view) |
| Instrument | method, expiry, block state, instrument-level success rate |
| Payment | failure txn, reason code, attempt seq, failure cluster, degradation observation |
| Checkout | cart value, stage, elapsed time, payment initiation, prior abandonments |
| Subscription/Mandate | cycle state, debit history, mandate state/expiry |
| Receivable | outstanding, ageing bucket/days, prior overdue count |
| Temporal | time since event/success/failure, merchant-local hour, window close |
| Degradation | M4 flag + observable method failure rate vs baseline |

---

## Diagnostic taxonomy

Closed set from docs/12 §8.1 — `CauseCode` enum in `revive/domain/enums.py`.  
Deterministic raw-reason mapping in `revive/recovery/diagnosis/mapping.py` (`RR-FUNC-011`).  
Unmapped values → `UNCLASSIFIED`; never invent codes.

Class-specific rule ranking in `revive/recovery/diagnosis/rules.py`:

| Scenario | Primary candidate cause(s) |
|----------|---------------------------|
| Payment + degradation spike | `ISSUER_DOWNTIME` (+ mapped reason if present) |
| Payment + mapped reason | e.g. `INSUFFICIENT_FUNDS`, `CARD_EXPIRED`, `GATEWAY_TIMEOUT` |
| Checkout abandonment | `CHECKOUT_STEP_FRICTION`, `AUTH_ABANDONED_BY_CUSTOMER`, `SESSION_INTERRUPTED` |
| Subscription mandate revoked | `MANDATE_REVOKED` |
| Receivable ageing | `BUYER_CASHFLOW_CONSTRAINT`, `OVERSIGHT_OR_FORGOTTEN` (LOW band) |
| Insufficient evidence | `UNCLASSIFIED` |

---

## Evidence model

`ContextEvidence` and `RankedCause` distinguish:

| Kind | Meaning |
|------|---------|
| `FACT` | Directly observed (e.g. reason_code, transaction row) |
| `PATTERN` | Statistical/temporal (e.g. failure cluster, degradation rate) |
| `LIKELY_CAUSE` | Interpretation supported by facts (via ranked cause) |
| `UNKNOWN` | Cannot determine from available data |

Each ranked cause carries `evidence_refs`, `supporting_features`, and `contradicting_features`.

---

## Uncertainty model

- Confidence **bands only**: `LOW`, `MED`, `HIGH` — no numeric confidence on `Diagnosis` (`RR-GUARD-020`)
- `unclassified=True` when only `UNCLASSIFIED` causes remain
- `Diagnosis.uncertainty` property: `UNKNOWN`, `HEURISTIC_CONFIDENCE` (LOW band), or band value
- `context_degraded` flag when material context fields are missing

---

## Oracle boundary

- Lives under `revive.recovery` (decision-path import guard unchanged)
- No import of `revive.simulation.oracle`, `_partition`, or `latent`
- Diagnosis identical when hidden degradation windows / oracle fields injected into view
- `ContextObject.hidden_keys()` and `Diagnosis.hidden_keys()` scan outputs

---

## Action-agnostic guarantee

Diagnosis outputs ranked **candidate causes** only. No `ActionCode`, ENRV, retry schedule, or channel selection. Verified by tests and code inspection.

---

## Tests

`tests/recovery/`:

- `test_context_assembly_RR-FUNC-013.py` — context completeness, temporal, degradation interpretation
- `test_diagnosis_RR-FUNC-010.py` — taxonomy, six fixture scenarios, vocabulary, no numeric confidence
- `test_diagnosis_integrity.py` — oracle isolation, determinism, adversarial hidden-state, contradicting evidence

**Result:** 105 passed (full suite)

---

## Known limitations

- LLM-assisted diagnosis path not implemented (M5 deterministic-only; `allow_llm=False`)
- Fatigue derived from observable `opportunities.contacts_made` in view, not a separate intervention table
- Merchant-local timing uses deterministic timezone offset heuristic (not full tz database)
- History windows are configurable assumptions documented in `ContextConfig`, not PolicyPack-sealed
- Subscription debit stats link via order_id substring match when explicit subscription ref absent on txn

---

## Assumptions

- Customer history window: 90 days (provisional)
- Degradation context reuses M4 observable parameters (90 min, ≥3 attempts, ≥60% failure rate)
- Baseline merchant failure rate fallback: 0.15 when insufficient attempts in window
- Instrument “healthy” contradicting evidence: success rate ≥ 0.7 with ≥ 3 successes

---

## Deviations

None vs frozen docs semantics. M5 prompt conceptual categories (e.g. `TEMPORARY_PAYMENT_DEGRADATION`) mapped to authoritative docs/12 `CauseCode` values (e.g. `ISSUER_DOWNTIME`).

---

## Deferred

- M6 candidate action generation
- ENRV / counterfactuals (M7+)
- LLM diagnosis ranking (optional P1)
- Full ContactLedger integration for fatigue (when execution layer exists)

---

## Next milestone

**M6 — Candidate actions** — NOT AUTHORIZED.

> M5 answers “why might this revenue be at risk?” — not “how should we recover it?”
