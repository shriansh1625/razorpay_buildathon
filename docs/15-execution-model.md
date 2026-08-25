# 15 · Execution Model

Execution is where REVIVE stops reasoning and starts having effects. Everything in this document exists
to guarantee two properties:

> **Nothing happens that was not authorised. Nothing authorised happens twice.**

---

## 1. The single execution path

`RR-GUARD-021` requires exactly one code path from a decision to an effect:

```
Decision(SELECTED)
   → PolicyEngine.verdict == ALLOW            (C-13, § 13)
   → Ledger.RESERVE all resources granted     (C-16)
   → StoppingRules re-evaluated               (C-14, RR-FUNC-051)
   → IdempotencyKey minted and claimed
   → AuditEvent(ACTION_INTENT) written        ← BEFORE any effect
   → ExecutionAgent.execute()                 (C-17)
   → Adapter.invoke()                         (C-18)  ← the only place an effect occurs
   → typed AdapterResult
   → AuditEvent(ACTION_RESULT) written
   → Ledger.COMMIT or RELEASE
   → Intervention row persisted
```

### 1.1 Enforcement, not convention

| Mechanism | Statement |
|---|---|
| Adapters are only reachable through `ExecutionAgent` | The adapter interface is not exported to any other module; a test asserts no other module imports it |
| `ExecutionAgent.execute()` requires an `AuthorisedAction` value object | That type can only be constructed by the policy engine on an `ALLOW` verdict. There is no public constructor |
| The `AuthorisedAction` carries its reservation handle and idempotency key | Executing without either is a type error, not a runtime check |
| A test attempts execution outside the path and asserts failure | Named `RR-GUARD-021` |

Making authorisation a *type* rather than a *check* is the difference between a guardrail and a
reminder. A future contributor cannot forget to call the gate; they cannot obtain the argument.

---

## 2. The execution sequence and its crash points

Nine steps. After each, the question is: *if the process dies here, what is the state, and is it
recoverable and auditable?*

| # | Step | If the process dies immediately after |
|---|---|---|
| 1 | Reservation confirmed held | Reservation is orphaned. Reclaimed at next cycle open by cycle-id sweep. **No effect occurred.** Safe |
| 2 | Stopping rules re-evaluated, passed | Same as 1. Safe |
| 3 | Idempotency key minted and **claimed** (persisted as `CLAIMED`) | Key exists, no effect. Recovery finds a claimed key with no result → treats as `TIMEOUT_UNKNOWN` and reconciles. **Conservative: assumes it may have happened.** Safe |
| 4 | `AuditEvent(ACTION_INTENT)` written and chained | Audit shows intent, no result. Recovery reconciles. Safe |
| 5 | Adapter invoked, no response yet | **The dangerous point.** The effect may or may not have occurred. Recovery marks `TIMEOUT_UNKNOWN` → `RECONCILING`. No further action on this opportunity until resolved (`RR-FUNC-065`) |
| 6 | Adapter returned a typed result, not yet persisted | Result lost. Recovery sees claimed key + intent + no result → `TIMEOUT_UNKNOWN` → reconcile. Pessimistic but safe |
| 7 | `AuditEvent(ACTION_RESULT)` written | Audit complete. Ledger not yet settled. Recovery reads the audit result and settles the ledger idempotently |
| 8 | Ledger `COMMIT`/`RELEASE` done | Everything settled but the `Intervention` row may be missing. Recovery rebuilds it from the audit chain — **the audit trail is the source of truth, not the application table** |
| 9 | `Intervention` persisted | Complete |

### 2.1 The ordering rule that makes this work

> **Audit before effect. Always.** (`RR-GUARD-021`, `AI-4`)

Step 4 precedes step 5 unconditionally. If the audit store is unwritable, execution **halts** — the
system will not take an action it cannot record. This is the one place where REVIVE prefers doing
nothing over doing the right thing, and it is deliberate: an unrecorded financial action is
indistinguishable from a compromised system.

### 2.2 The asymmetry of assumptions

At every ambiguous point, recovery assumes **the effect happened**. That produces:

