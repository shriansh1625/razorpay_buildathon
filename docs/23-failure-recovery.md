# 23 · Failure Recovery

PAYVANTA operates on money under time constraints. Every failure mode has a defined detection,
containment, and resolution path. The system's default posture is **fail closed**: when in doubt,
do less, not more.

> **Principle.** A financial system that retries blindly after a failure is more dangerous than one
> that stops. Every failure path below either resolves to a safe state or stops and escalates.

---

## 1. Failure catalogue

### F-01 · Payment action failure

| Field | Value |
|---|---|
| **Detection** | Adapter returns `FAILED_RETRYABLE` or `FAILED_TERMINAL` |
| **Containment** | Intervention state → `COMPLETED_FAILED`. Reservation committed (cost charged on attempt, not on success). Opportunity remains open |
| **Retry policy** | `FAILED_RETRYABLE`: opportunity re-enters the pool next cycle, subject to `SR-03` (attempt cap) and `G4` (cooldown). `FAILED_TERMINAL`: no retry for this action code on this instrument; alternate actions may be considered |
| **Fallback** | Candidate Generator produces alternative actions next cycle. If no alternative clears `ε`, `NO_ACTION` |
| **Escalation** | After attempt cap (`SR-03`), opportunity stops. If repeated failures across a cohort, `C-03` Degradation Monitor flags |
| **Final state** | `STOPPED(SR-03)` or `CLOSED_UNRECOVERED(SR-01)` or `RECOVERED` (via alternate action) |
| **Audit event** | `ACTION_FAILED` with adapter result, failure reason, attempt count |

### F-02 · Timeout / adapter timeout

| Field | Value |
|---|---|
| **Detection** | Adapter returns `TIMEOUT_UNKNOWN` |
| **Containment** | Intervention state → `UNKNOWN`. Opportunity state → `RECONCILING`. **No further action on this opportunity until resolved** (`RR-FUNC-065`) |
| **Retry policy** | No retry until reconciliation determines the actual outcome. Reconciliation attempts are bounded by `max_reconcile_attempts` |
| **Fallback** | Reconciliation resolved → opportunity returns to `AWAITING_OUTCOME` or `RECOVERED`. Reconciliation failed → `RECONCILIATION_FAILED` (terminal, requires human resolution) |
| **Escalation** | `RECONCILIATION_FAILED` → human out-of-band resolution. Alert on `M-35` (unresolved reconciliations) |
| **Final state** | `AWAITING_OUTCOME` (resolved) or `RECONCILIATION_FAILED` (terminal) |
| **Audit event** | `ACTION_TIMEOUT`, `RECONCILIATION_ATTEMPT`, `RECONCILIATION_RESOLVED` or `RECONCILIATION_FAILED` |

**REVIVE must STOP rather than retry** when:
- The effect of the timed-out action is unknown
- Retrying could cause a duplicate financial effect
- The reconciliation window has not yet been exhausted

### F-03 · API / service unavailable

| Field | Value |
|---|---|
| **Detection** | Adapter throws a connection error or returns a service-unavailable status |
| **Containment** | Treat as `TIMEOUT_UNKNOWN` if the request may have been received; treat as `FAILED_RETRYABLE` if the connection was never established (pre-flight failure) |
| **Retry policy** | Pre-flight failure: opportunity deferred to next cycle. Post-flight unknown: enters `RECONCILING` |
| **Fallback** | If the LLM provider is unavailable: C-05 falls back to deterministic-only diagnosis; C-10 falls back to static template text. Cycle completes without LLM assistance ([08 § 9](08-agent-architecture.md)) |
| **Escalation** | Sustained unavailability → alert. If policy pack or predictor parameters are unreachable → **deny everything for the cycle** (fail closed) |
| **Final state** | `DEFERRED` (pre-flight) or `RECONCILING` (post-flight) |
| **Audit event** | `SERVICE_UNAVAILABLE` with service name, error class, pre/post-flight determination |

### F-04 · Duplicate event / signal

| Field | Value |
|---|---|
| **Detection** | C-01 Signal Ingestor detects a signal whose idempotency content matches an already-ingested signal |
| **Containment** | Duplicate is acknowledged but does not create a new opportunity. `attempt_count` on the existing opportunity is incremented if appropriate (`RR-FUNC-003`) |
| **Retry policy** | N/A — no action needed |
| **Fallback** | N/A |
| **Escalation** | Elevated duplicate rate → alert via `M-56` (signal hygiene) |
| **Final state** | Existing opportunity unchanged (or `attempt_count` incremented) |
| **Audit event** | `SIGNAL_DEDUPLICATED` with both signal IDs |

### F-05 · Duplicate execution attempt

