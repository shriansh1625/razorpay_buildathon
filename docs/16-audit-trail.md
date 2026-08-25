# 16 · Audit Trail

The Track 03 bar names an audit trail as a requirement. In REVIVE the audit trail is not a log — it is
the **system of record**. Application tables are projections of it, and where the two disagree, the
audit chain wins.

---

## 1. What it is for

Four distinct consumers, each needing something different:

| Consumer | Needs |
|---|---|
| **A merchant asking "why did you contact my customer?"** | The decision, the alternatives, the gate verdicts, in order |
| **A reviewer verifying no guardrail was bypassed** | Proof that every gate ran, and that no effect preceded its authorisation |
| **A judge checking the numbers are real** | A chain from every reported figure back to the events that produced it |
| **An engineer recovering from a crash** | Enough state to reconstruct application tables and settle the ledger |

The fourth is the reason it must be the system of record rather than a parallel narrative. A log you can
lose is not an audit trail; a log the system depends on cannot be lost silently.

---

## 2. Properties

| ID | Property | Enforcement |
|---|---|---|
| `RR-AUDIT-001` | **Append-only.** No update, no delete path exists | The data-access layer exposes only `append`. A test asserts an attempted update raises |
| `RR-AUDIT-002` | **Hash-chained.** Each event stores `prev_hash`; the chain is verifiable end to end | Chain verification runs on every benchmark run (`RR-NFR-051`) |
| `RR-AUDIT-003` | **Written before effect.** Intent is recorded before any adapter invocation | [15 § 2.1](15-execution-model.md) |
| `RR-AUDIT-004` | **Complete for money and permissions.** Every decision, verdict, reservation, execution, outcome, approval, policy change, halt, and stop is an event | § 4 catalogue |
| `RR-AUDIT-005` | **Reachable.** Every executed intervention is reachable to its decision, candidate set, diagnosis, and opportunity | `RR-NFR-052`, § 7 |
| `RR-AUDIT-006` | **Deterministic.** At a fixed seed, the event sequence is identical between runs, including hashes | `RR-NFR-020` |
| `RR-AUDIT-007` | **PII-free.** No field on the never-log list appears in any event | § 6, `RR-NFR-053` |
| `RR-AUDIT-008` | **Self-describing.** Each event carries its schema version | § 3 |
| `RR-AUDIT-009` | **Sufficient for reconstruction.** Application tables can be rebuilt from the chain | [15 § 2](15-execution-model.md) step 8 |
| `RR-AUDIT-010` | **Blocking.** If the audit store is unwritable, execution halts | `AI-4` |

`RR-AUDIT-010` deserves emphasis: unavailability of the audit store is treated as severely as a policy
failure. REVIVE will not act while it cannot record.

---

## 3. Event schema

```
AuditEvent
├── audit_id            aud_<ULID>            monotonic within a run
├── schema_version      integer
├── event_type          closed enum (§ 4)
├── occurred_at         virtual clock, ISO-8601 with offset
├── sequence_no         integer, gap-free within a run
├── prev_hash           hash of the previous event's canonical form
├── content_hash        hash of this event's canonical form
├── correlation
│   ├── run_id, cycle_id
│   ├── opportunity_id, decision_id, intervention_id      (as applicable)
│   └── customer_ref    pseudonymous token only
├── actor
│   ├── kind            SYSTEM | HUMAN | SCHEDULED | SIMULATED_APPROVER
│   ├── component       C-01 … C-28
│   └── identity        role token; never a personal name or email
├── versions
│   ├── policy_pack_version
│   ├── strategy_version
│   ├── generator_version
│   ├── prompt_version   (only where an LLM was involved)
│   └── code_version
├── payload             event-type-specific, schema-validated
└── payload_digest      hash of payload, for redaction-safe verification
```

### 3.1 Canonical form

Hashing requires a canonical serialisation, or the chain is not reproducible:

| Rule | Statement |
|---|---|
| Keys sorted lexicographically | No dict-order dependence |
| No insignificant whitespace | Fixed separators |
| Integers as integers; **no floats in hashed fields** | Floats are stored as their exact decimal string where unavoidable |
| Money as integer paise | `RR-NFR-001` |
| Timestamps as ISO-8601 with explicit offset, fixed precision | No locale dependence |
| Nulls explicit, never omitted | Absence and null must not hash alike |
| Enum values as their string names, not ordinals | Ordinals change when enums are extended |

### 3.2 `payload_digest` and redaction

The digest lets a payload be redacted later (if a field is ever discovered to be sensitive) while
leaving the chain verifiable: the chain hashes the digest, not the payload body. Redaction is recorded
as a *new* event (`REDACTION_APPLIED`), never as a mutation — consistent with `RR-AUDIT-001`.

---

## 4. Event catalogue

