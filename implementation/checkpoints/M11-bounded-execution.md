# M11 Checkpoint — Bounded Recovery Execution Simulator

**Milestone:** M11 — Bounded Recovery Execution (EXECUTE)  
**Date:** 2026-08-23  
**Status:** COMPLETE

---

## Purpose

First milestone permitted to **act**. Answers: *“What actually happens when an authorized recovery action is executed?”* — simulation only, oracle at adapter boundary, no benchmark claims.

---

## Execution architecture

```text
ExecutionAuthorization (AUTHORIZED only)
        ↓
mint_authorised_action() → AuthorisedAction
        ↓
ExecutionAgent.execute() / execute_authorization()
        ↓
AuditJournal ACTION_INTENT (before effect)
        ↓
Simulated adapter (revive.execution.adapters.simulated)
        ↓
resolve_outcome() — oracle boundary only here
        ↓
ReservationLedger commit/release
        ↓
Observable ExecutionResult + RealizedOutcome
        ↓
AuditJournal ACTION_RESULT
```

Package: `revive/execution/`

---

## Action adapters

| Family | Actions | Oracle |
|--------|---------|--------|
| Payment | A01, A02 | `resolve_outcome` |
| Message | A03–A11 | `resolve_outcome` |
| Voice | A12 | `resolve_outcome` |
| Human | A13, A14 | `resolve_outcome` |

Adapters are **not exported** from `revive.execution`; integrity test asserts no decision-path import.

---

## Authorization requirement

- Only `AuthorizationState.AUTHORIZED` executes via `AuthorisedAction`
- `BLOCKED`, `STALE`, `EXPIRED`, `REQUIRES_HUMAN_APPROVAL`, `REPLAN_REQUIRED` → `ExecutionStage.CANCELLED`
- `mint_authorised_action()` raises on non-AUTHORIZED
- No action substitution — exact `authorized_parameters` forwarded to oracle

---

## Oracle interaction

- Oracle consulted only in `revive.execution.adapters.simulated`
- Decision path modules unchanged — no oracle imports
- Observable `RealizedOutcome` only — no oracle row, latent traits, or fatigue internals on result
- Same action + different hidden partition state → different observable outcomes (tested)

---

## State transitions

- Opportunity: `AUTHORISED → ACTING → AWAITING_OUTCOME → RECOVERED|PRICED`
- Intervention: `INTENDED → IN_FLIGHT → COMPLETED_*|UNKNOWN`
- Illegal transitions avoided via `revive.state.transitions` tables

---

## Idempotency

- `ExecutionStore` claims `idempotency_key` from M9/M10
- Duplicate invocation returns stored result with `duplicate=True`
- `SCHEDULED` placeholder upgraded to final result at scheduled virtual time
- Expired scheduled auth supersedes `SCHEDULED` with `CANCELLED` rejection

---

## Resource consumption

- `ReservationLedger.commit()` added (`ReservationStatus.COMMITTED`)
- Execution verifies active reservation before effect
- `RESERVATION_INVALID` if no active reservation
- Commit/release per docs/15 §5 outcome taxonomy

---

## Cost realization

- `predicted_cost_paise` / `predicted_enrv_paise` from M7 valuation — never overwritten
- `realized_cost_paise` recorded separately on `ExecutionResult`
- Incentive released on failure paths per settlement rules

---

## Failure handling

| Failure | Behavior |
|---------|----------|
| Not authorized | CANCELLED, no oracle call |
| Authorization expired | CANCELLED before adapter |
| Invalid reservation | CANCELLED |
| Adapter FAILED_* | Typed result, ledger settled |
| TIMEOUT_UNKNOWN | UNKNOWN intervention, RECONCILING opportunity path |

No executor-initiated retries (RS-8).

---

## Delayed actions (A02)

- Schedules at `earliest_eligible_at_micros` or `delay_minutes`
- Returns `ExecutionStage.SCHEDULED` without oracle call before time
- Completes when virtual clock ≥ scheduled time (if auth still valid)
- Authorization TTL must cover scheduled time (15 min default TTL documented)

---

## Audit events

- `AuditJournal` — append-only hash-chained records
- `ACTION_INTENT` written before adapter invoke
- `ACTION_RESULT` after typed adapter result
- Audit unwritable → execution halts (RuntimeError)

---

## Tests

| Area | File |
|------|------|
| Authorization gate | `test_authorization_requirement.py` |
| Idempotency + resources | `test_idempotency.py` |
| Delayed + oracle boundary | `test_delayed_and_oracle.py` |
| Adapter isolation | `test_integrity.py` |

**17 new tests** — full suite **187 passing**.

---

## Results

- [x] Only AUTHORIZED actions execute
- [x] No action substitution
- [x] Simulated adapters + oracle boundary
- [x] Idempotent execution
- [x] Resource commit safe
- [x] Realized cost separate from prediction
- [x] Delayed A02 scheduling
- [x] Execution windows / expiry enforced
- [x] Legal state transitions
- [x] Auditable intent + result
- [x] No autonomous retry loops
- [x] No real Razorpay / UI / benchmark

---

## Known limitations

- Simulated adapters only — no production rails
- `reconcile()` shape present; full reconciliation loop deferred
- Default authorization TTL (15 min) shorter than some delayed-retry windows — callers must extend via `PolicyRules`
- Human escalation uses oracle model only — no real queue

---

## Deviations

None material. `SCHEDULED` placeholder stored under same idempotency key with upgrade path at completion.

---

## Deferred decisions

- Real adapter implementations
- M12 outcome measurement horizon
- Concurrent execution (design supports idempotent store; default serial)

---

## Next milestone

**M12 — MEASURE** (not started). M11 STOP.
