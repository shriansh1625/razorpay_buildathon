# 13 · Policy and Guardrails

The policy engine (C-13) is the only component in REVIVE with the authority to say *yes*. The
allocator proposes; this engine authorises. Nothing reaches an adapter without an `ALLOW` verdict
from here.

---

## 1. Design position

| Property | Statement |
|---|---|
| **Deterministic** | Pure rule evaluation. No LLM, no model, no probability. A verdict is reproducible from `(action, state, policy_pack_version)` |
| **Final** | No component may override a verdict within the cycle (`RR-GUARD-023`). A denied action is not re-optimised around |
| **Total** | Every proposed action receives a verdict from every applicable gate, in a fixed order, all recorded |
| **Fail-closed** | Missing or corrupt policy pack, indeterminate state, or an evaluation error results in denial (`P-11`) |
| **Immutable at runtime** | The policy pack is versioned and read-only during a cycle. The Learning Engine has no write path to it (`RR-GUARD-022`) |
| **Separate from economics** | Gates do not consider `ENRV`. A hugely profitable action that violates a cap is denied, without a trade-off calculation |

That last row is the point of the whole design. If gates were penalty terms in the objective, a
sufficiently large `ENRV` would purchase a violation. They are constraints, not costs.

---

## 2. The policy pack

A single versioned, declarative artefact. Every parameter that shapes a verdict lives here — none is
hard-coded (`RR-NFR-084`).

```
PolicyPack
├── version                     pol_<ULID>, immutable once sealed
├── consent                     required channels per action family
├── communication_windows        per channel, per merchant timezone (Asia/Kolkata default)
├── contact_caps                 per customer: per-day, per-7-day, per-30-day, per-channel
├── cooldowns                    minimum inter-contact and inter-retry gaps
├── retry_policy                 max attempts per opportunity, per instrument, per period
├── incentive_policy             max tier, max absolute paise, max % of V, per-customer period cap
├── budgets                      per resource: period limit, optional cycle cap, pacing fraction
├── approval_thresholds          value bands, uncertainty bands, action families requiring approval
├── risk_rules                   hard-block flags REVIVE must honour
├── stopping_rules               parameters for SR-01…SR-11
├── epsilon                      ε, the action threshold (paise)
├── lambda_fatigue               λ_f
├── horizons                     H per risk class
├── channel_eligibility          which channels are usable per action and per customer state
└── amount_sanity                absolute and relative caps on any action's monetary effect
```

### 2.1 Versioning rules

| Rule | Requirement |
|---|---|
| A pack is sealed and hash-identified before use | `RR-NFR-091` |
| Every decision records the pack version that judged it | `RR-NFR-091` |
| Changing a pack creates a new version; packs are never edited in place | `P-14` spirit |
| A historical verdict can be replayed against its original pack and reproduce exactly | `RR-GUARD-026` |
| Only a human, out of band, creates a pack version | `RR-GUARD-022` |

### 2.2 Replay as the real test of policy integrity

`RR-GUARD-026` requires that any past verdict be re-derivable. This is stronger than logging the
verdict: it means the *reasoning* is reconstructible. If a merchant asks "why did you deny this in
March?", the answer is produced by re-running March's pack against March's state, not by trusting a
stored string.

---

## 3. The twelve gates

Evaluated in the fixed order below. Order matters: cheap, hard, and customer-protective checks come
first, so that an action failing on consent never gets as far as consuming a budget reservation.

| # | Gate | ID | Asks | Verdicts it can return |
|---|---|---|---|---|
| G1 | **Consent** | `RR-GUARD-001` | Is there valid consent for this channel and purpose? | `DENY` |
| G2 | **Communication window** | `RR-GUARD-002` | Is it a permitted local hour/day for this channel? | `DEFER` |
| G3 | **Contact frequency cap** | `RR-GUARD-003` | Is the customer within per-day / 7-day / 30-day / per-channel caps? | `DENY`, `DEFER` |
| G4 | **Retry cap and cooldown** | `RR-GUARD-004` | Attempts remaining? Cooldown elapsed? | `DENY`, `DEFER` |
| G5 | **Incentive ceiling** | `RR-GUARD-005` | Is the incentive within tier, absolute, %-of-`V`, and per-customer period caps? | `DENY`, `ALLOW_WITH_MODIFICATION` |
| G6 | **Budget and capacity** | `RR-GUARD-006` | Can the ledger reserve every resource this action needs? | `DEFER` |
| G7 | **Approval threshold** | `RR-GUARD-007` | Does value, uncertainty, or action family require a human? | `REQUIRE_APPROVAL` |
| G8 | **Risk block** | `RR-GUARD-008` | Is there a fraud, legal, deceased, bankruptcy, or merchant-suppression flag? | `DENY` |
| G9 | **Duplicate suppression** | `RR-GUARD-009` | Is an equivalent action already in flight or recently executed? | `DENY` |
| G10 | **Stopping rules** | `RR-GUARD-010` | Does any of `SR-01…SR-11` fire right now? | `DENY` |
| G11 | **Channel eligibility** | `RR-GUARD-011` | Is this channel usable for this action and this customer state? | `DENY` |
| G12 | **Amount sanity** | `RR-GUARD-012` | Is the monetary effect within absolute and relative bounds? | `DENY` |

