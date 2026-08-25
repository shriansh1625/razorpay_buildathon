# 22 · Security and Privacy

A revenue-recovery agent that touches payment data, controls financial actions, and invokes LLMs
has a threat surface materially different from a typical application. This document is REVIVE's
threat model — scoped to the system as specified, not to a generic cybersecurity checklist.

> **Scope.** This threat model covers the hackathon build running on synthetic data with simulated
> adapters. Threats are categorised by whether they are exercisable in this build or would emerge
> only in a production deployment. Both are documented because the architecture must not *create*
> production-grade threats even if it does not *face* them yet.

---

## 1. Data protection

### 1.1 PII minimisation

| Control | Statement | Requirement |
|---|---|---|
| **No real PII in this build** | All customer, transaction, and instrument data is synthetic (`RR-BENCH-010`, [19](19-synthetic-dataset.md)) | `HACKATHON-SCOPE` |
| **Pseudonymous identifiers** | Customer references use `cust_<ULID>` tokens. No name, email, phone, or PAN appears in decision, audit, or metric tables | `RR-AUDIT-007` |
| **Never-log list** | The following fields must never appear in any log, audit event, metric snapshot, or LLM prompt: raw PAN, full card number, CVV, OTP, password, Aadhaar, unmasked phone, unmasked email, bank account number | `RR-NFR-053` |
| **Privacy canaries** | The synthetic dataset plants sentinel values from the never-log list. `M-57` scans all output sinks. Non-zero is a build failure | [19 § 7](19-synthetic-dataset.md) |
| **LLM context stripping** | Before any LLM call (C-05, C-10), a sanitiser removes all fields on the never-log list and replaces customer references with session-scoped tokens | `RR-NFR-064` |

### 1.2 Secret handling

| Threat | Mitigation | Label |
|---|---|---|
| API keys for LLM providers embedded in code | Environment variables or secret manager; never committed to version control | `PROPOSED` |
| Secrets in logs | Structured logging with a deny-list filter; secret fields masked at the serialisation boundary | `PROPOSED` |
| Secrets in audit events | Audit schema has no secret-typed field; the append-only store never receives one | `RR-AUDIT-007` |

### 1.3 Encryption

| Layer | Statement | Label |
|---|---|---|
| At rest | All persistent stores use filesystem-level or database-level encryption. `HACKATHON-SCOPE`: SQLite with application-level AES for sensitive columns is acceptable | `PROPOSED` |
| In transit | All external calls (LLM provider, future Razorpay API) over TLS 1.2+. Internal calls within a single process need no transport encryption | `PROPOSED` |
| Audit chain | Hash chain uses SHA-256 for integrity, not confidentiality. Tampering is detectable; reading requires access control | `RR-AUDIT-002` |

### 1.4 Data retention

| Data class | Retention | Rationale |
|---|---|---|
| Audit events | Indefinite within a run; output artefacts retained for reproducibility | Reconstruction depends on the full chain |
| Decision and intervention records | Lifetime of the run | Required for traceability |
| LLM prompt/response cache | Lifetime of the run; cache keys are content-hashed and contain no PII | Determinism requires cache persistence |
| Synthetic dataset | Retained alongside the run for reproducibility | `RR-NFR-020` |
| Metric snapshots | Retained with the run artefact | Evaluation depends on them |

### 1.5 Access control

| Principal | Access | Enforcement |
|---|---|---|
| Cycle Orchestrator (C-23) | Read/write per the permission model in [08 § 7](08-agent-architecture.md) | Code-level: only granted interfaces are importable |
| LLM agents (C-05, C-10) | Read only: sanitised context. Write only: schema-validated structured output | `RR-GUARD-020`; schema rejection on violation |
| Learning Engine (C-21) | Write: `StrategyVersion` and predictor parameters only. **No write access to policy, budget, threshold, or limit tables** | `RR-GUARD-022`; enforced at data-access layer |
| Human operator | Read: all UI screens. Write: approvals, `HALT`, policy pack changes (out of band) | `RR-GUARD-024` |
| Audit Store (C-22) | Append only. No update, no delete | `RR-AUDIT-001` |

