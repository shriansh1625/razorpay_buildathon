# 14 · Stopping Rules

The Track 03 bar names stopping rules explicitly. They are not error handling — they are the mechanism
that makes a recovery workflow **bounded**, and therefore the mechanism that makes autonomous action
on money defensible.

---

## 1. Position

| Property | Statement |
|---|---|
| **Stopping is terminal for the opportunity, not for the system** | A stopped opportunity takes no further action, ever, under that opportunity id |
| **Stopping is cheap and preferred** | When in doubt, stop. The cost of stopping wrongly is measurable (`M-19 Missed Opportunity Value`); the cost of not stopping is a customer harmed and an unbounded loop |
| **Stopping is not failure** | `PP-5`. A stopped opportunity with a recorded reason is a correct outcome |
| **Stopping is deterministic** | Rule evaluation over state. No model, no LLM, no judgement call |
| **Stopping is evaluated twice per cycle** | At cycle start and again immediately before execution (`RR-FUNC-051`) |
| **Stopping is distinct from deferral** | Deferral means "not now". Stopping means "not ever". Conflating them is forbidden ([09 § 3.1](09-decision-engine.md)) |

---

## 2. The eleven rules

| ID | Rule | Trigger | Terminal? | Re-openable? |
|---|---|---|---|---|
| `SR-01` | **Recovery window expired** | `now ≥ recovery_window_expires_at` | yes | no |
| `SR-02` | **Recovered** | Full recoverable amount observed as settled | yes | no |
| `SR-03` | **Attempt cap reached** | Retry attempts exhausted per opportunity / instrument / period | yes | no |
| `SR-04` | **Contact cap reached** | Contact allowance for this opportunity exhausted | yes | no |
| `SR-05` | **Terminal cause** | Diagnosis is a terminal cause with no remaining fix path | yes | **yes**, on new evidence |
| `SR-06` | **Approval expired** | A queued action was neither approved nor rejected within its validity | action-level | yes, next cycle |
| `SR-07` | **Economic exhaustion** | No candidate cleared `ε` for `N` consecutive cycles | yes | **yes**, on material state change |
| `SR-08` | **Customer refusal or opt-out** | Explicit decline to pay, or consent revoked on every eligible channel | yes | **yes**, only on re-consent |
| `SR-09` | **Risk or legal hold** | Fraud, dispute, insolvency, deceased, or legal flag set | yes | yes, if the flag clears |
| `SR-10` | **Value no longer recoverable** | Written off, refunded, credited, or `V(i) → 0` | yes | no |
| `SR-11` | **Merchant stop** | Per-opportunity suppression, or global `HALT` | yes | yes, on explicit resume |

### 2.1 Rule detail

#### `SR-01` Recovery window expired

The hard boundary of the product. After the window, the money is treated as unrecoverable and REVIVE
takes no action, regardless of `ENRV`. Window lengths are per risk class and per policy pack, frozen
before measurement (§ 10).

Interaction with horizon: `H = min(H_class, window_close − now)`. A closing window shortens the
horizon, which lowers `p(i,∅)` and raises urgency — so urgency is modelled, not hand-coded, right up
to the moment the window shuts.

#### `SR-02` Recovered

Fires on observed settlement of the full recoverable amount. Three subtleties:

| Case | Handling |
|---|---|
| **Partial recovery** | Does **not** fire `SR-02`. `V(i)` is reduced to the remaining balance and the opportunity stays open, re-priced at the smaller `V` — which often means it stops on `SR-07` shortly after, correctly |
| **Recovery observed mid-cycle, after reservation** | The pre-execution evaluation catches it: reservation released, decision becomes `DEFERRED_STOPPED`, **no action executes**. This is the single most important pre-execution check in the system |
| **Recovery timestamp precedes the action timestamp** | Attribution is `NATURAL`, never `ATTRIBUTED` (`RR-FUNC-071`) |

#### `SR-03` Attempt cap reached

Three independent counters — per opportunity, per instrument, per period — and the strictest binds.
Attempts that ended in `TIMEOUT_UNKNOWN` **count** against the cap, because the safe assumption is
that they reached the rail.

#### `SR-04` Contact cap reached

Distinct from `G3`. `G3` is the customer-level regulatory/courtesy cap that denies an individual
action. `SR-04` is the **opportunity-level** budget: this particular loss is allowed a bounded number
of customer touches in total, after which REVIVE stops pursuing it even if the customer's global
allowance has room.

Without `SR-04`, a single stubborn invoice could consume a customer's entire tolerance across many
cycles, one contact at a time, never violating any per-cycle cap. This is the drip-feed failure mode,
and `SR-04` is its structural defence.

#### `SR-05` Terminal cause

Fires when the top-ranked cause is terminal **and** the confidence band is not `LOW`:

