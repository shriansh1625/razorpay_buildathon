# 34 · State Machines

Every entity that can be observed mid-flight has an explicit state machine with a legal-transition
table. `RR-NFR-043` requires that illegal transitions raise rather than being silently absorbed —
a state machine that permits anything documents nothing.

Five machines: **Opportunity**, **Intervention**, **ApprovalRequest**, **ReservationHandle**, and
**Cycle/Run**. `Decision` has no machine: decisions are immutable
([09 § 4](09-decision-engine.md)).

---

## 1. Opportunity

The central lifecycle. Fourteen states.

### 1.1 States

| State | Meaning | Terminal? |
|---|---|---|
| `DETECTED` | Created and valued; not yet diagnosed | no |
| `NOT_ADDRESSABLE` | Detected and valued, but no action is permissible or possible | no (re-enterable) |
| `DIAGNOSED` | Candidate causes ranked | no |
| `PRICED` | Candidates generated, predicted, priced | no |
| `AWAITING_APPROVAL` | An action requires a human decision | no |
| `AUTHORISED` | An action has an `ALLOW` verdict and a held reservation | no |
| `ACTING` | Adapter invocation in flight | no |
| `AWAITING_OUTCOME` | Action executed; outcome not yet observed within `H` | no |
| `RECONCILING` | An action returned `TIMEOUT_UNKNOWN`; effect unknown | no |
| `RECONCILIATION_FAILED` | Reconciliation exhausted; escalated to a human | **yes** |
| `DEFERRED` | Priced with positive `ENRV` but not actioned this cycle | no |
| `NO_ACTION_CYCLE` | Priced; `∅` was the best option this cycle | no |
| `RECOVERED` | Full recoverable amount observed as settled | **yes** |
| `STOPPED` | A stopping rule fired | **yes** (conditionally re-openable) |
| `CLOSED_UNRECOVERED` | Window expired or value became unrecoverable, without recovery | **yes** |

`NO_ACTION_CYCLE` and `DEFERRED` are per-cycle resting states, not terminal ones. An opportunity
oscillates between `PRICED` and one of them across cycles until it recovers, stops, or closes.

### 1.2 Legal transitions

| From | To | Trigger |
|---|---|---|
| — | `DETECTED` | Signal creates an opportunity |
| `DETECTED` | `NOT_ADDRESSABLE` | Addressability check fails (`RR-FUNC-008`) |
| `DETECTED` | `DIAGNOSED` | Diagnosis completes |
| `DETECTED` | `STOPPED` | Stopping rule at cycle start |
| `DETECTED` | `RECOVERED` | Success signal arrives before any decision |
| `NOT_ADDRESSABLE` | `DETECTED` | Addressability restored (consent granted, amount determined, flag cleared) |
| `NOT_ADDRESSABLE` | `CLOSED_UNRECOVERED` | Window expires while non-addressable |
| `NOT_ADDRESSABLE` | `RECOVERED` | Natural recovery |
| `DIAGNOSED` | `PRICED` | Candidates generated and priced |
| `DIAGNOSED` | `STOPPED` | Terminal cause (`SR-05`) |
| `PRICED` | `AUTHORISED` | Selected by allocator **and** gate `ALLOW` |
| `PRICED` | `AWAITING_APPROVAL` | Gate `REQUIRE_APPROVAL` (`G7`) |
| `PRICED` | `DEFERRED` | Selected but capacity/window refused, or gate `DEFER` |
| `PRICED` | `NO_ACTION_CYCLE` | `∅` chosen, or all candidates `≤ ε` |
| `PRICED` | `STOPPED` | Gate `DENY` triggering a stopping rule, or `SR-*` fires |
| `AWAITING_APPROVAL` | `AUTHORISED` | Approved and re-gated to `ALLOW` |
| `AWAITING_APPROVAL` | `PRICED` | Approved with modification → re-priced and re-gated (`RR-FUNC-066`) |
| `AWAITING_APPROVAL` | `DEFERRED` | Approval expired (`SR-06`) or rejected |
| `AWAITING_APPROVAL` | `STOPPED` | Stopping rule fires while queued |
| `AUTHORISED` | `ACTING` | Audit intent written; adapter invoked |
| `AUTHORISED` | `DEFERRED` | Pre-execution stopping re-evaluation fired (`RR-FUNC-051`); reservation released |
| `ACTING` | `AWAITING_OUTCOME` | Adapter returned `SUCCESS` / `FAILED_*` / `REJECTED_BY_PROVIDER` |
| `ACTING` | `RECONCILING` | Adapter returned `TIMEOUT_UNKNOWN` |
| `AWAITING_OUTCOME` | `RECOVERED` | Full amount observed within `H` |
| `AWAITING_OUTCOME` | `PRICED` | Horizon elapsed without full recovery; opportunity re-enters decisioning |
| `AWAITING_OUTCOME` | `STOPPED` | A stopping rule fires (caps, refusal, terminal cause) |
| `AWAITING_OUTCOME` | `CLOSED_UNRECOVERED` | Window expired (`SR-01`) |
| `RECONCILING` | `AWAITING_OUTCOME` | Reconciliation resolved to a definite result |
| `RECONCILING` | `RECONCILIATION_FAILED` | `max_reconcile_attempts` exhausted |
| `RECONCILING` | `RECOVERED` | Reconciliation revealed the payment succeeded |
| `DEFERRED` | `PRICED` | Next cycle, re-priced from current state |
| `DEFERRED` | `STOPPED` / `CLOSED_UNRECOVERED` / `RECOVERED` | As per the respective triggers |
| `NO_ACTION_CYCLE` | `PRICED` | Next cycle |
| `NO_ACTION_CYCLE` | `STOPPED` | `SR-07` after `N` consecutive such cycles |
| `NO_ACTION_CYCLE` | `RECOVERED` / `CLOSED_UNRECOVERED` | Natural recovery / window expiry |
| `STOPPED` | `PRICED` | **Re-open only** on an external material state change ([14 § 4.1](14-stopping-rules.md)) |