---

## 2. Agent security

### T-01 · Prompt injection via failure-reason string

| Field | Value |
|---|---|
| **Threat** | A malicious or corrupted `failure_reason` string in a payment event contains instructions that alter C-05's diagnosis |
| **Attack surface** | C-05 Root Cause Analyst receives the raw failure-reason string as part of its context |
| **Potential impact** | Incorrect diagnosis → wrong candidate set → suboptimal or harmful action selection |
| **Likelihood** | LOW in hackathon (synthetic data); MEDIUM in production (reason strings from issuer responses) |
| **Mitigation** | (1) Failure reason is treated as **untrusted data**, never as an instruction. (2) C-05's output is constrained to a closed enum; any value outside the taxonomy is rejected. (3) Deterministic taxonomy mapping handles known codes without LLM involvement. (4) Schema validation rejects free-form causes. (5) Injection test corpus included in evaluation ([08 § 3](08-agent-architecture.md) C-05) |
| **Residual risk** | An injection that produces a valid-but-wrong taxonomy code. Mitigated by the confidence band — the deterministic path disagrees, lowering confidence |
| **Test method** | Adversarial injection corpus: inject known attack patterns in failure-reason fields; assert zero out-of-taxonomy outputs and zero behavioural change in pricing |

### T-02 · Prompt injection via merchant-authored policy text

| Field | Value |
|---|---|
| **Threat** | If natural-language policy interpretation (`RR-GUARD-027`, SHOULD) is implemented, a merchant could craft policy text that alters agent behaviour |
| **Attack surface** | Policy text → compiled rules pipeline |
| **Potential impact** | Policy bypass; guardrail circumvention |
| **Likelihood** | LOW (feature is SHOULD-tier and compilation is reviewed) |
| **Mitigation** | (1) Policy text is compiled to deterministic rules **before** runtime. (2) Compiled rules — not text — are enforced. (3) Compilation output is diffable and must be reviewed. (4) Runtime never consults free text |
| **Residual risk** | A compilation bug that misinterprets text. Mitigated by the review step and by the policy pack being versioned and sealed |
| **Test method** | Adversarial policy text corpus; assert compiled rules match expected semantics |

### T-03 · Malicious transaction content

| Field | Value |
|---|---|
| **Threat** | Transaction descriptions, invoice line items, or customer-facing fields contain payloads designed to influence LLM behaviour |
| **Attack surface** | C-10 Copy Composer receives template variables that may include product descriptions |
| **Potential impact** | Generated message copy includes unintended offers, misleading claims, or harmful content |
| **Likelihood** | LOW in hackathon; MEDIUM in production |
| **Mitigation** | (1) C-10 receives only a whitelisted variable set — no raw transaction descriptions. (2) Template slots for monetary values, percentages, dates, and URLs are populated by deterministic code, not by the LLM. (3) The renderer rejects any LLM attempt to populate a `*_paise` or `*_pct` slot. (4) Fallback to static template text is always available |
| **Residual risk** | A product-name token that subtly influences tone. Impact is cosmetic, not financial |
| **Test method** | Adversarial product-name tokens; assert zero monetary-slot violations and zero offers not in the template |

### T-04 · Tool abuse / unauthorised action requests

| Field | Value |
|---|---|
| **Threat** | An LLM agent attempts to invoke tools or adapters beyond its granted set |
| **Attack surface** | C-05 and C-10 LLM call boundaries |
| **Potential impact** | Unauthorised data access; unauthorised action execution |
| **Likelihood** | LOW — REVIVE's LLM agents have **no tool access** from within an LLM call ([08 § 8](08-agent-architecture.md)). The LLM receives a prepared context and returns a structured value |
| **Mitigation** | (1) LLM calls are single-turn, no tool use. (2) No tool registry is exposed to the model. (3) Output is schema-validated; anything outside the expected structure is discarded. (4) No reflection-based dispatch on model output (`RR-GUARD-025`) |
| **Residual risk** | Effectively zero in the current architecture. The LLM has no mechanism to invoke anything |
| **Test method** | Include tool-invocation instructions in test prompts; assert no tool call is made and output is schema-valid |

