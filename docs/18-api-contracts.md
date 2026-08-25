# 18 · API Contracts

Interface **shapes**, not implementations. Nothing here is client code; nothing here is called during
documentation. Status: **`PROPOSED`** unless a row says otherwise.

Three surfaces:

| Surface | Consumer | Nature |
|---|---|---|
| **Internal module contracts** (§ 2–§ 5) | Components `C-01`…`C-28` | In-process typed function signatures |
| **Read API** (§ 6) | The operator UI ([25](25-ui-ux-spec.md)) | HTTP, read-mostly |
| **Control API and CLI** (§ 7–§ 8) | Human operator, benchmark harness | HTTP + command line |

No **outbound** provider API is specified here. Outbound calls exist only behind the adapter interface
(§ 5), and only simulated implementations exist in this build (`OS-02`,
[36](36-razorpay-integration-assumptions.md)).

---

## 1. Cross-cutting contract rules

| # | Rule |
|---|---|
| AC-1 | Every money field is an integer paise field named `*_paise`. No API accepts or returns a float for money (`RR-NFR-001`) |
| AC-2 | Every timestamp is ISO-8601 with an explicit offset and is **virtual clock** time inside the engine (`README § C-3`) |
| AC-3 | Every enum is transported as its string name, never an ordinal (`16 § 3.1`) |
| AC-4 | Every response carries the versions that produced it: `policy_pack_version`, `strategy_version`, `code_version`, and `prompt_version` where an LLM was involved |
| AC-5 | No response contains a never-log field (`16 § 6`). The serialiser is allow-list based, so a new field is invisible until explicitly permitted |
| AC-6 | Errors are typed and closed (§ 9). No stack traces, no provider payloads, no free text derived from untrusted input |
| AC-7 | Every internal contract that can fail returns a typed result, never a bare `null` meaning "something went wrong" |
| AC-8 | Read endpoints are pure functions of stored state. No read endpoint triggers a decision, a cycle, or an effect |
| AC-9 | Every mutating endpoint requires an actor role and writes an audit event before its effect |
| AC-10 | Contracts are versioned; a breaking change is a new version, not a mutation (`RR-NFR-084`) |

**AC-8 is load-bearing.** A UI that can cause a cycle by being opened destroys reproducibility. The
read API is a window, not a trigger.

---

## 2. Detection and understanding contracts

```
ingest(signals: Signal[], clock: VirtualClock)
    -> IngestReport { accepted, deduplicated, quarantined, opportunities_created,
                      opportunities_updated }

detect(signal: Signal, existing: OpportunityIndex)
    -> DetectionResult = Created(Opportunity) | Merged(opportunity_id)
                       | Updated(opportunity_id, changed_fields)
                       | Ignored(reason_code)

value(opportunity: Opportunity, context: Context)
    -> Valuation { value_at_risk_paise, original_value_paise,
                   continuation_value_paise, basis_code, reductions[] }

addressability(opportunity, policy: PolicyPack, context)
    -> Addressable | NotAddressable(reason_code)

diagnose(opportunity, evidence: Evidence, cache: LLMCache, mode: LLMMode)
    -> Diagnosis { ranked_causes: [{cause_code, confidence_band, evidence_refs}],
                   unclassified, llm_used, cache_hit }
```

| # | Contract obligation |
|---|---|
| AC-11 | `diagnose` returns **no numeric field** other than counts. Bands only (`RR-GUARD-020`) |
| AC-12 | `diagnose` is total: an unparseable or absent LLM response yields `unclassified = true`, never an exception that stops the cycle |
| AC-13 | `value` never returns a value larger than the outstanding amount in the domain record (`LK-1`) |
| AC-14 | `detect` is idempotent on `dedupe_hash` |

---

## 3. Simulation, pricing, and allocation contracts