Closed enumeration. Adding a type is a schema-version change.

### 4.1 Detection and understanding

| Event | Payload highlights |
|---|---|
| `SIGNAL_INGESTED` | signal type, source ref, validation result |
| `SIGNAL_QUARANTINED` | rejection reason |
| `OPPORTUNITY_CREATED` | class, `value_at_risk_paise`, window, addressability |
| `OPPORTUNITY_UPDATED` | changed fields, before/after, trigger |
| `OPPORTUNITY_MERGED` | surviving id, merged id, natural key |
| `DEGRADATION_WINDOW_OPENED` / `_CLOSED` | cohort, severity, volume |
| `DIAGNOSIS_PRODUCED` | ranked cause codes, confidence bands, evidence refs, `llm_used`, cache hit/miss |
| `LLM_OUTPUT_REJECTED` | validator reason, fallback applied |

### 4.2 Simulation and decision

| Event | Payload highlights |
|---|---|
| `CANDIDATES_GENERATED` | action codes, parameters, count |
| `CANDIDATE_PRICED` | `p_action`, `p_natural`, `uplift`, `sigma`, cost components, `ENRV`, interval |
| `ALLOCATION_STARTED` | opportunity count, capacities, `ε` |
| `ALLOCATION_COMPLETED` | mode, iterations, runtime, shadow prices, binding constraints, optimality gap where measured |
| `ALLOCATOR_FALLBACK_TRIGGERED` | reason |
| `DECISION_RECORDED` | outcome, chosen action, runner-up `ENRV`, reason code, full candidate set ref |

### 4.3 Guarding

| Event | Payload highlights |
|---|---|
| `GATE_EVALUATED` | gate id, verdict, reason, inputs digest — **one event per gate, including passes** (`RR-GUARD-027`) |
| `ACTION_MODIFIED_BY_GATE` | gate, original params, clamped params |
| `STOPPING_RULE_FIRED` | rule id, evaluation point (cycle-start / pre-execution) |
| `OPPORTUNITY_STOPPED` | stop reason, `V` at stop |
| `OPPORTUNITY_REOPENED` | triggering evidence ref, counters carried forward |
| `APPROVAL_REQUESTED` | trigger, `V`, interval, action |
| `APPROVAL_RESOLVED` | outcome, actor role, latency, modification if any |
| `APPROVAL_EXPIRED` | validity window |
| `HALT_ENGAGED` / `HALT_RELEASED` | actor role, scope, reservations released |
| `POLICY_PACK_ACTIVATED` | version, hash |

### 4.4 Acting and verifying

| Event | Payload highlights |
|---|---|
| `RESOURCE_RESERVED` / `_COMMITTED` / `_RELEASED` / `_RECLAIMED` | resource, quantity, handle, ledger state after |
| `IDEMPOTENCY_KEY_CLAIMED` | key, action, attempt seq |
| `IDEMPOTENCY_CONFLICT` | key, blocked action |
| **`ACTION_INTENT`** | authorised action, params, key, reservation handle — **written before the adapter call** |
| `ACTION_RESULT` | adapter, typed result, latency |
| `RECONCILIATION_ATTEMPTED` | key, result or `UNRESOLVED`, attempt count |
| `RECONCILIATION_FAILED` | key, attempts, escalation |
| `OUTCOME_OBSERVED` | recovered amount, timing, partial flag, horizon used |
| `ATTRIBUTION_ASSIGNED` | class, rationale code |

### 4.5 Learning and run lifecycle

| Event | Payload highlights |
|---|---|
| `STRATEGY_VERSION_CREATED` | prior version, cells updated, calibration before/after |
| `EXPLORATION_DRAW` | cell, budget consumed |
| `RUN_STARTED` | seed, all versions, config hash, mode |
| `CYCLE_OPENED` / `CYCLE_CLOSED` | cycle id, virtual time, counts, duration |
| `CYCLE_ABORTED` | reason, step reached |
| `INVARIANT_VIOLATION` | invariant id, detail — **any occurrence is a build failure** |
| `RUN_COMPLETED` | artefact hashes, metric summary refs |
| `REDACTION_APPLIED` | target audit id, field, reason |

### 4.6 The completeness rule

> Every event that (a) moves money, (b) contacts a customer, (c) grants or denies a permission, (d)
> changes a version, or (e) changes an opportunity's state **must** appear in this catalogue.

A test walks the codebase's effect sites and asserts each emits a catalogued event. An effect without
an event is a defect, not a logging gap.

---

## 5. Hash chain

### 5.1 Construction

```
event[0].prev_hash    = H(run_id ‖ seed ‖ config_hash ‖ code_version)     # genesis binding
event[n].content_hash = H(canonical(event[n] without content_hash))
event[n+1].prev_hash  = event[n].content_hash
```