### T-05 · Privilege escalation

| Field | Value |
|---|---|
| **Threat** | A module acquires capabilities beyond its grant at runtime |
| **Attack surface** | Module boundaries; data-access layer |
| **Potential impact** | Policy bypass; unauthorised execution; budget manipulation |
| **Likelihood** | LOW — capability model is static and enforced at the interface level |
| **Mitigation** | (1) Permission model ([08 § 7](08-agent-architecture.md)) is the authoritative grant list. (2) No module may grant itself a capability at runtime. (3) No dynamic tool discovery. (4) Data-access layer enforces write restrictions (e.g., C-21 cannot write policy tables). (5) Exactly one code path reaches an execution adapter (`RR-GUARD-021`) |
| **Residual risk** | A code-level bug that exposes a forbidden interface. Mitigated by the single-execution-path test |
| **Test method** | For each module, attempt every forbidden operation; assert all raise |

### T-06 · Policy bypass via re-allocation after denial

| Field | Value |
|---|---|
| **Threat** | After a gate denies an action, the system re-optimises to find an action that circumvents the denied rule |
| **Attack surface** | The boundary between C-12 (Allocator) and C-13 (Policy Engine) |
| **Potential impact** | Guardrail circumvention; the gate trace would not match the executed action |
| **Likelihood** | LOW — explicitly forbidden by `RR-GUARD-023` |
| **Mitigation** | (1) No in-cycle re-optimisation after a denial ([13 § 5](13-policy-and-guardrails.md)). (2) A denied opportunity receives `REJECTED` or `DEFERRED` and is reconsidered from scratch next cycle. (3) Test asserts no runner-up promotion within a cycle |
| **Residual risk** | None if the prohibition is implemented correctly |
| **Test method** | Inject a scenario where the top candidate is denied; assert no second candidate executes in the same cycle |

---

## 3. Financial safety

### T-07 · Unauthorised discount / incentive

| Field | Value |
|---|---|
| **Threat** | An incentive above the merchant-configured ceiling is applied |
| **Attack surface** | Incentive computation → G5 Incentive Ceiling gate |
| **Potential impact** | Financial loss to the merchant; margin erosion |
| **Likelihood** | LOW — G5 clamps or denies |
| **Mitigation** | (1) G5 enforces four independent ceilings: tier maximum, absolute paise, %-of-V, per-customer period cap. (2) `ALLOW_WITH_MODIFICATION` clamps downward only — never raises. (3) Clamped action is re-priced; if `ENRV ≤ ε`, it becomes `NO_ACTION`. (4) `RR-GUARD-020`: no LLM output may become a monetary value |
| **Residual risk** | A bug in the clamping arithmetic. Mitigated by G12 amount sanity as a second line |
| **Test method** | Inject incentives above each ceiling; assert all are clamped or denied; assert no executed incentive exceeds any ceiling |

### T-08 · Repeated / duplicate action execution

| Field | Value |
|---|---|
| **Threat** | The same recovery action is executed twice for the same opportunity |
| **Attack surface** | Execution path; adapter invocation; crash recovery |
| **Potential impact** | Double-charging; duplicate customer contact; budget over-consumption |
| **Likelihood** | MEDIUM — crashes and timeouts create the conditions |
| **Mitigation** | (1) Mandatory idempotency key per execution (`RR-FUNC-060`). (2) G9 Duplicate Suppression checks both idempotency key and semantic equivalence window. (3) `TIMEOUT_UNKNOWN` → `RECONCILING`, no further action until resolved (`RR-FUNC-065`). (4) State machine forbids `ACTING → ACTING` and `RECONCILING → ACTING` ([34 § 1.3](34-state-machine.md)) |
| **Residual risk** | An adapter that does not honour idempotency. In the hackathon build, the simulator respects it by construction |
| **Test method** | Crash-injection between audit-intent and adapter-call; assert no duplicate effect; duplicate-key test returns stored result |