| Terminal cause | Why no fix path |
|---|---|
| `CUSTOMER_DECLINED_TO_PAY` | The customer decided. Further contact is harassment, not recovery |
| `ORDER_NO_LONGER_WANTED` | There is nothing to collect for |
| `INSTRUMENT_INVALID` with no alternate instrument and no consented channel to request one | No reachable action |
| `ISSUER_DECLINE_HARD` with no alternate method available | Same |

Re-openable on new evidence: if a customer later adds an instrument or grants consent, the state
changed materially and the opportunity may re-open — but only inside its recovery window, and the
re-opening is audited.

**A `LOW` confidence band does not stop anything.** Stopping on a weak inference would let an
uncertain LLM-assisted ranking silently kill recoverable revenue. Terminal stopping requires either a
deterministic fact (no instrument, no consent) or a `MED`/`HIGH` band.

#### `SR-06` Approval expired

Action-level, not opportunity-level. An approval request has a validity period; unattended requests
expire and the action is voided. The opportunity itself remains open and may be reconsidered next
cycle — which may again require approval.

**Silence is never consent.** An expired request is a rejection, not a timeout-into-execution. This is
one of the highest-severity safety properties in the package: the failure mode of a busy approver must
be *less* action, never more.

#### `SR-07` Economic exhaustion

Fires when, for `N` consecutive cycles, no candidate cleared `ε`. This is the rule that stops REVIVE
from carrying dead weight in its opportunity book forever, and it is the most *interesting* rule
because it is an economic stop rather than a compliance one.

| Property | Statement |
|---|---|
| `N` is a policy parameter | `PROPOSED`; sensitivity reported |
| Re-openable on material state change | A new failure, a consent grant, an instrument update, or a `V` change resets the counter |
| Distinct from `NO_ACTION` | `NO_ACTION` is per cycle; `SR-07` is the accumulation of `N` of them |
| Reported | The stopped-on-`SR-07` set with its total `V` is a report line — it is the honest statement "we gave up on this much money, deliberately" |

#### `SR-08` Customer refusal or opt-out

Fires on explicit decline, or on consent revocation across every eligible channel. Non-contact actions
(a retry on a valid mandate) may in principle continue after a *communication* opt-out — but an
explicit **decline to pay** stops everything, including retries. The pack distinguishes the two, and
the distinction is a policy decision recorded per merchant, not a system default.

#### `SR-09` Risk or legal hold

REVIVE consumes the flag and stops. It does not adjudicate, appeal, or reason about the flag
(`OS-24`). Clearing is out of band.

#### `SR-10` Value no longer recoverable

Write-off, refund, credit note, or full dispute reduces `V(i)` to zero. Fires immediately. Also fires
if a reconciliation reveals the amount was never outstanding.

#### `SR-11` Merchant stop

Per-opportunity suppression, or the global `HALT`. Global halt stops every opportunity, releases
reservations, records the actor, and requires an explicit audited resume (`RR-GUARD-024`,
`RR-NFR-046`).

---

## 3. Evaluation timing

```
cycle open
   │
   ├─ [1st evaluation] SR-01…SR-11 over all open opportunities
   │      stopped → excluded from selection, state → STOPPED(reason)
   │
   ├─ decide, allocate, gate, reserve
   │
   ├─ [2nd evaluation] SR-01…SR-11 for each action about to execute   ← RR-FUNC-051
   │      stopped → release reservation, decision = DEFERRED_STOPPED, no execution
   │
   └─ execute survivors
```

The second evaluation exists because state changes during a cycle: a success signal arrives, a consent
is revoked, an approval expires, a risk flag lands. Evaluating only at cycle start would allow REVIVE
to act on a stale world. This double evaluation is required (`RR-FUNC-051`) and is asserted by a test
that injects a mid-cycle success signal and verifies no action executed.

---

## 4. Terminal versus re-openable

| Category | Rules | Meaning |
|---|---|---|
| **Permanently terminal** | `SR-01`, `SR-02`, `SR-03`, `SR-04`, `SR-10` | The state that caused them cannot un-happen |
| **Conditionally re-openable** | `SR-05`, `SR-07`, `SR-08`, `SR-09`, `SR-11` | A material, externally-caused state change may re-open |
| **Action-level only** | `SR-06` | The opportunity was never stopped |

### 4.1 Re-opening discipline

Re-opening is the obvious loophole — a system that can re-open its own stops has no stops. Therefore:

| Rule | Statement |
|---|---|
| Re-opening requires an **external** state change | New signal, consent grant, instrument change, flag clearance, or human act. Never a REVIVE-internal recomputation |
| Re-opening is audited with the triggering evidence reference | `RR-AUDIT-*` |
| Re-opening cannot extend the recovery window | `SR-01` still binds |
| Attempt and contact counters **do not reset** on re-open | Otherwise re-opening would launder the caps |
| Re-openings per opportunity are themselves capped | `PROPOSED`; prevents oscillation |
| REVIVE cannot re-open on the grounds that `ENRV` improved | The predictor changing its mind is not a state change in the world |