```
generate(opportunity, diagnosis, catalogue: ActionCatalogue, policy)
    -> ActionCandidate[]                    # always includes A00 NO_ACTION

predict(candidate, opportunity, strategy: StrategyVersion)
    -> Prediction { p_action, p_natural, uplift, sigma,
                    cell_key, shrinkage_level, horizon_minutes }

price(candidate, prediction, opportunity, policy)
    -> Priced { gross_paise, cost_paise, expected_incentive_paise,
                fatigue_cost_paise, enrv_paise, enrv_lo_paise, enrv_hi_paise }

allocate(priced: Priced[], capacities: Capacities, policy, mode: AllocatorMode)
    -> Allocation { assignments: [{opportunity_id, action_code}],
                    shadow_prices: {resource_key: price_paise},
                    binding_constraints: resource_key[],
                    mode_used, iterations, optimality_gap? , fallback_reason? }
```

| # | Contract obligation |
|---|---|
| AC-15 | `predict` never reads the outcome oracle, and no type it returns can carry oracle data (`AI-6`) |
| AC-16 | `price` is a pure function; called twice with the same arguments it returns byte-identical output |
| AC-17 | `allocate` returns exactly one assignment per input opportunity, `A00` included (`AL-1`) |
| AC-18 | `allocate` never returns an assignment violating a capacity (`AL-2`) |
| AC-19 | `allocate` reports `optimality_gap` where measured and omits it otherwise — it never estimates one (`10 § 6`) |
| AC-20 | `shadow_prices` are accompanied by `shadow_price_method`, so a `GREEDY_ESTIMATE` is never read as a dual optimum |

---

## 4. Guarding, reservation, and approval contracts

```
evaluate_policy(candidate, opportunity, context, policy)
    -> PolicyOutcome { verdict, gate_trace: GateVerdict[], modified_params?,
                       reason_code }
       # verdict ∈ ALLOW | ALLOW_WITH_MODIFICATION | DEFER | DENY | REQUIRE_APPROVAL

authorise(PolicyOutcome, ReservationHandle, IdempotencyKey)
    -> AuthorisedAction | AuthorisationRefused(reason_code)
       # AuthorisedAction has no public constructor (15 § 1.1)

check_stopping(opportunity, context, policy, point: CYCLE_START | PRE_EXECUTION)
    -> Continue | Stop(rule_id, detail)

reserve(items: [{resource_key, quantity}], cycle_id, decision_id)
    -> ReservationHandle | ReservationRefused(resource_key, requested, available)

commit(handle) -> LedgerState
release(handle, reason_code) -> LedgerState

request_approval(decision, policy) -> ApprovalRequest
resolve_approval(approval_id, resolution, actor_role, modified_params?)
    -> ApprovalResolved | ApprovalConflict(reason_code)
```

| # | Contract obligation |
|---|---|
| AC-21 | `evaluate_policy` returns a `gate_trace` containing **every** applicable gate, including passes, in fixed order (`RR-GUARD-027`) |
| AC-22 | `authorise` is the only producer of `AuthorisedAction`, and only on `ALLOW`/`ALLOW_WITH_MODIFICATION` |
| AC-23 | `reserve` is atomic; concurrent callers cannot jointly exceed a limit (`RR-NFR-041`) |
| AC-24 | `commit` and `release` are idempotent on `handle` |
| AC-25 | `resolve_approval` on an `EXPIRED` request returns `ApprovalConflict` — never an approval (`SR-06`) |
| AC-26 | `check_stopping` fails closed: an unreadable state returns `Stop` (`14 § 7`) |
| AC-27 | No contract in this section accepts an `ENRV` argument. Gates cannot see the objective (`13 § 1`) |

AC-27 is the mechanical form of gate supremacy: the *type signature* prevents a gate from being
influenced by how much money is at stake.

---

## 5. Execution and verification contracts

```
interface ActionAdapter:                          # frozen in 15 § 4
    supports(action_code) -> bool
    invoke(AuthorisedAction, idempotency_key, clock) -> AdapterResult
    reconcile(idempotency_key) -> AdapterResult | UNRESOLVED

AdapterResult = SUCCESS | FAILED_RETRYABLE | FAILED_TERMINAL
              | TIMEOUT_UNKNOWN | REJECTED_BY_PROVIDER

execute(AuthorisedAction) -> ExecutionRecord { intervention_id, adapter_result,
                                               intent_audit_id, result_audit_id,
                                               latency_ms }

observe(opportunity, horizon_minutes, clock)
    -> Outcome { recovered_amount_paise, partial, recovered_at,
                 observed_within_horizon, observability }

attribute(outcome, interventions)
    -> Attribution { class: ATTRIBUTED | NATURAL | AMBIGUOUS, rationale_code }

learn(outcomes, strategy_in: StrategyVersion) -> StrategyVersion
```