- occasional false `TIMEOUT_UNKNOWN` marks on actions that never fired,
- consequent under-recovery, reported honestly as `unresolved_reconciliation_count`,
- and **zero double effects**.

The opposite assumption would produce double charges and double messages. `AG-04` forbids it. The cost
of the safe assumption is measured and disclosed rather than optimised away.

---

## 3. Idempotency

### 3.1 The key

```
idempotency_key = H( opportunity_id, action_code, attempt_seq, cycle_id )
```

| Component | Why it is in the key |
|---|---|
| `opportunity_id` | Scopes the key to one economic loss |
| `action_code` | A reminder and a retry are different effects |
| `attempt_seq` | Deliberate repeat attempts must be distinguishable |
| `cycle_id` | Two cycles proposing the same action produce different keys, so a legitimate later attempt is not blocked by the earlier one |

The key is **derived, not random**. Two independent computations of the same intended action produce
the same key, which is what makes retry-after-crash safe: the recovering process recomputes the key and
finds it already claimed.

### 3.2 Key lifecycle

```
UNCLAIMED  →  CLAIMED  →  RESOLVED(result)
                  └────→  RESOLVED(TIMEOUT_UNKNOWN)   (recovery path)
```

| Rule | Statement |
|---|---|
| Claiming is atomic | A unique constraint at the storage layer, not an application check |
| A `CLAIMED` key with no result blocks all further attempts on that action | Until reconciliation resolves it |
| Keys are never deleted | They are the record that an attempt existed |
| A `RESOLVED` key returns its stored result on re-invocation | Never re-invokes the adapter |
| Under concurrency, exactly one claimant wins | `RR-NFR-040`, tested with parallel executors |

### 3.3 What idempotency does not cover

Honesty requirement: an idempotency key protects against *REVIVE* duplicating an effect. It cannot
protect against duplication downstream of the adapter boundary — a real provider that accepts a request
twice, a message gateway that re-delivers, a customer who receives the same SMS twice for unrelated
reasons.

Real end-to-end idempotency requires the provider to honour an idempotency header, which is
`UNVERIFIED` here ([36-razorpay-integration-assumptions.md](36-razorpay-integration-assumptions.md)).
The interface passes the key onward; whether it is honoured is outside this build's ability to
guarantee, and the package says so rather than implying end-to-end exactly-once semantics.

---

## 4. The adapter contract

One interface, several implementations, all satisfying the same tests (`RR-NFR-083`).

```
interface ActionAdapter:
    supports(action_code) -> bool
    invoke(AuthorisedAction, idempotency_key, virtual_clock) -> AdapterResult
    reconcile(idempotency_key) -> AdapterResult | UNRESOLVED
```

### 4.1 Contract obligations

| # | Obligation |
|---|---|
| AD-1 | Return a value from the closed `AdapterResult` set, or raise a declared exception. Never return an untyped or provider-shaped object |
| AD-2 | Never mutate REVIVE state. Adapters write nothing |
| AD-3 | Never decide, substitute, or modify the action |
| AD-4 | Accept and forward the idempotency key |
| AD-5 | Be interruptible; a partially-completed invoke must be reconcilable |
| AD-6 | Use only the injected clock; no wall clock |
| AD-7 | Support `reconcile()` for `TIMEOUT_UNKNOWN` resolution |
| AD-8 | Never consult the outcome oracle **except** in a simulated adapter, and never return oracle internals — only the typed result (`AI-6`) |

### 4.2 Implementations in this build

| Adapter | Actions | Nature |
|---|---|---|
| `SimulatedPaymentAdapter` | `A01`, `A02` | Consults the hidden oracle; returns a typed result |
| `SimulatedMessageAdapter` | `A03`–`A11` | Consults the oracle for response behaviour; models delivery failure |
| `SimulatedVoiceAdapter` | `A12` | As above, with a duration model consuming `voice_minutes` |
| `HumanTaskAdapter` | `A13`, `A14` | Creates a queue entry; outcome arrives via the simulated approver/handler policy |

**No real provider adapter exists** (`OS-02`). There is no code path in this build that can move real
money or contact a real person. That is a design property, not an omission, and it is stated in every
place a reader might assume otherwise.