| Field | Value |
|---|---|
| **Detection** | G9 Duplicate Suppression: idempotency key already exists in a non-terminal or successful state, or semantic equivalence window triggered |
| **Containment** | Action denied (`G9 → DENY`). No adapter call. No resource consumption |
| **Retry policy** | N/A — the original action's outcome governs |
| **Fallback** | N/A |
| **Escalation** | Repeated duplicate attempts → engineering alert (potential loop bug) |
| **Final state** | Opportunity state unchanged; decision records `REJECTED(DUPLICATE)` |
| **Audit event** | `DUPLICATE_SUPPRESSED` with original intervention ID |

### F-06 · Stale state / stale decision

| Field | Value |
|---|---|
| **Detection** | Stale-decision detection (`RR-FUNC-043`): opportunity state changed after the decision was computed |
| **Containment** | Action is not executed. Reservation released. Decision invalidated |
| **Retry policy** | Opportunity re-enters the pipeline next cycle with current state |
| **Fallback** | Pre-execution stopping-rule evaluation (`RR-FUNC-051`) is the second line of defence |
| **Escalation** | High stale-decision rate → cycle interval may be too long (operational alert) |
| **Final state** | `DEFERRED` (re-enters next cycle) |
| **Audit event** | `STALE_DECISION_DETECTED` with original and current state snapshots |

### F-07 · Conflicting state

| Field | Value |
|---|---|
| **Detection** | State machine transition guard: an attempted transition is not in the legal-transition table ([34 § 1.2](34-state-machine.md)) |
| **Containment** | Transition raises. The opportunity does not change state. The cycle may abort if the conflict is unrecoverable |
| **Retry policy** | N/A — illegal transitions are bugs, not transient faults |
| **Fallback** | Cycle abort with recorded reason; all `HELD` reservations released |
| **Escalation** | Any illegal transition attempt → `M-22` (invariant violation) → run invalidated |
| **Final state** | Opportunity in its pre-conflict state; cycle `ABORTED` |
| **Audit event** | `INVARIANT_VIOLATION` with attempted transition, current state, trigger |

### F-08 · Inconsistent payment status