| # | Contract obligation |
|---|---|
| AC-28 | `execute` accepts **only** an `AuthorisedAction`. There is no overload taking a decision or an action code (`RR-GUARD-021`) |
| AC-29 | `execute` writes the intent audit event before calling `invoke`, and a test asserts the sequence numbers (`V-6`) |
| AC-30 | Adapters write nothing and decide nothing (`AD-2`, `AD-3`) |
| AC-31 | `attribute` resolves ambiguity against REVIVE by default (`AMBIGUOUS` is not counted as attributed) |
| AC-32 | `learn` has no return path into policy, budgets, or thresholds; its output type is `StrategyVersion` only (`RR-GUARD-022`) |
| AC-33 | `observe` returns `late_recovery` outcomes but they are excluded from attributed uplift (`17 § 4.8`) |

---

## 6. Read API

For the operator UI. HTTP, JSON, read-only, pure (AC-8).

| Method | Path | Returns |
|---|---|---|
| `GET` | `/runs` | Run summaries with seed, mode, versions, state, config hash |
| `GET` | `/runs/{run_id}` | Run detail incl. genesis/final hash, event count, artefact hashes |
| `GET` | `/runs/{run_id}/cycles` | Cycle list with counts by decision outcome and duration |
| `GET` | `/cycles/{cycle_id}` | Cycle detail: capacities, shadow prices, binding constraints, allocator mode, iterations |
| `GET` | `/cycles/{cycle_id}/decisions` | Decision list, filterable by outcome and reason code |
| `GET` | `/opportunities` | Filterable by class, state, ageing bucket, value band, stop reason |
| `GET` | `/opportunities/{opportunity_id}` | Full current state and counters |
| `GET` | `/opportunities/{opportunity_id}/timeline` | Ordered audit events for this opportunity |
| `GET` | `/decisions/{decision_id}` | Decision with the **whole candidate set**, ENRV components, runner-up, gate trace |
| `GET` | `/decisions/{decision_id}/explanation` | The `RR-UI-003` explanation object (§ 6.2) |
| `GET` | `/interventions/{intervention_id}` | Execution record, idempotency key, reservation, results |
| `GET` | `/approvals?state=QUEUED` | Approval queue with context and expiry |
| `GET` | `/resources/{run_id}` | Ledger state per resource: limit, committed, reserved, available, shadow price |
| `GET` | `/metrics/{run_id}` | `MetricSnapshot` set with derivation references |
| `GET` | `/audit/{run_id}?from=&to=` | Paged audit events |
| `GET` | `/audit/{run_id}/verification` | Result of checks `V-1`…`V-12` |
| `GET` | `/policy/{policy_pack_version}` | Sealed pack contents and hash |
| `GET` | `/strategy/{strategy_version}` | Band mapping, shrinkage constants, calibration summary |

### 6.1 Response envelope

```
{ data, versions{policy_pack, strategy, code, generator, prompt?},
  clock{virtual_now, run_id}, page{cursor, has_more}?,
  disclosure{ data_source: "SYNTHETIC", oracle_visible: false } }
```

`disclosure.data_source` is **mandatory on every response** (`RR-UI-007`). It is impossible to read a
number out of this system without also reading that it came from synthetic data.

### 6.2 The explanation object

The one response shape worth freezing, because it is what a merchant reads:

```
Explanation
├── opportunity { class, value_at_risk_paise, window_closes_at, ageing_bucket }
├── diagnosis   { top_causes[{cause_code, confidence_band}], unclassified }
├── chosen      { action_code, params, enrv_paise, components{...},
                  p_action, p_natural, uplift, interval }
├── alternatives[] { action_code, enrv_paise, why_not_reason_code }
├── contention  { binding_constraints[], shadow_prices{}, shadow_price_method,
                  displaced_by_opportunity_id? }
├── gates       [{ gate_id, verdict, reason_code }]          # all, including passes
├── outcome?    { recovered_amount_paise, attribution_class, rationale_code }
└── provenance  { decision_id, cycle_id, audit_event_ids[], versions{} }
```

Every field is deterministic. **No field of `Explanation` is LLM-generated** — the LLM's contribution
appears only as `cause_code` labels and, separately, as message copy that is not part of the
explanation (`P-6`, `16 § 7.2`).

---

## 7. Control API

Small by design. Four capabilities, each audited (AC-9).

| Method | Path | Effect |
|---|---|---|
| `POST` | `/approvals/{approval_id}/resolve` | Approve, approve-with-modification, or reject. Body carries `actor_role`, `resolution`, optional `modified_params` |
| `POST` | `/halt` | Engage global or scoped halt; releases reservations; body carries `actor_role`, `scope`, `reason` |
| `POST` | `/halt/release` | Explicit audited resume (`RR-GUARD-024`) |
| `POST` | `/opportunities/{opportunity_id}/suppress` | Merchant stop for one opportunity (`SR-11`) |

| # | Rule |
|---|---|
| AC-34 | There is **no** endpoint that overrides a gate denial, edits a decision, edits an outcome, or writes a metric (`13 § 7`) |
| AC-35 | There is **no** endpoint that triggers a cycle. Cycles are driven by the scheduler or the CLI, never by a UI action |
| AC-36 | `POST /halt` succeeds even when the decision engine is wedged — it is the one control path that must not depend on healthy components (`RR-NFR-046`) |
| AC-37 | Approve-with-modification returns the opportunity to re-pricing and re-gating; it does not authorise anything directly (`RR-FUNC-066`) |

The absence of AC-34's endpoints is a specified feature. A reviewer should be able to enumerate the
mutating surface — it is exactly four routes — and confirm that none of them can move money without a
gate.

---

## 8. CLI surface

The benchmark and reproducibility surface. Shapes only; **no command in this package is run**
(`DOCUMENTATION ONLY`).

| Command | Purpose |
|---|---|
| `revive generate --seed <n> --profile <name> --out <dir>` | Emit a synthetic dataset ([19](19-synthetic-dataset.md)) |
| `revive prepare --seed <n> --mode LLM_FULL` | PREPARE phase: populate the LLM cache. **The only phase permitted network access** (`09 § 6.2`) |
| `revive run --seed <n> --policy <ver> --strategy <ver> --mode <mode>` | EVALUATE phase: execute cycles offline; cache miss is a hard error |
| `revive baseline --name <B0…B5> --seed <n>` | Run a baseline policy on the identical dataset |
| `revive bench --seeds <list> --modes <list>` | Full matrix; writes the artefact set |
| `revive verify --run <run_id>` | Audit-chain checks `V-1`…`V-12` |
| `revive replay --run <run_id>` | Rebuild application state from the chain and assert equality (`V-12`) |
| `revive report --run <run_id> --out <file>` | Metric artefact with disclosures ([21](21-evaluation.md)) |
| `revive diff --run <a> --run <b>` | Byte-level artefact comparison for `RR-NFR-020` |

| # | Rule |
|---|---|
| AC-38 | `run` refuses to start if the mode requires an LLM and the cache is absent — it never falls back to a live call |
| AC-39 | Every command prints the resolved version set and config hash before doing anything |
| AC-40 | `bench` fails loudly on any `INVARIANT_VIOLATION`; it does not skip the seed and continue |
| AC-41 | No command has a flag that disables a gate, a stopping rule, or the audit trail. Test fixtures use their own harness, not a production flag |

AC-41 matters because `--no-guardrails` is exactly the flag that ends up in a demo.

---

## 9. Error taxonomy

Closed set. Every failure maps to one code, and every code has a defined effect on the cycle.