### 4.3 The simulator/reality boundary

| Guarantee | Statement |
|---|---|
| The interface is designed for a real adapter | Same signature, same result set, same reconcile semantics |
| The simulator is not privileged | It receives exactly what a real adapter would receive |
| The shared contract suite runs against every implementation | So a future real adapter is held to the same standard |
| **The simulator's fidelity to real rails is unverified** | It reproduces the *interface*, not the *behaviour*, of any real system. No claim is made about how well its response model matches reality |

---

## 5. Outcome taxonomy

Five results. Exhaustive and closed (`RR-FUNC-064`).

| Result | Meaning | Ledger | Attempt counter | Retry permitted? |
|---|---|---|---|---|
| `SUCCESS` | The effect occurred as intended | `COMMIT` | +1 | n/a — `SR-02` likely fires |
| `FAILED_RETRYABLE` | Failed for a transient reason | `COMMIT` cost, `RELEASE` incentive | +1 | Yes, subject to `G4` and a **fresh gate pass** |
| `FAILED_TERMINAL` | Failed for a reason that will recur | `COMMIT` cost, `RELEASE` incentive | +1 | No — `SR-05` likely fires |
| `TIMEOUT_UNKNOWN` | Effect status unknown | Cost committed **pessimistically** | +1 | **No**, until reconciled |
| `REJECTED_BY_PROVIDER` | The provider refused before any effect | `RELEASE` all | +1 | Depends on reason; treated as terminal by default |

### 5.1 Notes

- **`SUCCESS` of the action ≠ recovery of the money.** A message delivered successfully is a successful
  *action* with an as-yet-unknown *outcome*. Recovery is observed later by C-19, over the horizon `H`.
  Conflating the two is how systems report "95% success" for having sent things. `M-06` and action
  success are separate metrics and are never combined.
- **`TIMEOUT_UNKNOWN` counts against the attempt cap.** The pessimistic direction.
- **`REJECTED_BY_PROVIDER` releases the reservation** because no effect occurred — the only result
  where full release is safe.
- **Incentive release on failure.** `d(i,a)` is charged only on success, so a failed action releases
  the reserved incentive back to the budget within the same cycle, making it available to later
  actions in that cycle if the allocator's plan still holds.

---

## 6. Reconciliation

The state `RECONCILING` exists to hold an opportunity still while REVIVE finds out what it did.

```
TIMEOUT_UNKNOWN
   → opportunity state = RECONCILING
   → no further action on this opportunity, any action code   (RR-FUNC-065)
   → each cycle: adapter.reconcile(idempotency_key)
         RESOLVED(result)  → apply result, exit RECONCILING
         UNRESOLVED        → remain, increment reconcile_attempts
   → after max_reconcile_attempts:
         → state = RECONCILIATION_FAILED
         → opportunity stops (SR-09-adjacent hold), flagged for human review
         → counted in unresolved_reconciliation_count and REPORTED
```

| Rule | Statement |
|---|---|
| Reconciliation blocks **all** action codes for that opportunity, not just the timed-out one | Otherwise a stuck retry could be joined by a reminder about a payment that may already have succeeded |
| Reconciliation never assumes success or failure | It either learns the answer or escalates to a human |
| Permanently unresolved cases are a **reported metric**, not a swept-under-the-rug residual | `P-7`, `P-15` |
| Reconciliation is idempotent | Repeated calls are safe |

`unresolved_reconciliation_count` appearing in the report is an honesty requirement: it is the count of
cases where REVIVE does not know what it did, and a system that reports zero such cases without having
tested for them has not tested for them.

---

## 7. Retry safety

The most dangerous verb in a payments system. Rules:

| # | Rule |
|---|---|
| RS-1 | A retry is a **new action** with a new idempotency key (`attempt_seq` increments) — never a re-invocation of a previous key |
| RS-2 | A retry requires a **fresh, complete gate pass**. Prior authorisation does not carry forward |
| RS-3 | A retry requires a fresh resource reservation |
| RS-4 | Retry amount **must equal** the original failed amount, asserted by `G12` |
| RS-5 | No retry while `RECONCILING` |
| RS-6 | No retry after `SR-03` |
| RS-7 | Cooldown is cause-aware and enforced by `G4`, not by the executor |
| RS-8 | **The execution layer never retries on its own initiative.** A failure returns a typed result; whether to retry is a *decision* made by the decision engine in a later cycle |