That last row is the important one. `SR-07` re-opens on a *world* change, not on a *belief* change.
Otherwise a learning update could resurrect every stopped opportunity.

---

## 5. What is deliberately **not** a stopping rule

| Not a stop | It is a… | Because |
|---|---|---|
| Budget exhausted | `DEFER` (`G6`) | Capacity returns next period. Stopping would discard recoverable revenue |
| Outside communication window | `DEFER` (`G2`) | It will be inside the window later |
| Cooldown active | `DEFER` (`G4`) | Timing, not termination |
| Allocator chose someone else | `DEFER` | Contention, not termination |
| One failed action | Nothing — the opportunity continues | A single failure is expected; caps handle repetition |
| Predictor degraded | `DEFER` | Degradation is temporary; stopping would be irreversible on a transient fault |
| Low `ENRV` this cycle | `NO_ACTION` | Only `N` consecutive cycles (`SR-07`) is a stop |
| Wide uncertainty | `REQUIRE_APPROVAL` (`G7`) | Uncertainty warrants a human, not abandonment |

The pattern: **transient conditions defer; permanent conditions stop.** A test asserts that no
transient condition can produce a terminal state, because an irreversible response to a temporary
fault is the worst class of bug in a money system.

---

## 6. Coverage and reporting

| Requirement | Statement |
|---|---|
| `RR-FUNC-050` | All eleven rules implemented and evaluated |
| `RR-FUNC-051` | Double evaluation per cycle |
| `M-17` | Count of opportunities that *should* have stopped but did not. **Must be 0.** Non-zero is a build failure |
| Coverage table | Every rule fires at least once across the benchmark; the table is published with counts, and empty cells are named and explained |
| Stop-reason breakdown | Reported with the total `V` stopped per reason — the honest accounting of what REVIVE walked away from |
| Re-open audit | Every re-opening listed with its triggering evidence |

The synthetic dataset deliberately manufactures conditions for every rule: windows that close mid-run,
mid-cycle successes, customers at their caps, terminal causes, unattended approvals, opportunities
whose `ENRV` never clears `ε`, explicit refusals, injected risk flags, write-offs, and a scripted
merchant halt ([19-synthetic-dataset.md](19-synthetic-dataset.md)).

---

## 7. Failure behaviour

| Failure | Behaviour |
|---|---|
| A rule cannot be evaluated (state unreadable) | **Treat as stopped** (fail closed) |
| Rule parameters missing from the pack | Deny all actions for the cycle (policy pack integrity failure) |
| Contradictory rules fire | All are recorded; the opportunity stops; the earliest-listed reason is canonical for reporting |
| Stop state write fails | Halt execution — an unrecorded stop is worse than no stop |

---

## 8. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-FUNC-050` stopping rules exist and are evaluated | § 2 |
| `RR-FUNC-051` pre-execution re-evaluation | § 3 |
| `RR-GUARD-010` stopping gate | § 2, [13 § 3.1](13-policy-and-guardrails.md) G10 |
| `RR-GUARD-024` global halt | `SR-11` |
| `RR-FUNC-071` attribution on late success | `SR-02` |
| `AG-02` no unbounded loops | § 1, § 5 |

---

## 9. The bounded-workflow argument, stated once

Track 03 asks for a *bounded* recovery workflow. REVIVE's boundedness is the conjunction of five
independent mechanisms, each of which alone would be insufficient:

1. **A finite action catalogue** — fifteen codes, no code generates a new one
   ([11 § 3](11-counterfactual-engine.md))
2. **A fixed cycle** — 23 steps, a step budget, no self-directed planning
   ([07 § 4](07-system-architecture.md))
3. **Hard resource ceilings** — the ledger cannot be exceeded, by construction
   ([10 § 3.2](10-recovery-allocation.md))
4. **Twelve gates with final authority** — no software override exists
   ([13](13-policy-and-guardrails.md))
5. **Eleven stopping rules** — evaluated twice per cycle, fail-closed (this document)

Remove any one and the system is unbounded in some dimension. That is why all five are `MUST`.

---

## 10. Open items

| Item | Label |
|---|---|
| `N` for `SR-07` | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION`; sensitivity required |
| Recovery-window lengths per class | `UNKNOWN`; must be frozen before measurement |
| Approval validity period | `PROPOSED`; must be shorter than the recovery window |
| Per-opportunity contact budget for `SR-04` | `PROPOSED` |
| Re-opening cap | `PROPOSED` |
| Whether a communication opt-out should also stop non-contact retries | `UNKNOWN`; depends on real consent and mandate semantics, which are `UNVERIFIED` ([13 § 10](13-policy-and-guardrails.md)) |
| Whether partial recovery should reset `SR-07`'s counter | `PROPOSED` yes, because `V` changed materially |