Binding the genesis hash to the run parameters means a chain cannot be transplanted between runs: an
event sequence from a different seed will not validate against this run's genesis.

### 5.2 What tamper-evidence does and does not give

| Property | Status |
|---|---|
| Detects modification of any past event | ✅ — the chain breaks at that point |
| Detects deletion of a past event | ✅ — `sequence_no` gap and hash mismatch |
| Detects insertion | ✅ |
| Detects **truncation of the tail** | ⚠️ **Only if the expected final hash is known independently.** The run artefact records the final hash and event count, so truncation is detectable against the artefact — but a party who can rewrite both is not defended against |
| Prevents tampering | ❌ **No.** This is tamper-*evidence*, not tamper-*proofing* |
| Provides third-party non-repudiation | ❌ No signing, no external anchoring, no notarisation |

Signing with an external key and anchoring the final hash outside the system are
`FUTURE / NOT IMPLEMENTED`. Stating this is required by `PP-4`: the audit trail must not be described
as immutable when it is append-only-by-construction-and-verifiable-by-hash, which is a weaker and more
accurate claim.

### 5.3 Verification is not optional

Chain verification runs as part of **every** benchmark run (`RR-NFR-051`), not as a separate manual
step. A run whose chain does not validate produces no metrics: the artefact is marked invalid. This
prevents the failure mode where verification exists but nobody runs it.

---

## 6. The never-log list

No field below may appear in any audit event, any application log, any metric label, any LLM prompt, or
any artefact. Enforced by a serialiser and by a canary test that plants sentinel values in the
synthetic data and scans every output for them (`RR-NFR-053`, `RR-NFR-062`).

### 6.1 Never logged, never stored

| Category | Fields |
|---|---|
| **Direct contact details** | Phone number, email address, postal address, messaging handle |
| **Payment instrument data** | Full card number, PAN, any digits beyond a network-safe last-four *token*, CVV, expiry in combination with a card reference, bank account number, IFSC + account pair, UPI VPA, token vault references |
| **Authentication material** | OTP, password, PIN, session token, cookie, bearer token, signing key, webhook secret, API key |
| **Government identifiers** | Aadhaar, PAN (tax), GSTIN of an individual, passport, driving licence |
| **Message bodies containing personal data** | The rendered outbound text. Only `template_id` + a digest of the variable set is logged |
| **Voice content** | Audio, transcript, or any recording reference |
| **Free-text merchant or customer notes** | May contain anything; treated as untrusted and unloggable |
| **Real customer names** | Only a pseudonymous `customer_ref` token appears |

### 6.2 Logged instead

| Instead of | Log |
|---|---|
| Phone / email | `channel_type` + `contact_ref` (pseudonymous, non-reversible within the system) |
| Card details | `method_type`, `network_band`, `instrument_ref`, `expiry_state` (enum, not a date) |
| Message body | `template_id`, `variable_set_digest`, `language_tag`, `copy_source` (`LLM` / `STATIC`) |
| Voice call | `duration_seconds`, `disposition_code` |
| Customer name | `customer_ref` |
| Notes | `notes_present: bool`, `notes_digest` |

### 6.3 Why this is easy here, and why that is not a virtue

This build uses **only synthetic data** (`OS-11`), so there is no real PII to leak. The never-log list
is nevertheless specified and enforced now, for two reasons:

1. A design that would leak PII if pointed at real data is not a safe design, whatever data it
   currently sees.
2. The canary test is meaningful on synthetic data: sentinel values are planted precisely so the
   enforcement path is exercised.

Enforcement is a serialiser-level deny-list, not a review convention (`P-13`). A field not on the
allow-list for a given sink does not reach that sink.

---

## 7. Reachability and reconstruction

### 7.1 The reachability requirement

`RR-NFR-052`: from any `ACTION_RESULT` event, a traversal must reach — with no missing link — the
`ACTION_INTENT`, the `GATE_EVALUATED` set, the `DECISION_RECORDED`, the `CANDIDATE_PRICED` set, the
`DIAGNOSIS_PRODUCED`, and the `OPPORTUNITY_CREATED`.

A test performs this traversal for **every** intervention in a benchmark run and fails on the first
broken link. Sampling is not permitted (`P-15` — no silent caps).

### 7.2 The question chain

The traversal exists so that these questions have mechanical answers:

```
"You charged this customer."
   → ACTION_RESULT        what happened
   → ACTION_INTENT        what was authorised, and when relative to the effect
   → GATE_EVALUATED[*]    which gates ran, in order, with verdicts
   → DECISION_RECORDED    why this action and not the alternatives
   → CANDIDATE_PRICED[*]  what the alternatives were worth
   → DIAGNOSIS_PRODUCED   what we thought was wrong, and how confident
   → OPPORTUNITY_CREATED  what was at risk, and how we valued it
```