### T-09 · Action replay

| Field | Value |
|---|---|
| **Threat** | A previously valid action is replayed after conditions have changed (stale decision) |
| **Attack surface** | Time between decision computation and execution |
| **Potential impact** | Action on a recovered opportunity; action after a stopping rule should have fired |
| **Likelihood** | MEDIUM — state changes mid-cycle |
| **Mitigation** | (1) Stale-decision detection (`RR-FUNC-043`): if opportunity state changed after decision, action is not executed. (2) Pre-execution stopping-rule re-evaluation (`RR-FUNC-051`). (3) Two-phase reservation: stale actions release their reservation |
| **Residual risk** | A state change between the second stopping check and adapter invocation. Window is minimised by the execution sequence |
| **Test method** | Inject a mid-cycle success signal; assert no action executes on the recovered opportunity |

### T-10 · Race condition on budget

| Field | Value |
|---|---|
| **Threat** | Two concurrent cycles or actions over-consume a shared resource |
| **Attack surface** | Resource Ledger (C-16) |
| **Potential impact** | Budget exceeded; capacity invariant violated |
| **Likelihood** | LOW in hackathon (single-threaded cycle); MEDIUM in production |
| **Mitigation** | (1) Two-phase `RESERVE → COMMIT/RELEASE` with atomic reservation. (2) Invariant `committed[r] + reserved[r] ≤ limit[r]` checked after every transition ([34 § 4](34-state-machine.md)). (3) Violation aborts the cycle. (4) Orphaned reservations reclaimed at cycle open |
| **Residual risk** | Implementation bug in atomic reservation. Mitigated by the invariant assertion |
| **Test method** | Property test under injected concurrency; assert invariant holds and no over-consumption occurs (`RR-NFR-041`) |

### T-11 · Budget bypass via Learning Engine

| Field | Value |
|---|---|
| **Threat** | The Learning Engine (C-21) modifies policy limits, budget caps, or approval thresholds |
| **Attack surface** | C-21's write path |
| **Potential impact** | Guardrail erosion over time; budget expansion without authorisation |
| **Likelihood** | LOW — structurally prevented |
| **Mitigation** | (1) `RR-GUARD-022`: C-21 has no write access to policy, budget, threshold, or limit tables, enforced at the data-access layer. (2) Write attempt raises. (3) C-21 can only write `StrategyVersion` and predictor parameter rows |
| **Residual risk** | None if data-access enforcement is correct |
| **Test method** | Attempt policy/budget/threshold writes from C-21; assert all raise |

### T-12 · Approval bypass

| Field | Value |
|---|---|
| **Threat** | An action that requires approval (`REQUIRE_APPROVAL` verdict from G7) executes without a valid approval |
| **Attack surface** | Execution path after approval queue |
| **Potential impact** | Unauthorised high-value or high-uncertainty actions |
| **Likelihood** | LOW — `M-18` is a tier-0 guardrail |
| **Mitigation** | (1) `REQUIRE_APPROVAL` actions never execute in the proposing cycle. (2) Approved actions re-enter all gates. (3) Expired approvals are voided (`SR-06`). (4) `M-18` computed by independent evaluator. (5) Silence is never consent |
| **Residual risk** | A code path that skips the approval check. Mitigated by `M-18` being independently computed |
| **Test method** | Assert zero executions of `REQUIRE_APPROVAL` actions without a valid, unexpired, matching approval |

---

## 4. Model safety

### T-13 · LLM hallucination in diagnosis