### 3.1 Per-gate specification

#### G1 · Consent

- Consent is per **channel** and per **purpose**. Consent for transactional payment notices does not
  imply consent for promotional incentives.
- Absence of a consent record is **not** consent. Unknown → deny.
- Consent revocation takes effect within one cycle and voids in-flight reservations.
- Non-contact actions (`A01`, `A02`, `A13`, `A14`) do not require contact consent, but do require the
  underlying mandate/authorisation to be valid, checked by G11.

#### G2 · Communication window

- Evaluated in the **customer's merchant-local timezone** (`Asia/Kolkata` default), from the virtual
  clock.
- Returns `DEFER`, not `DENY` — the action may be fine in four hours, and deferral preserves it.
- Windows differ by channel: a message and a voice call do not share acceptable hours.

#### G3 · Contact frequency cap

- Four independent counters: per-day, per-7-day, per-30-day, per-channel.
- Evaluated against **executed** contacts plus **reserved** ones, so two actions in the same cycle
  cannot both slip through (this is the gate half of the per-customer resource in
  [10 § 3.1](10-recovery-allocation.md)).
- At a hard cap → `DENY`. Within cap but inside a cooldown → `DEFER`.

#### G4 · Retry cap and cooldown

- Caps on attempts per opportunity, per instrument, and per period.
- Cooldown is cause-aware: `ISSUER_DOWNTIME` implies a longer cooldown than `INSUFFICIENT_FUNDS`.
  Cause-aware **timing** is allowed here because it is a declarative table keyed by cause code, not a
  model output.
- A retry after a `TIMEOUT_UNKNOWN` is denied until reconciliation completes (`RR-FUNC-065`) — the one
  case where the system refuses to retry money it is unsure about.

#### G5 · Incentive ceiling — the only gate that modifies

Four independent ceilings, all applied: tier maximum, absolute paise maximum, maximum percentage of
`V(i)`, and per-customer period cap.

`ALLOW_WITH_MODIFICATION` **clamps downward only**. It can never raise an incentive. Consequences:

1. The action is re-priced after clamping, and if the clamped action no longer clears `ε`, it becomes
   `NO_ACTION` — a clamp can turn a selected action into no action, and that is correct.
2. The modification is recorded with the original and clamped values, so a reviewer can see that the
   ceiling bound.
3. No other gate may modify. Modification is a controlled exception, not a general mechanism, because
   a gate that can rewrite actions is a gate that can be argued with.

#### G6 · Budget and capacity

- The only gate that talks to the Resource Ledger.
- Requests reservations for **all** resources atomically. Partial reservation is impossible; a partial
  grant is released immediately.
- Returns `DEFER` (capacity may exist next cycle), never `DENY`.
- Shadow-price inputs come from this gate's refusals.

#### G7 · Approval threshold

Triggers on any of:

| Trigger | Rationale |
|---|---|
| `V(i)` above a value band | Large money deserves a human |
| Wide `ENRV` interval on a material amount | Uncertainty × size is exactly when to ask |
| Action family flagged sensitive (`A10`, `A11`, `A12`, `A14`) | Incentives, voice, and collections handoffs are policy-sensitive |
| First-ever use of an action code for this merchant | A safe rollout property |
| Cumulative incentive to one customer crossing a band | Prevents drip-fed over-discounting |

`REQUIRE_APPROVAL` actions **never execute in the proposing cycle** (step 14 of the cycle,
[07 § 4](07-system-architecture.md)). They queue. If approved, they are re-gated in a later cycle.

#### G8 · Risk block

- REVIVE **does not adjudicate** fraud, insolvency, or legal status. It consumes flags set elsewhere
  and honours them absolutely (`OS-24`).