### 1.3 Explicitly illegal transitions

These are the ones a test suite asserts *cannot* happen. Each corresponds to a real failure mode.

| Illegal | Why it must be impossible |
|---|---|
| `PRICED` → `ACTING` | Skips the gate. Guardrail bypass |
| `AUTHORISED` → `AUTHORISED` | Double authorisation for one reservation |
| `ACTING` → `ACTING` | Double adapter invocation |
| `RECONCILING` → `AUTHORISED` / `ACTING` | Acting while the prior effect is unknown (`RR-FUNC-065`) |
| `RECONCILIATION_FAILED` → anything | Terminal; requires human out-of-band resolution |
| `RECOVERED` → anything | Terminal. A later payment is an over-payment, not a re-opening |
| `CLOSED_UNRECOVERED` → `PRICED` | The window cannot be re-opened by the system (`SR-01`) |
| `STOPPED` → `PRICED` **without** an external evidence reference | Self-authorised re-opening defeats stopping |
| `DEFERRED` → `ACTING` | Skips re-pricing and re-gating in the new cycle |
| `AWAITING_APPROVAL` → `ACTING` | Executing without the approval resolving |
| Any state → `RECOVERED` without an `OUTCOME_OBSERVED` audit event | Unevidenced recovery inflates metrics |

### 1.4 The cycle loop, drawn

```
                      ┌──────────────────────────────────────────┐
                      │                                          │
   DETECTED ─► DIAGNOSED ─► PRICED ─┬─► AUTHORISED ─► ACTING ─┬─► AWAITING_OUTCOME
       │            │          │    │        │                │        │  │
       │            │          │    │        └► DEFERRED      └► RECONCILING
       │            │          │    │              │                   │  │
       │            │          │    ├─► DEFERRED ──┘                   │  └─► RECOVERED
       │            │          │    ├─► NO_ACTION_CYCLE ───────────────┘
       │            │          │    └─► AWAITING_APPROVAL ──► (approve → AUTHORISED)
       │            │          │                              (modify  → PRICED)
       │            │          │                              (expire  → DEFERRED)
       │            │          │
       └────────────┴──────────┴──► STOPPED / CLOSED_UNRECOVERED / RECOVERED   (terminal)

   AWAITING_OUTCOME ──(horizon elapsed, not recovered)──► PRICED    ← the recovery loop
```