| Field | Value |
|---|---|
| **Threat** | C-05 produces a cause code that is plausible but wrong, leading to an inappropriate action |
| **Attack surface** | LLM output in diagnosis |
| **Potential impact** | Wrong candidate set; suboptimal action; wasted spend |
| **Likelihood** | MEDIUM — LLMs hallucinate |
| **Mitigation** | (1) Output constrained to a closed enum; out-of-taxonomy values rejected. (2) Confidence bands (LOW/MED/HIGH) mapped to numeric priors by a versioned deterministic table the analyst cannot see or change. (3) Deterministic fallback always available. (4) A wrong diagnosis shifts candidate ranking but does not bypass any gate. (5) `M-27` measures diagnosis agreement |
| **Residual risk** | A valid-but-wrong code at HIGH confidence. Impact is economic (wrong action selected), not safety (gates still enforce all constraints) |
| **Test method** | Diagnosis agreement against generator ground truth; band calibration — HIGH must be right more often than MED |

### T-14 · False confidence in predictions

| Field | Value |
|---|---|
| **Threat** | The Recovery Predictor (C-07) produces tight uncertainty intervals that do not reflect true uncertainty |
| **Attack surface** | `sigma` output from C-07 |
| **Potential impact** | Actions that should require approval (G7) bypass the uncertainty threshold; over-allocation to poorly-understood opportunities |
| **Likelihood** | MEDIUM — calibration is hard |
| **Mitigation** | (1) Unseen feature combination → shrink to parent cell's prior and inflate `sigma`. (2) `M-24` (calibration) reported per run. (3) Reliability curve published. (4) Context-degraded flag raises uncertainty. (5) G7 triggers on wide intervals |
| **Residual risk** | Systematic overconfidence on a novel population. Mitigated by calibration monitoring and the `ABUNDANT` profile where over-confident allocation is less harmful |
| **Test method** | ECE and Brier score on eval split; reliability curve; assert `sigma` non-null on every candidate |

### T-15 · Invalid reasoning / corrupted context

| Field | Value |
|---|---|
| **Threat** | The LLM receives a corrupted or incomplete context object and produces a structurally valid but semantically nonsensical output |
| **Attack surface** | Context assembly (C-04) → LLM call |
| **Potential impact** | Misdiagnosis; inappropriate tone in communications |
| **Likelihood** | LOW — context degradation is detected and flagged |
| **Mitigation** | (1) `context_degraded = true` flag when fields are missing. (2) Degraded context raises the uncertainty term downstream. (3) Schema validation on all context objects. (4) LLM call receives the degradation flag; deterministic fallback can be used |
| **Residual risk** | A context that passes schema validation but is internally inconsistent. Impact is economic, not safety |
| **Test method** | Inject incomplete and contradictory contexts; assert degradation flag is set; assert deterministic fallback activates when appropriate |

### T-16 · Model drift

| Field | Value |
|---|---|
| **Threat** | Over successive learning cycles, predictor parameters drift to values that produce systematically biased estimates |
| **Attack surface** | Learning Engine (C-21) parameter updates |
| **Potential impact** | Miscalibrated predictions; systematic over-action or under-action |
| **Likelihood** | LOW in hackathon (limited cycles); MEDIUM in production |
| **Mitigation** | (1) Every decision records `strategy_version`. (2) A version that degrades calibration (`M-24`) is rolled back. (3) Capped exploration budget supplies data for unacted cells. (4) Shrinkage toward parent cells prevents overfitting. (5) Learning-on vs learning-off ablation both reported |
| **Residual risk** | Drift within a single run too subtle to trigger rollback. Mitigated by the ablation comparison |
| **Test method** | Monitor `M-24` across cycles; learning-on vs learning-off ablation; assert calibration does not degrade |

---

## 5. Threat summary matrix

