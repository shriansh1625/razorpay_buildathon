# M6 Checkpoint — Candidate Recovery Actions

**Milestone:** M6 — Candidate Recovery Action Space (SIMULATE feasibility)  
**Date:** 2026-08-22  
**Status:** COMPLETE

---

## Purpose

Given M4 opportunity + M5 context and diagnosis, enumerate **feasible** recovery actions with prerequisites, timing, resource requirements, and policy constraints. M6 does **not** rank actions, compute ENRV, or select a decision.

---

## Candidate action vocabulary

Authoritative closed set: `ActionCode` A00–A14 from docs/11 §3 (`revive/domain/enums.py`).

| Code | Action |
|------|--------|
| A00 | NO_ACTION |
| A01 | RETRY_PAYMENT_NOW |
| A02 | RETRY_PAYMENT_SCHEDULED |
| A03 | REQUEST_INSTRUMENT_UPDATE |
| A04–A09 | Comms / checkout / dunning |
| A10–A11 | Incentives |
| A12 | VOICE_OUTREACH |
| A13–A14 | Human escalation |

---

## Input contract

| Input | Source |
|-------|--------|
| `DetectedOpportunity` | M4 Sentinel |
| `ContextObject` | M5 context assembly |
| `Diagnosis` | M5 diagnosis |
| `now_micros` | Virtual clock |
| `PolicyPack` | `revive/config/policy_pack.py` (metadata overlays config) |
| `CandidateCapacityContext` | Optional cycle capacity snapshot |
| `cycle_id` | Optional |

---

## Output contract

`CandidateSetResult` with `RecoveryCandidate` rows:

- `candidate_id` (deterministic)
- `action_code`, `params` (delay_minutes, channel, incentive_tier)
- `availability_status`: `AVAILABLE` | `INELIGIBLE` | `TEMPORARILY_UNAVAILABLE` | `IMPOSSIBLE`
- `prerequisites_satisfied` / `prerequisites_failed`
- `resource_requirements` (retry_slots, message_capacity, etc.)
- `nominal_cost_paise` (documented direct cost — not ENRV)
- `earliest_eligible_at_micros`
- `approval_required`
- `reason_codes`, `provenance`

Entry point: `generate_candidates(...)` / `simulate(...)`

---

## Feasibility model

Layered evaluation in `feasibility.py`:

1. Action exists in catalogue
2. Risk-class + cause compatibility (`rules.py`, docs/12 §8.3)
3. Recovery window / addressability
4. Retry attempts, instrument state
5. Communication window + contact caps
6. Incentive policy bounds
7. Optional capacity snapshot

---

## Availability states

| State | Meaning |
|-------|---------|
| `AVAILABLE` | Eligible for downstream evaluation |
| `INELIGIBLE` | Policy/business rule blocks (e.g. contact window closed) |
| `TEMPORARILY_UNAVAILABLE` | Valid but capacity exhausted this cycle |
| `IMPOSSIBLE` | Cannot apply to this opportunity (e.g. window expired) |

---

## Resource requirements

From docs/11 catalogue (`catalogue.py`): `retry_slots`, `message_capacity`, `contact_allowance`, `incentive_budget`, `voice_minutes`, `human_review_slots`.

---

## Policy integration

`CandidateConfig` with provisional defaults; `PolicyPack.metadata` may override windows, caps, approval thresholds. No gate execution — feasibility-only checks.

---

## Approval model

`approval_required=True` when value ≥ threshold or human/incentive actions warrant it (provisional). M6 does not queue or resolve approvals.

---

## NO_ACTION semantics

`A00` always enumerated. Available for addressable and non-addressable opportunities; sole feasible option when not addressable.

---

## Oracle boundary

- Package under `revive.recovery` (decision-path import guard)
- Adversarial test: identical candidate sets when hidden oracle fields injected into view
- No ENRV, uplift, or prediction fields on output

---

## Determinism

Same opportunity + context + diagnosis + policy + time → identical `candidate_id` set and payloads.

---

## Tests

`tests/recovery/`:

- `test_candidate_generation_RR-FUNC-020.py` — count, NO_ACTION, class/cause-aware sets
- `test_candidate_feasibility.py` — retries, contact window, capacity, approval
- `test_candidate_integrity.py` — oracle isolation, no value leakage, policy neutrality

**Result:** 122 passed (full suite)

---

## Known limitations

- Gate suite (G1–G12) not executed — feasibility approximates documented constraints
- `PolicyPack` skeleton only; full sealed pack deferred
- Voice (A12) enumerated but not fixture-tested on all risk classes
- Capacity context is optional snapshot, not ledger-backed

---

## Provisional values

Communication window 9–19, max 5 retries, contact caps, incentive 5% of V / 5000 paise max, approval threshold 50_000 paise — in `CandidateConfig`.

---

## Deviations

None vs docs/11 action codes. M6 prompt vocabulary (IMMEDIATE_RETRY, etc.) mapped to authoritative `ActionCode` enum.

---

## Deferred

- M7 ENRV / prediction / uplift
- M8+ allocation, gates execution, learning
- LLM copy generation

---

## Next milestone

**M7 — Economic evaluation (pricing)** — NOT AUTHORIZED.

> M6 answers “what could be done?” — not “what is worth doing?”