RS-8 is the structural one. Executor-level automatic retry is how retry storms happen: the component
with the least context makes the most consequential repeated decision. In REVIVE the executor has no
retry logic at all — it reports what happened and stops.

### 7.1 Consequence: retries are visible in the allocation

Because a retry must win allocation again next cycle, a retry competes on `ENRV` against every other
opportunity. A second retry with lower uplift will lose to a fresh opportunity with higher uplift. The
retry policy is therefore *economic*, not a fixed schedule — which is the specific improvement over
baseline `B1 FIXED_RETRY` that the benchmark measures.

---

## 8. Concurrency

| Property | Statement |
|---|---|
| Default execution model | **Single-threaded within a cycle.** Simplest correct thing (`P-9`) |
| Concurrency support | The design does not *rely* on single-threading for correctness: idempotency claiming and ledger reservation are both atomic at the storage layer |
| Test requirement | `RR-NFR-040` and `RR-NFR-041` are tested with parallel executors and injected interleavings even though the default is serial |
| Ordering | Execution order within a cycle is the frozen sort key, so serial execution is deterministic |
| Cross-cycle overlap | Not permitted. A cycle completes or aborts before the next opens |

Testing concurrency safety while shipping a serial executor is deliberate: it means enabling
concurrency later is a configuration change rather than a correctness project.

---

## 9. Observability of execution

| Signal | Purpose |
|---|---|
| `interventions{action_code, result}` | The primary execution counter |
| `execution_latency_ms{adapter}` | Performance |
| `idempotency_claims`, `idempotency_conflicts` | Duplicate-suppression evidence |
| `reservations_committed`, `reservations_released`, `reservations_leaked` | Ledger integrity |
| `reconciling_open`, `unresolved_reconciliation_count` | Honesty metrics |
| `audit_write_failures` | Should be 0; non-zero means execution halted |
| `actions_executed_without_allow` (`M-16`) | **Must be 0**; build-blocking |

Every log line in this path carries the correlation quad `(cycle_id, opportunity_id, decision_id,
intervention_id)` (`RR-NFR-071`).

---

## 10. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-FUNC-060` execute only the approved action | § 1, § 1.1 |
| `RR-FUNC-061` idempotency | § 3 |
| `RR-FUNC-062` reservation commit/release | § 2, § 5 |
| `RR-FUNC-063` adapter interface | § 4 |
| `RR-FUNC-064` closed outcome set | § 5 |
| `RR-FUNC-065` reconciliation blocks action | § 6 |
| `RR-FUNC-066` modified approvals re-gated | [13 § 7](13-policy-and-guardrails.md) |
| `RR-GUARD-021` single path, audit before effect | § 1, § 2.1 |
| `RR-NFR-040` no double execution under concurrency | § 3.2, § 8 |
| `RR-NFR-041` no budget over-consumption | § 2, § 5 |
| `RR-NFR-042` crash recoverability | § 2 |
| `RR-NFR-083` shared adapter contract tests | § 4.1 |
| `AG-04` no double-charging | § 2.2, § 3 |

---

## 11. Open items

| Item | Label |
|---|---|
| Whether real providers honour a client-supplied idempotency key | `UNVERIFIED` — determines whether end-to-end exactly-once is achievable at all ([36](36-razorpay-integration-assumptions.md)) |
| Real reconciliation mechanism (status query, webhook, settlement file) | `UNVERIFIED`; the `reconcile()` method is a placeholder shape |
| `max_reconcile_attempts` | `PROPOSED` |
| Whether `REJECTED_BY_PROVIDER` should ever be retryable | `UNKNOWN`; depends on real rejection reason codes |
| Whether message delivery receipts are available and how they map to outcomes | `UNVERIFIED` |
| Concurrency limits if enabled | `FUTURE / NOT IMPLEMENTED` |