- Unknown flag state on a flag the pack marks as required → deny (fail closed).
- No override path exists in software. Removing a block is an out-of-band act by a human on the source
  system.

#### G9 · Duplicate suppression

Two mechanisms:

1. **Idempotency key check** — `H(opportunity_id, action_code, attempt_seq, cycle_id)` already present
   → deny.
2. **Semantic equivalence window** — an action of the same family to the same customer on the same
   channel within a configured window → deny, even with a different key. This catches the case where
   two distinct opportunities for one customer would each independently send a reminder.

#### G10 · Stopping rules

Delegates to C-14. Evaluated **twice**: at cycle start, and again immediately before execution
(`RR-FUNC-051`), because a success signal may have arrived in between. Failing the second evaluation
releases the reservation and produces `DEFERRED_STOPPED`.

#### G11 · Channel eligibility

- Channel must be technically available for the action, present on the customer record, and in a
  usable state (not bounced, not invalid, not unreachable).
- Voice requires a stricter eligibility set than messaging.
- A failed delivery marks the channel degraded, which affects subsequent eligibility — so the system
  does not keep sending to a dead address.

#### G12 · Amount sanity

The last line of defence against a numeric bug becoming a financial event.

| Check | Statement |
|---|---|
| Absolute cap | No single action's monetary effect exceeds the pack's absolute maximum |
| Relative cap | No incentive exceeds a configured fraction of `V(i)` |
| Retry amount identity | A retry's amount **equals** the original failed amount, exactly. Not more, not less |
| Non-negative | No action has a negative monetary effect |
| Unit assertion | The amount is an integer in paise and passed the `Paise` type boundary |

The retry-amount identity check is worth naming: it means REVIVE structurally cannot retry a different
amount than the one that failed, regardless of upstream bugs.

---

## 4. Verdicts

| Verdict | Meaning | Ledger | Next |
|---|---|---|---|
| `ALLOW` | Execute exactly this action, now | Reservation held → commit | C-17 executes |
| `ALLOW_WITH_MODIFICATION(params)` | Execute the clamped action | Reservation re-sized down | Re-priced; may become `NO_ACTION` |
| `DEFER(reason)` | Not now; reconsider next cycle | Released | Decision `DEFERRED` |
| `DENY(reason)` | Not permitted | Released | Decision `REJECTED` |
| `REQUIRE_APPROVAL(reason)` | Human must decide | Released (re-reserved after approval) | Queued in C-15 |

### 4.1 Combination rule

An action passes only if **every** applicable gate returns `ALLOW` or `ALLOW_WITH_MODIFICATION`.
Precedence when gates disagree:

```
DENY  >  REQUIRE_APPROVAL  >  DEFER  >  ALLOW_WITH_MODIFICATION  >  ALLOW
```

The most restrictive verdict wins. If two gates return contradictory *modifications*, the smaller
clamp applies, and the contradiction is logged as a **defect**, not silently resolved — contradictory
policy is a bug in the pack that someone should fix.

### 4.2 The full trace

Every gate's verdict is recorded, in order, including the ones that passed:

```
gate_trace = [
  { gate: "G1_CONSENT",   verdict: "ALLOW", evaluated_at, inputs_hash },
  { gate: "G2_WINDOW",    verdict: "ALLOW", ... },
  ...
  { gate: "G6_BUDGET",    verdict: "DEFER", reason: "incentive_budget_exhausted",
    detail: { requested_paise, available_paise } },
  ...
]
```

Recording passes matters as much as recording failures: it is the only way to prove a gate *ran*.
`RR-GUARD-027` requires that every gate appear in every trace for every applicable action, and a test
asserts no gate is ever silently skipped.

---

## 5. Gate supremacy, and the re-allocation prohibition

When a gate denies the allocator's chosen action, REVIVE does **not**:

- promote the runner-up candidate within the same cycle,
- re-run the allocator with the denied option removed,
- or retry the action with adjusted parameters.

The opportunity receives `REJECTED` (or `DEFERRED`) and is reconsidered from scratch next cycle.

**Why this restraint is deliberate.** In-cycle re-optimisation around a denial is functionally a
search for the nearest permitted action — which is how a system learns to route around its own
guardrails. It would also make the gate trace misleading, because the recorded denial would not
correspond to the executed action. `RR-GUARD-023` forbids it, and § 6.3 of
[10-recovery-allocation.md](10-recovery-allocation.md) tests it.

The cost is real and accepted: a cycle sometimes leaves capacity unused that a re-run would have
spent. That capacity appears in the next cycle.

---

## 6. Coverage requirements