| ID | Threat | Category | Likelihood | Impact | Severity | Exercisable in hackathon? |
|---|---|---|---|---|---|---|
| T-01 | Prompt injection via failure reason | Agent | LOW | MEDIUM | LOW | Yes (injection corpus) |
| T-02 | Prompt injection via policy text | Agent | LOW | HIGH | MEDIUM | Only if SHOULD feature built |
| T-03 | Malicious transaction content | Agent | LOW | LOW | LOW | Yes (adversarial tokens) |
| T-04 | Tool abuse | Agent | LOW | HIGH | LOW | Yes (test prompts) |
| T-05 | Privilege escalation | Agent | LOW | HIGH | MEDIUM | Yes (forbidden-op tests) |
| T-06 | Policy bypass via re-allocation | Agent | LOW | HIGH | LOW | Yes (denial test) |
| T-07 | Unauthorised discount | Financial | LOW | HIGH | MEDIUM | Yes (ceiling tests) |
| T-08 | Duplicate execution | Financial | MEDIUM | HIGH | HIGH | Yes (crash injection) |
| T-09 | Action replay | Financial | MEDIUM | MEDIUM | MEDIUM | Yes (stale-decision test) |
| T-10 | Budget race condition | Financial | LOW | HIGH | MEDIUM | Yes (property test) |
| T-11 | Budget bypass via learning | Financial | LOW | HIGH | LOW | Yes (write-attempt test) |
| T-12 | Approval bypass | Financial | LOW | HIGH | LOW | Yes (M-18 check) |
| T-13 | LLM hallucination | Model | MEDIUM | MEDIUM | MEDIUM | Yes (diagnosis eval) |
| T-14 | False confidence | Model | MEDIUM | MEDIUM | MEDIUM | Yes (calibration eval) |
| T-15 | Corrupted context | Model | LOW | LOW | LOW | Yes (injection test) |
| T-16 | Model drift | Model | LOW | MEDIUM | LOW | Partially (limited cycles) |

---

## 6. Audit-log protection

| Control | Statement |
|---|---|
| Append-only | No update/delete path (`RR-AUDIT-001`) |
| Hash chain | Tampering detection (`RR-AUDIT-002`) |
| Blocking on failure | Execution halts if audit store is unwritable (`RR-AUDIT-010`) |
| PII-free | Never-log list enforced; canary scan (`M-57`) |
| Reconstruction | Application state derivable from chain alone (`RR-AUDIT-009`) |
| Verification | `V-1`…`V-12` checks run on every benchmark run (`M-58`) |

---

## 7. Requirement mapping

| Requirement | Where in this document |
|---|---|
| `RR-NFR-053` never-log list | § 1.1 |
| `RR-NFR-064` LLM context stripping | § 1.1 |
| `RR-GUARD-020` no LLM in money path | § 2 (T-04, T-07), § 3 (T-07) |
| `RR-GUARD-021` single execution path | § 2 (T-05) |
| `RR-GUARD-022` learning cannot write policy | § 3 (T-11) |
| `RR-GUARD-023` verdicts final | § 2 (T-06) |
| `RR-AUDIT-001`…`010` | § 6 |
| `RR-FUNC-060` idempotency | § 3 (T-08) |
| `RR-FUNC-065` reconciliation blocks action | § 3 (T-08) |
| `RR-FUNC-043` stale-decision detection | § 3 (T-09) |
| `RR-FUNC-051` pre-execution stopping check | § 3 (T-09) |
| `RR-NFR-041` ledger invariant | § 3 (T-10) |

---

## 8. Open items

| Item | Label |
|---|---|
| Specific encryption algorithm and key management for production | `FUTURE` |
| TLS certificate management for real Razorpay API integration | `FUTURE` |
| Real consent semantics under TRAI/DND and RBI norms | `UNVERIFIED` — see [13 § 10](13-policy-and-guardrails.md) |
| Rate limiting on LLM provider calls to prevent cost attacks | `PROPOSED` — bounded by the single-call-per-opportunity design |
| Whether the audit chain hash algorithm should be configurable | `PROPOSED` SHA-256 fixed |
| IP-based access control for the operator UI | `FUTURE` |