| Field | Value |
|---|---|
| **Detection** | Outcome Observer (C-19) finds a payment status that contradicts the expected state (e.g., settled amount differs from the opportunity's `value_at_risk_paise`) |
| **Containment** | Record the inconsistency. If the payment shows as settled, update recovered amount. If the amount is unexpected, flag for reconciliation |
| **Retry policy** | N/A — observation, not action |
| **Fallback** | Partial recovery handling: reduce `V(i)` to the remaining balance; opportunity continues with the revised value |
| **Escalation** | Persistent inconsistency → reconciliation; unresolvable → `RECONCILIATION_FAILED` |
| **Final state** | `RECOVERED` (full match), `PRICED` (partial, re-enters with reduced `V`), or `RECONCILING` |
| **Audit event** | `OUTCOME_INCONSISTENCY` with expected and observed values |

### F-09 · Model uncertainty

| Field | Value |
|---|---|
| **Detection** | Recovery Predictor (C-07) returns a wide `sigma` (uncertainty measure). Context Enricher (C-04) sets `context_degraded = true` on missing data |
| **Containment** | Wide uncertainty → G7 may trigger `REQUIRE_APPROVAL`. Degraded context inflates `sigma` downstream. Unseen feature combination → shrink to parent cell's prior and inflate `sigma` |
| **Retry policy** | N/A — uncertainty is a property of the estimate, not a failure |
| **Fallback** | Approval queue for high-uncertainty cases. If parameters corrupt → **entire cycle defers with no actions** ([08 § 5](08-agent-architecture.md) C-07) |
| **Escalation** | Systematic high uncertainty → predictor calibration issue → engineering investigation |
| **Final state** | `AWAITING_APPROVAL` or `DEFERRED` or `NO_ACTION_CYCLE` |
| **Audit event** | `HIGH_UNCERTAINTY_FLAGGED` with `sigma`, confidence interval |

### F-10 · Tool / service unavailable (LLM)

| Field | Value |
|---|---|
| **Detection** | LLM API call fails (timeout, rate limit, error) |
| **Containment** | C-05: discard LLM output, use deterministic-only taxonomy mapping. C-10: discard generated copy, use static template text. Cycle continues |
| **Retry policy** | No LLM retry within the cycle. The cached result will be available for subsequent cycles if the LLM recovers |
| **Fallback** | Both LLM agents have complete deterministic fallback paths ([08 § 9](08-agent-architecture.md)). The system loses nuance, not capability |
| **Escalation** | Sustained LLM unavailability → `M-50` spike → operational alert |
| **Final state** | Cycle completes normally with reduced diagnostic quality |
| **Audit event** | `LLM_UNAVAILABLE` with purpose, fallback activated |

### F-11 · Budget exhaustion

| Field | Value |
|---|---|
| **Detection** | G6 Budget gate: reservation request refused because `committed[r] + reserved[r] + requested[r] > limit[r]` |
| **Containment** | Action deferred (`G6 → DEFER`), not denied. Capacity may exist next cycle or next period |
| **Retry policy** | Opportunity re-enters allocation next cycle. Budget refills at period boundary |
| **Fallback** | Shadow prices inform the merchant which resources are scarce (`M-30`) |
| **Escalation** | Persistent budget exhaustion → `M-29` near 1.0 → merchant alert |
| **Final state** | `DEFERRED` |
| **Audit event** | `BUDGET_EXHAUSTION` with resource, requested amount, available amount |

**REVIVE must STOP rather than retry** when: Never. Budget exhaustion is a `DEFER`, not a `STOP`. Stopping would discard recoverable revenue ([14 § 5](14-stopping-rules.md)).

### F-12 · Policy conflict / contradictory rules

| Field | Value |
|---|---|
| **Detection** | Two gates return contradictory modifications (e.g., two G5 ceilings disagree on the clamp value) |
| **Containment** | The smaller (more restrictive) clamp applies. The contradiction is logged as a **defect**, not silently resolved ([13 § 4.1](13-policy-and-guardrails.md)) |
| **Retry policy** | N/A — the stricter rule governs immediately |
| **Fallback** | Policy pack integrity check at cycle open should catch malformed packs before they produce contradictions |
| **Escalation** | Policy contradiction → engineering alert → pack fix required out of band |
| **Final state** | Decision proceeds with the stricter interpretation |
| **Audit event** | `POLICY_CONTRADICTION` with both gate verdicts, resolved value, defect flag |

### F-13 · Customer unavailable / unreachable

| Field | Value |
|---|---|
| **Detection** | G11 Channel Eligibility: no valid channel exists for the customer. Or: adapter returns `REJECTED_BY_PROVIDER` with a delivery-failure reason |
| **Containment** | If no channel exists → action denied by G11. If delivery failed → channel marked degraded for future eligibility checks |
| **Retry policy** | Different channel may be attempted next cycle if eligible. Same channel not retried until degradation clears |
| **Fallback** | Non-contact actions (payment retry on valid mandate) may still be applicable |
| **Escalation** | All channels degraded for a customer → `SR-05` may fire (no reachable action). Opportunity stops if no fix path exists |
| **Final state** | `DEFERRED` (alternate channel possible) or `STOPPED(SR-05)` |
| **Audit event** | `CHANNEL_UNAVAILABLE` or `DELIVERY_FAILED` with channel, reason |

### F-14 · Outcome not observable

| Field | Value |
|---|---|
| **Detection** | Outcome Observer (C-19): no settlement or payment event observed within horizon `H` after action execution |
| **Containment** | Outcome classified as unobservable. Attribution set to `AMBIGUOUS`. Excluded from attributed totals. `M-21` `unobservable_rate` incremented |
| **Retry policy** | Opportunity re-enters decisioning (`AWAITING_OUTCOME → PRICED`) with updated state after horizon elapsed |
| **Fallback** | Late observation (payment arrives after `H`) is recorded but attributed conservatively |
| **Escalation** | High `unobservable_rate` → data pipeline issue → engineering alert |
| **Final state** | `PRICED` (re-enters) or `CLOSED_UNRECOVERED(SR-01)` if window also expired |
| **Audit event** | `OUTCOME_UNOBSERVABLE` with horizon, action, elapsed time |

### F-15 · Delayed event

| Field | Value |
|---|---|
| **Detection** | C-01 Signal Ingestor: event timestamp is older than the current virtual clock by more than a configured threshold |
| **Containment** | Signal is processed but marked `late_signal = true`. Deduplication still applies. If the opportunity already has a decision or action, stale-decision detection triggers |
| **Retry policy** | N/A — the event is processed; the opportunity is updated |
| **Fallback** | Late events that arrive after the opportunity is terminal (e.g., after `STOPPED` or `CLOSED_UNRECOVERED`) are recorded but do not change the terminal state |
| **Escalation** | Elevated late-signal rate → `M-56` signal hygiene alert |
| **Final state** | Depends on content: may update `V(i)`, trigger `SR-02` (recovery), or be discarded |
| **Audit event** | `LATE_SIGNAL_RECEIVED` with delay, original timestamp, current clock |

### F-16 · Out-of-order events

| Field | Value |
|---|---|
| **Detection** | C-01 Signal Ingestor: event sequence number or timestamp is earlier than a previously processed event for the same entity |
| **Containment** | Signal is quarantined if it would create an illegal state transition. If it carries new information (e.g., a success signal arriving out of order), it is processed with a reordering flag |
| **Retry policy** | N/A |
| **Fallback** | Quarantined events are reviewed at cycle boundary; if the state machine can accommodate the information, it is applied; otherwise it is logged and discarded |
| **Escalation** | Repeated out-of-order events from one source → data pipeline investigation |
| **Final state** | Depends on content; quarantine is not a terminal state |
| **Audit event** | `OUT_OF_ORDER_SIGNAL` with expected and actual sequence, disposition |

### F-17 · Partial success

| Field | Value |
|---|---|
| **Detection** | Outcome Observer (C-19): `recovered_amount_paise < value_at_risk_paise` |
| **Containment** | Opportunity state → `PRICED` with reduced `V(i)` (remaining balance). Does not fire `SR-02` (which requires full recovery). Re-enters decisioning with the smaller value |
| **Retry policy** | Opportunity is re-priced at the reduced `V(i)`. If no candidate clears `ε` at the smaller value, `NO_ACTION`. If `N` consecutive `NO_ACTION` cycles → `SR-07` |
| **Fallback** | Different action types may be attempted for the remaining balance |
| **Escalation** | Repeated partial recoveries with diminishing returns → `SR-07` fires naturally |
| **Final state** | `RECOVERED` (if subsequent actions recover the remainder) or `STOPPED(SR-07)` or `CLOSED_UNRECOVERED(SR-01)` |
| **Audit event** | `PARTIAL_RECOVERY` with original value, recovered amount, remaining balance |

---

## 2. When REVIVE must STOP rather than retry

The following conditions require REVIVE to **stop all activity on the opportunity**, not retry:

| Condition | Rule | Rationale |
|---|---|---|
| Recovery window expired | `SR-01` | Time boundary is absolute. No extension |
| Full recovery observed | `SR-02` | Nothing to recover |
| Attempt cap exhausted | `SR-03` | Further attempts are harassment, not recovery |
| Contact cap exhausted for this opportunity | `SR-04` | Prevents drip-feed contact fatigue |
| Terminal cause with no fix path | `SR-05` (MED/HIGH confidence) | Customer declined; order cancelled; no instrument |
| Economic exhaustion — N consecutive no-value cycles | `SR-07` | Carrying dead weight |
| Customer explicit refusal or full opt-out | `SR-08` | Further contact is harassment |
| Risk/legal hold | `SR-09` | REVIVE does not adjudicate flags |
| Value no longer recoverable (write-off, refund) | `SR-10` | Nothing to recover |
| Merchant stop or global HALT | `SR-11` | Human authority |
| Reconciliation exhausted | `RECONCILIATION_FAILED` | Cannot determine what happened; human intervention required |
| Invariant violation | `M-22` | System integrity compromised |

REVIVE must **NOT** stop for:
- Budget exhaustion (defer, not stop — budget returns)
- Communication window closed (defer — window opens later)
- Cooldown active (defer — cooldown expires)
- Single failed action (continue — alternatives exist)
- Wide uncertainty (route to approval, not abandonment)
- Predictor degradation (defer — transient)

---

## 3. Cycle-level failure handling

| Failure | Cycle behaviour | Next cycle |
|---|---|---|
| Policy pack missing/corrupt | Deny all actions; cycle completes with all `REJECTED_POLICY_UNAVAILABLE` | Retry if pack restored |
| Predictor parameters missing/corrupt | Defer entire cycle; no actions | Retry if parameters restored |
| Allocator timeout | Switch to `FALLBACK_GREEDY`; record `allocator_mode` | Normal |
| Ledger invariant violated | Abort cycle; release all reservations; `M-22` incremented | Run invalidated |
| Audit store unwritable | **Halt execution entirely** (`RR-AUDIT-010`) | Cannot proceed until restored |
| Step budget exceeded | Clean termination; reservations released; recorded reason | Normal restart |
| LLM unavailable | Deterministic fallback; cycle completes | Normal |

---

## 4. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-FUNC-003` deduplication | F-04 |
| `RR-FUNC-043` stale-decision detection | F-06 |
| `RR-FUNC-051` pre-execution stopping | F-06, F-09 |
| `RR-FUNC-060` idempotency | F-05 |
| `RR-FUNC-065` reconciliation blocks action | F-02 |
| `RR-FUNC-070` partial recovery | F-17 |
| `RR-FUNC-073` legal state transitions | F-07 |
| `RR-GUARD-006` budget gate | F-11 |
| `RR-GUARD-009` duplicate suppression | F-05 |
| `RR-GUARD-023` verdict finality | F-12 |
| `RR-GUARD-024` global halt | § 2 |
| `RR-AUDIT-010` audit store blocking | § 3 |
| `SR-01`…`SR-11` | § 2 |