No step in that chain requires an LLM-generated field. That is the audit-trail form of `P-6`.

### 7.3 Reconstruction

Application tables (`Opportunity`, `Decision`, `Intervention`, ledger balances) are rebuildable by
replaying the chain. A test truncates the application database, replays, and asserts equality with the
pre-truncation state. This test is what makes `RR-AUDIT-009` meaningful rather than aspirational.

---

## 8. Verification procedure

Runs automatically at the end of every benchmark run, and available as a standalone command:

| # | Check | Failure meaning |
|---|---|---|
| V-1 | `sequence_no` gap-free from 1 to N | Events lost |
| V-2 | Every `prev_hash` matches the predecessor's `content_hash` | Modification or insertion |
| V-3 | Every `content_hash` recomputes from canonical form | Payload altered |
| V-4 | Genesis hash matches the run's parameters | Chain from another run |
| V-5 | Final hash and count match the run artefact | Truncation |
| V-6 | Every `ACTION_RESULT` has a preceding `ACTION_INTENT` with a lower `sequence_no` | **Effect before authorisation — the most serious possible finding** |
| V-7 | Every `ACTION_INTENT` has a preceding full `GATE_EVALUATED` set with `ALLOW` | Guardrail bypass |
| V-8 | Reachability holds for every intervention | Broken lineage |
| V-9 | Ledger events balance: reserved = committed + released + reclaimed | Ledger integrity |
| V-10 | No never-log field present (canary scan) | Privacy violation |
| V-11 | No `INVARIANT_VIOLATION` events | Correctness failure |
| V-12 | Replay reconstructs application state exactly | Insufficient audit content |

V-6 and V-7 are the two checks that make the phrase "compliant escalation with an audit trail"
falsifiable rather than decorative.

---

## 9. What the audit trail is not

| Not | Because |
|---|---|
| A debug log | Debug logs are separate, unstructured-tolerant, and not chained. The audit chain contains only catalogued events |
| Immutable | Append-only and hash-verified. Not cryptographically notarised (§ 5.2) |
| Legally sufficient evidence | No signing, no external anchoring, no retention policy verified against regulation. `UNVERIFIED` |
| A metrics store | Metrics are derived artefacts, computed from the chain and stored separately |
| Free | It is the dominant write volume in the system; § 10 covers the cost |
| Optional under load | `RR-AUDIT-010` — execution halts rather than skipping audit |

---

## 10. Volume and cost

Honest accounting, since `RR-GUARD-027` requires an event per gate per action.

Per opportunity per cycle, roughly: 1 diagnosis + ~3 candidate pricings + 1 decision + up to 12 gate
events + reservation events + (if executed) intent/result/outcome. Order **20–25 events per considered
opportunity per cycle**.

| Mitigation | Statement |
|---|---|
| Events are small and structured | Digests instead of bodies |
| Gate events for non-selected candidates are **summarised**, not omitted | One event carrying the pre-filter reasons for the whole candidate set, plus full per-gate events for candidates that reached the gates. **The summarisation is declared here and logged as a summarisation** (`P-15`), not hidden |
| No sampling of interventions | Executed actions are always fully evented |
| Volume is a reported metric | `audit_events_per_cycle` |

The trade-off is stated rather than optimised silently: REVIVE accepts a large audit volume because the
audit trail is the product's defensibility.

---

## 11. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-AUDIT-001`…`010` | § 2 |
| `RR-NFR-050` append-only | `RR-AUDIT-001` |
| `RR-NFR-051` chain verifiable | § 5, § 8 |
| `RR-NFR-052` reachability | § 7 |
| `RR-NFR-053` never-log list | § 6 |
| `RR-GUARD-027` full gate trace | § 4.3 |
| `RR-GUARD-021` audit before effect | V-6, V-7 |
| `RR-NFR-042` crash recoverability | § 7.3 |
| `P-14` append-only, tamper-evident | § 2, § 5 |
| `AG-11` audit not lost on failure | `RR-AUDIT-010` |

---

## 12. Open items

| Item | Label |
|---|---|
| Hash function choice | `PROPOSED` SHA-256; must be recorded in the artefact so verification is unambiguous |
| External anchoring / signing | `FUTURE / NOT IMPLEMENTED` |
| Retention period and legal sufficiency | `UNVERIFIED`; out of scope for a hackathon build (`OS-31`) |
| Storage backend | `PROPOSED` append-only table + newline-delimited JSON export |
| Whether summarised pre-filter events are sufficient for a real audit | `UNKNOWN`; declared as a known limitation in § 10 |
| Whether `contact_ref` pseudonymisation needs to be irreversible outside the system too | `PROPOSED` yes for any real deployment; not applicable to synthetic data |