The arrow from `AWAITING_OUTCOME` back to `PRICED` is the loop that makes REVIVE iterative, and it is
bounded by exactly the five mechanisms in [14 § 9](14-stopping-rules.md).

---

## 2. Intervention

One row per executed action attempt. States are narrow because an intervention is nearly a record of
fact.

| State | Meaning | Terminal? |
|---|---|---|
| `INTENDED` | Idempotency key claimed, audit intent written, adapter not yet called | no |
| `IN_FLIGHT` | Adapter invoked | no |
| `COMPLETED_SUCCESS` | Adapter returned `SUCCESS` | yes |
| `COMPLETED_FAILED` | `FAILED_RETRYABLE`, `FAILED_TERMINAL`, or `REJECTED_BY_PROVIDER` | yes |
| `UNKNOWN` | `TIMEOUT_UNKNOWN` | no |
| `RESOLVED_BY_RECONCILIATION` | Reconciliation determined the true result | yes |
| `UNRESOLVED` | Reconciliation exhausted | yes (reported) |

Legal: `INTENDED → IN_FLIGHT → {COMPLETED_SUCCESS, COMPLETED_FAILED, UNKNOWN}`;
`UNKNOWN → {RESOLVED_BY_RECONCILIATION, UNRESOLVED}`.

Illegal, and asserted so: `INTENDED → COMPLETED_*` (no adapter call happened),
`COMPLETED_* → anything` (facts do not change), `UNKNOWN → IN_FLIGHT` (no re-invocation of a claimed
key), and any entry to `IN_FLIGHT` without a preceding `ACTION_INTENT` audit event.

---

## 3. ApprovalRequest

| State | Meaning | Terminal? |
|---|---|---|
| `QUEUED` | Awaiting a human | no |
| `APPROVED` | Approved as proposed | yes |
| `APPROVED_MODIFIED` | Approved with changed parameters; **re-enters all gates** | yes |
| `REJECTED` | Declined | yes |
| `EXPIRED` | Validity elapsed with no decision (`SR-06`) | yes |
| `VOIDED` | The underlying opportunity stopped, recovered, or the window closed while queued | yes |

Legal: `QUEUED → {APPROVED, APPROVED_MODIFIED, REJECTED, EXPIRED, VOIDED}`. No transitions out of any
terminal state.

Illegal: `EXPIRED → APPROVED` — **silence never becomes consent after the fact**. A late approval on an
expired request requires a fresh request in a later cycle.

---

## 4. ReservationHandle

Small, and the most safety-critical machine in the system.

| State | Meaning | Terminal? |
|---|---|---|
| `HELD` | Capacity reserved, not yet consumed | no |
| `COMMITTED` | Capacity consumed | yes |
| `RELEASED` | Capacity returned (deny, defer, stop, failure, halt) | yes |
| `RECLAIMED` | Returned by the cycle-open sweep after an orphaning crash | yes |

Legal: `HELD → {COMMITTED, RELEASED, RECLAIMED}`.

Illegal and asserted: `COMMITTED → RELEASED` (would create capacity from nothing),
`RELEASED → COMMITTED` (would spend released capacity twice), `RELEASED → RELEASED` (double release
inflates the budget), and any handle remaining `HELD` at cycle close (`AL-10`).

The invariant `committed[r] + reserved[r] ≤ limit[r]` is checked after **every** transition, not
periodically (`RR-NFR-041`). A violation raises `INVARIANT_VIOLATION` and aborts the cycle.

---

## 5. Cycle and Run

### 5.1 Cycle

| State | Meaning |
|---|---|
| `OPEN` | Reservations swept, strategy and policy snapshots taken |
| `DECIDING` | Steps 1–13 of the 23-step sequence |
| `EXECUTING` | Steps 14–19 |
| `VERIFYING` | Steps 20–22 |
| `CLOSED` | Completed; all handles settled; metrics emitted |
| `ABORTED` | Terminated early with a recorded reason and step number |

Legal: `OPEN → DECIDING → EXECUTING → VERIFYING → CLOSED`, and any state → `ABORTED`.