A guardrail that never fires is undemonstrated. The benchmark must exercise all of them.

| Requirement | Statement |
|---|---|
| `RR-GUARD-027` | Every gate appears in every applicable trace |
| `RR-BENCH-*` | Every gate returns each of its possible verdicts at least once across the benchmark |
| `M-14` | Guardrail-block count, by gate and verdict, is a reported metric |
| `M-16` | Count of executed actions lacking an `ALLOW` verdict. **Must be exactly 0.** Non-zero is a build failure |
| Gate coverage table | Published in the evaluation report: gate × verdict × count. Empty cells are named and explained |

The synthetic dataset is designed to force this coverage: it includes customers without consent,
customers at their contact cap, actions above the incentive ceiling, high-value cases that trip
approval, risk-flagged customers, and cycles where the budget is deliberately too small
([19-synthetic-dataset.md](19-synthetic-dataset.md)).

---

## 7. Human authority

| Capability | Who | Requirement |
|---|---|---|
| Approve a queued action | Approver role | `RR-GUARD-007` |
| Reject a queued action | Approver role | `RR-GUARD-007` |
| Modify a queued action | Approver role — **re-enters all gates** | `RR-FUNC-066` |
| Global `HALT` | Any operator | `RR-GUARD-024` |
| Change the policy pack | Out of band, human only | `RR-GUARD-022` |
| Override a gate denial | **Nobody, in software** | `RR-GUARD-023` |

The last two rows together define the safety property: a human can change the *rules* (deliberately,
out of band, versioned, audited) but cannot make an *exception* to them at runtime. Exceptions are
invisible; rule changes are legible.

### 7.1 `HALT` semantics

| Property | Statement |
|---|---|
| Takes effect within one cycle | `RR-NFR-046` |
| Durable across restart | `RR-NFR-046` |
| In-flight reservations released | Ledger invariant preserved |
| In-flight adapter calls not abandoned silently | Outcome recorded; opportunity → `RECONCILING` if unknown |
| Recorded in the audit chain with actor and timestamp | `P-14` |
| Resuming is a separate, audited act | Not automatic |

---

## 8. Failure behaviour

| Failure | Behaviour |
|---|---|
| Policy pack missing or hash mismatch | **Deny every action for the cycle.** Cycle completes with all decisions `REJECTED_POLICY_UNAVAILABLE` |
| A gate raises an exception | That action is denied; the exception is logged as a defect; the cycle continues for other actions |
| State needed by a gate is stale or unreadable | Deny (fail closed) |
| Two gates contradict on modification | Smaller clamp wins; contradiction logged as a defect |
| Ledger unreachable at G6 | `DEFER` all budget-consuming actions; non-consuming actions may still proceed |
| Approval queue unwritable at G7 | Deny — an action that cannot be queued must not execute |
| Audit store unwritable | **Halt execution entirely** (`AI-4`) — an unauditable action is forbidden |

Every row reduces action. There is no failure path through the policy engine that permits more.

---

## 9. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-GUARD-001`…`012` | § 3.1, one subsection each |
| `RR-GUARD-020` no LLM in authority path | § 1 |
| `RR-GUARD-021` single execution path | [15-execution-model.md](15-execution-model.md) § 2 |
| `RR-GUARD-022` learner cannot write policy | § 2.1, § 7 |
| `RR-GUARD-023` verdicts final, no re-allocation | § 5 |
| `RR-GUARD-024` global halt | § 7.1 |
| `RR-GUARD-026` verdict replay | § 2.2 |
| `RR-GUARD-027` full gate trace | § 4.2 |
| `RR-FUNC-037` gates run after allocation | § 5 |
| `RR-FUNC-066` modified approvals re-gated | § 7 |

---

## 10. Open items

| Item | Label |
|---|---|
| Actual consent semantics and channel rules under Indian regulation (TRAI/DND, RBI recurring-payment norms) | `UNVERIFIED — MUST BE VERIFIED BEFORE ANY REAL USE`. The pack is structured to hold them; the values here are placeholders and are **not** legal advice |
| Permitted communication windows per channel | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION` |
| Contact cap values | `PROPOSED` placeholders; sensitivity reported |
| Approval threshold bands | `UNKNOWN`; merchant policy in reality |
| Whether G5's %-of-`V` ceiling should be per-action or cumulative per opportunity | `PROPOSED` cumulative, to prevent drip-fed discounting |
| Retry cap interaction with real issuer/network rules | `UNVERIFIED` ([36](36-razorpay-integration-assumptions.md)) |