| Code | Meaning | Cycle effect |
|---|---|---|
| `VALIDATION_FAILED` | Input failed schema | Signal quarantined; cycle continues |
| `POLICY_PACK_INVALID` | Missing or unhashable pack | **Deny all actions this cycle** |
| `GATE_DENIED` | Normal denial | No action for that candidate |
| `APPROVAL_REQUIRED` | Awaiting human | Deferral |
| `APPROVAL_CONFLICT` | Resolving a non-`QUEUED` request | No effect |
| `RESOURCE_EXHAUSTED` | Capacity unavailable | Deferral |
| `RESERVATION_CONFLICT` | Concurrent claim lost | Deferral |
| `IDEMPOTENCY_CONFLICT` | Key already claimed | No action; reconcile path |
| `ADAPTER_TIMEOUT` | Unknown effect | `RECONCILING` |
| `ADAPTER_REJECTED` | Provider refused | Release; treated terminal |
| `RECONCILIATION_EXHAUSTED` | Unknown after max attempts | `RECONCILIATION_FAILED`; human escalation; **reported** |
| `LLM_UNAVAILABLE` | Model unreachable in PREPARE | Deterministic fallback; recorded |
| `LLM_CACHE_MISS` | Miss during EVALUATE | **Hard error; run invalidated** (`RR-NFR-035`) |
| `LLM_OUTPUT_INVALID` | Schema validation failed | Fallback; `LLM_OUTPUT_REJECTED` audited |
| `AUDIT_UNWRITABLE` | Cannot record | **Halt execution** (`RR-AUDIT-010`) |
| `INVARIANT_VIOLATION` | An invariant broke | Abort cycle; invalidate run; **build failure** |
| `CLOCK_INCONSISTENT` | Non-monotonic virtual time | Abort cycle |
| `HALTED` | Halt engaged | No actions; reservations released |

### 9.1 The direction rule

> **Every error path reduces action.** No error code has "proceed anyway" as its effect.

A reviewer can check this claim in one pass down the right-hand column: every entry is quarantine,
deny, defer, halt, abort, or escalate. None is "continue and execute."

---

## 10. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-UI-003` explanation available | § 6.2 |
| `RR-UI-007` synthetic-data disclosure on every surface | § 6.1 |
| `RR-GUARD-020` no numeric LLM output | AC-11 |
| `RR-GUARD-021` single execution path | AC-28, AC-29 |
| `RR-GUARD-022` learner isolation | AC-32 |
| `RR-GUARD-024` halt and audited resume | § 7, AC-36 |
| `RR-GUARD-027` full gate trace | AC-21 |
| `RR-FUNC-063` adapter interface | § 5 |
| `RR-FUNC-066` modified approvals re-gated | AC-37 |
| `RR-NFR-020` reproducibility | AC-16, § 8, AC-39 |
| `RR-NFR-035` no uncached LLM call in EVALUATE | AC-38, `LLM_CACHE_MISS` |
| `RR-NFR-041` ledger safety under concurrency | AC-23 |
| `RR-NFR-046` halt reliability | AC-36 |
| `RR-NFR-084` interface versioning | AC-10 |
| `RR-BENCH-*` benchmark surface | § 8 |

---

## 11. Open items

| Item | Label |
|---|---|
| Transport for the read API | `PROPOSED` HTTP+JSON; a local process boundary would also satisfy every contract here |
| Authentication and authorisation on the control API | `HACKATHON-SCOPE` single trusted local operator; real auth is `FUTURE / NOT IMPLEMENTED` |
| Pagination style | `PROPOSED` opaque cursor |
| Whether the read API should be served from the audit chain rather than projections | `PROPOSED` projections, with `V-12` proving equivalence |
| Real Razorpay request/response shapes | `UNVERIFIED` — the adapter interface deliberately does not mirror any real payload ([36](36-razorpay-integration-assumptions.md)) |
| Webhook ingress shape for real signals | `UNVERIFIED`; this build ingests generated signal files only |
| Rate limits, retries, and backoff against real providers | `FUTURE / NOT IMPLEMENTED` |