On `ABORTED`: every `HELD` handle is released, no partial metric is emitted, the reason and step are
audited, and the next cycle opens with a sweep. A cycle never resumes mid-way — it is re-run from
`OPEN`, which is safe precisely because idempotency keys prevent duplicate effects.

### 5.2 Run

| State | Meaning |
|---|---|
| `INITIALISED` | Seed, versions, and config recorded; genesis hash computed |
| `RUNNING` | Cycles executing |
| `COMPLETED` | All cycles closed; chain verified; artefacts written and hashed |
| `INVALIDATED` | Chain verification failed, or an `INVARIANT_VIOLATION` occurred |
| `ABORTED` | Terminated by halt or fatal error |

**`INVALIDATED` produces no metrics.** The artefact is marked invalid and is not usable as evidence
(§ 5.3 of [16-audit-trail.md](16-audit-trail.md)). This is the mechanism that prevents a run with a
broken audit chain from quietly contributing numbers to a report.

---

## 6. Cross-machine invariants

| # | Invariant |
|---|---|
| SM-1 | An opportunity in `ACTING` has exactly one intervention in `IN_FLIGHT` |
| SM-2 | An opportunity in `RECONCILING` has exactly one intervention in `UNKNOWN` |
| SM-3 | Every intervention in `IN_FLIGHT` or later has a `COMMITTED` or `RELEASED` reservation handle by cycle close |
| SM-4 | No two interventions share an idempotency key |
| SM-5 | An `AUTHORISED` opportunity has exactly one `HELD` handle and one `ALLOW` gate trace |
| SM-6 | An `AWAITING_APPROVAL` opportunity holds **no** reservation (released at queueing, re-reserved on approval) |
| SM-7 | At cycle close, zero handles are `HELD` |
| SM-8 | Every terminal opportunity state has an audit event justifying it |
| SM-9 | An opportunity's state is derivable from the audit chain alone |
| SM-10 | Sum of `V` over `RECOVERED` opportunities ≤ sum of `V` over all opportunities ever created (`LK-4`) |

---

## 7. Testing requirements

| Requirement | Statement |
|---|---|
| `RR-NFR-043` | Every legal transition has a test; every illegal transition has a test asserting it raises |
| Exhaustive illegal-pair sweep | For each machine, generate all (state, state) pairs, subtract the legal table, and assert every remainder raises. This catches transitions nobody thought to forbid |
| Reachability | Every state is reached at least once across the benchmark; unreached states are named in the coverage report and explained |
| Terminality | No transition out of any terminal state, except the audited `STOPPED → PRICED` re-open with an external evidence reference |
| Crash-resume | For each step boundary in [15 § 2](15-execution-model.md), kill and resume, and assert the resulting state is legal, auditable, and free of duplicate effects |
| Replay | State reconstructed from the audit chain equals live state (SM-9) |

---

## 8. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-NFR-043` legal transitions enforced | § 1.3, § 7 |
| `RR-FUNC-051` pre-execution stopping check | `AUTHORISED → DEFERRED` |
| `RR-FUNC-065` reconciliation blocks action | § 1.3, SM-2 |
| `RR-FUNC-066` modified approvals re-gated | `AWAITING_APPROVAL → PRICED` |
| `RR-GUARD-023` no in-cycle re-optimisation after denial | `PRICED → DEFERRED/REJECTED` only; no `PRICED → PRICED` within a cycle |
| `RR-NFR-041` ledger invariant | § 4 |
| `RR-NFR-042` crash recoverability | § 7 crash-resume |
| `RR-AUDIT-009` reconstruction | SM-9 |

---

## 9. Open items

| Item | Label |
|---|---|
| Whether `AWAITING_OUTCOME` should hold a reservation for a follow-up action | `PROPOSED` no — it holds nothing, so capacity is never idle |
| Whether partial recovery deserves its own state | `PROPOSED` no — it reduces `V` and returns to `PRICED`, which keeps the machine smaller (`P-9`) |
| `max_reconcile_attempts` | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION` |
| Whether `RECONCILIATION_FAILED` should be re-openable after human resolution | `PROPOSED` yes, as an audited human act, but not by the system |
