# 19 · Synthetic Dataset

Every number REVIVE will ever report comes from this generator. That makes the dataset the single
largest threat to the honesty of the whole package: a generator can be tuned, consciously or not, until
the product looks good.

This document therefore spends more space on **how the dataset could be rigged and what prevents it**
than on the dataset itself.

> **Disclosure, binding on every artefact (`RR-BENCH-010`):** all data is synthetic. No real merchant,
> customer, transaction, or payment rail is involved. The generator's fidelity to real payment
> behaviour is **`UNVERIFIED`**. No result produced against it is evidence about the real world.

---

## 1. What the dataset must provide

| # | Requirement | Why |
|---|---|---|
| DS-1 | A population of opportunities across all five risk classes | `RR-BENCH-001` |
| DS-2 | A **hidden outcome oracle** answering "what would have happened under action `a`" | Uplift cannot be measured without a counterfactual (`11 § 1`) |
| DS-3 | A **non-trivial natural-recovery process** — some opportunities recover with no intervention | Without it, `p(i,∅) = 0` and the product's central idea is untestable (`CF-7`) |
| DS-4 | Genuine scarcity — demand for every resource exceeding supply | Without contention, allocation is not being tested at all (`10 § 1`) |
| DS-5 | Conditions that fire every gate and every stopping rule | `13 § 6`, `14 § 6` require coverage |
| DS-6 | Late, duplicate, out-of-order, and malformed signals | `RR-NFR-045`, `DM-5`, `DM-6` |
| DS-7 | Adversarial and degenerate cases | § 6 |
| DS-8 | Full determinism from a seed | `RR-NFR-020` |
| DS-9 | Cause signals that are **incomplete and partly misleading** | Otherwise diagnosis is a lookup, and `UNCLASSIFIED` never occurs (`12 § 8.2`) |
| DS-10 | Planted privacy canaries | `RR-NFR-053` enforcement must be exercised (`16 § 6.3`) |

DS-3 and DS-4 are the two that decide whether the benchmark means anything. A dataset where nothing
recovers on its own and nothing is scarce would make REVIVE's allocation logic indistinguishable from
"contact everyone", and every baseline would tie.

---

## 2. Generator design

### 2.1 Determinism

| Rule | Statement |
|---|---|
| One seed drives everything | `--seed <n>` |
| **Separate labelled PRNG streams** | `stream(seed, "generator")`, `stream(seed, "oracle")`, `stream(seed, "exploration")`, `stream(seed, "approver")` |
| Streams are independent | Consuming a different number of draws in one stream cannot shift another. This is what stops a code change in the allocator from changing the dataset |
| Generator version is recorded | `generator_version` in every audit event and artefact |
| Output is content-hashed | `dataset_hash` is part of `config_hash` (`RR-NFR-021`) |
| No wall clock, no OS entropy | `RR-NFR-022` |

The labelled-stream rule is not a detail. With a single stream, adding one exploration draw would
re-roll every subsequent outcome, and two runs of "the same" experiment would silently differ.

### 2.2 Generation order

```
1  Merchant + policy pack parameters
2  Customer population with latent traits          (see § 3)
3  Instruments, mandates, consent records
4  Commercial history: orders, invoices, subscriptions, checkout sessions
5  Failure/abandonment/overdue events → the signal stream
6  For each resulting opportunity: draw the ORACLE ROW                (§ 4)
7  Inject adversarial cases                                          (§ 6)
8  Inject signal-hygiene faults                                      (§ 5.3)
9  Plant privacy canaries                                            (§ 7)
10 Emit dataset files + manifest + hashes
```

Step 6 happens **at generation time, not at decision time**. The oracle is fixed before REVIVE runs,
so REVIVE cannot influence what the counterfactual world would have been.

### 2.3 Profiles

Named parameter sets, all `PROPOSED`, all frozen before measurement:

| Profile | Character | Purpose |
|---|---|---|
| `BALANCED` | Mixed classes, moderate scarcity | Primary benchmark |
| `HIGH_NATURAL` | Many opportunities self-recover | Punishes over-contacting; the profile where naive baselines lose most |
| `SCARCE` | Severe budget and capacity limits | Stresses allocation and shadow prices |
| `ABUNDANT` | Near-unlimited capacity | **Expected to shrink REVIVE's advantage** toward the greedy baseline. Included precisely because it is unflattering (§ 8.2) |
| `HOSTILE` | Heavy adversarial injection | Tests guardrails and stopping, not revenue |
| `DEGRADED` | Provider outage windows, predictor drift | Tests degradation behaviour |

Reporting every profile — including `ABUNDANT`, where the differentiator is expected to matter least —
is required by `P-7`. A single flattering profile is metric theatre.

### 2.4 Scale

| Parameter | Label |
|---|---|
| Opportunity count per run | `PROPOSED` on the order of a few hundred to a few thousand; must satisfy `RR-NFR-030` (≤ 10 s/cycle at 500 opportunities) and `RR-BENCH-002` (a *batch*, not a single case) |
| Cycle count | `PROPOSED` enough virtual days for windows to close and multi-attempt sequences to play out |
| Customer count | `PROPOSED` fewer than opportunities, so per-customer contention is real |
| Exact distributions | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION`, and whatever is chosen is **invented**, not derived from real data |

---

## 3. Customer and opportunity latent structure

Each customer carries **latent traits the decision path cannot read**:

| Latent trait | Effect on the oracle |
|---|---|
| `intent_to_pay` | Dominates natural recovery |
| `responsiveness{channel}` | Whether a message changes anything |
| `price_sensitivity` | Whether an incentive changes anything |
| `annoyance_threshold` | When contact starts to *reduce* recovery probability |
| `instrument_health_trajectory` | Whether a retry could ever succeed |
| `attention_delay` | How long a real response takes, which interacts with `H` |

The engine sees only **observable proxies** — segment, tenure band, value band, prior self-recovery
rate, failure history. The gap between latent truth and observable proxy is what makes the prediction
problem real. If the engine could see `intent_to_pay`, calibration would be trivial and the benchmark
would measure nothing.

| # | Rule |
|---|---|
| DS-11 | Latent traits are stored in the oracle partition, never in the DOMAIN tables the engine reads (`17 § 4.8`) |
| DS-12 | A test asserts no decision-path module can reach the oracle partition (`AI-6`) |
| DS-13 | Observable proxies are **noisy** functions of latent traits, never invertible |

`annoyance_threshold` deserves a note: it is the mechanism by which over-contacting actively destroys
value in the simulation rather than merely wasting budget. Without it, `λ_f · F(i,a)` would be a
cost REVIVE pays for nothing, and fatigue modelling would be unfalsifiable.

---

## 4. The outcome oracle

### 4.1 Shape

For each opportunity, one row generated **once**, before any run:

```
OracleRow(opportunity_id)
├── recovers_naturally: bool          # under action ∅
├── natural_recovery_at: timestamp    # may fall outside H
├── natural_amount_paise
├── per_action_response: { action_code → { would_recover: bool,
│                                          recover_at: timestamp,
│                                          amount_paise,
│                                          adapter_result_override? } }
├── fatigue_curve: contact_count → multiplicative response factor
└── degradation_window_membership: cohort refs
```

### 4.2 Rules

| # | Rule | Why |
|---|---|---|
| OR-1 | Drawn from `stream(seed, "oracle")` only | Independence from engine behaviour |
| OR-2 | Fixed before the run; never regenerated mid-run | Otherwise the counterfactual is contaminated by what REVIVE did |
| OR-3 | Reachable **only** by simulated adapters and the evaluator | `AD-8`, `AI-6` |
| OR-4 | Contains cases where **an action makes things worse** | Uplift must be able to be negative, or `ENRV` filtering is untested |
| OR-5 | Contains cases where the *correct* answer is `NO_ACTION` for reasons other than cost | `RR-BENCH-006` |
| OR-6 | Timing matters: `recover_at` may fall after `H`, so a "would have worked" action still scores zero | Makes horizon choice consequential |
| OR-7 | Oracle-derived numbers never enter a prompt, a predictor update, or a decision | Type-level separation |

OR-4 and OR-6 are what make the oracle adversarial rather than accommodating. A generous oracle —
every action helps, timing always cooperates — would make almost any policy look competent.

### 4.3 Consistency constraint

The oracle must be **internally coherent**, or `ENRV` becomes unlearnable noise:

| Constraint | Statement |
|---|---|
| A customer with an invalid instrument does not have `A01 RETRY_PAYMENT_NOW` succeed | Physical impossibility must not be rewarded |
| A customer who declined to pay does not respond to reminders | Terminal means terminal |
| Fatigue is monotone non-increasing in contact count | Otherwise more contact could randomly be better |
| A larger incentive is never *less* effective for the same customer | Monotonicity in the incentive tier |
| Natural recovery and action recovery share the same latent `intent_to_pay` | So `u = p_a − p_∅` is genuinely small for high-intent customers — the exact regime the product is designed to detect |

The last row is the dataset property that makes `CF-7` (natural-recovery dominance) a real test rather
than a coincidence.

---

## 5. Population content

### 5.1 By risk class

| Class | Generated substrate | Notes |
|---|---|---|
| `PAYMENT_FAILURE` | Orders with failed attempts, varied reason codes, some retryable, some not | Includes issuer-downtime clusters |
| `CHECKOUT_ABANDONMENT` | Sessions abandoned at varied stages | Some anonymous — hence non-addressable, which must be represented |
| `OVERDUE_RECEIVABLE` | Invoices past due at varied ages and amounts | Includes partial payments, credit notes, disputes |
| `SUBSCRIPTION_RENEWAL_FAILURE` | Renewal charges failing on mandates | Includes expiring mandates |
| `MANDATE_HEALTH_RISK` | Mandates with dated near-certain failure | The only proactive class; deliberately a small population (`12 § 2`) |

### 5.2 Difficulty and scarcity

| Property | Statement |
|---|---|
| Total `ENRV`-positive demand exceeds capacity | By construction, so `G6` and shadow prices are exercised |
| Value distribution is skewed | A few large opportunities, many small — so value-ranking and ENRV-ranking genuinely disagree |
| Value and recoverability are **negatively correlated in part of the population** | The regime where "chase the biggest" is wrong. Without this, baseline `B4 VALUE_RANK` would be near-optimal and the differentiator would be invisible |
| Natural recovery is concentrated among high-value customers in `HIGH_NATURAL` | The regime where over-contacting is most expensive |

**Stated as a deliberate construction, not discovered:** the correlation structure in the third row is
invented to make the product's thesis testable. That is legitimate — the thesis must be *falsifiable*
in the dataset — but it also means the benchmark measures whether REVIVE handles this structure, **not
whether the structure exists in reality**. That limitation is repeated in
[21-evaluation.md](21-evaluation.md) § 9.

### 5.3 Signal hygiene faults

Injected deliberately (`DS-6`):

| Fault | Expected handling |
|---|---|
| Exact duplicate signals | Deduplicated (`DM-5`) |
| Out-of-order arrival (`occurred_at` < prior `received_at`) | Tolerated (`RR-NFR-045`) |
| Late success signals arriving after a decision | Reservation released, `DEFERRED_STOPPED`, no execution (`SR-02`) |
| Success timestamp preceding the action | Attribution `NATURAL` (`RR-FUNC-071`) |
| Malformed payloads | Quarantined, not crashed (`DM-6`) |
| Unknown enum values | Quarantined |
| Hostile free text in `reason_text` (prompt-injection strings) | Escaped; never alters control flow (`RR-NFR-063`) |
| Contradictory signals for one opportunity | Latest-wins with both audited |
| Signal storms in one cycle | Degradation detection (`RR-FUNC-009`) |

---

## 6. Adversarial injections

Each row exists to make a specific safety claim falsifiable.

| Case | Targets |
|---|---|
| Customer at their contact cap | `G3`, `SR-04` |
| Consent revoked mid-run | `G1`, `SR-08` |
| Opportunity whose window closes mid-cycle | `SR-01`, horizon shortening |
| Recovery arriving between reservation and execution | Pre-execution stopping (`RR-FUNC-051`) — **the highest-value single test in the package** |
| Approval left unattended past expiry | `SR-06` (silence ≠ consent) |
| Approval approved-with-modification | `RR-FUNC-066` re-gating |
| Duplicate action proposals across cycles | Idempotency, `G9` |
| Adapter timeout | `RECONCILING`, reconciliation, `unresolved_reconciliation_count` |
| Adapter timeout that later resolves to success | No double effect |
| Provider outage window | Degradation, deferral not stopping |
| Risk flag landing mid-run | `SR-09` |
| Write-off / refund / credit note | `SR-10` |
| Scripted merchant `HALT` and resume | `SR-11`, `RR-GUARD-024`, `RR-NFR-046` |
| Zero-`ENRV` population segment | `SR-07` economic exhaustion |
| Opportunity where every action has negative uplift | Correct answer is `NO_ACTION` |
| Incentive request exceeding the ceiling | `G5` downward clamp |
| Retry with a mismatched amount | `G12` |
| Two opportunities for the same customer competing | `contact_allowance` as a resource |
| Near-tie `ENRV` values | Deterministic tie-break (`10 § 7`) |
| Extreme value outlier | `G7` approval threshold, `G12` sanity |
| Prompt-injection payload in merchant notes | `RR-NFR-063` |
| Planted PII sentinels | `RR-NFR-053` canary scan |

| # | Rule |
|---|---|
| DS-14 | Every row above is present in the `HOSTILE` profile and a named subset in `BALANCED` |
| DS-15 | Each has a corresponding named test ([30](30-test-plan.md)) |
| DS-16 | Adversarial cases are **included in the reported metrics**, not excluded as noise (`P-15`) |

DS-16 is the anti-theatre rule for the dataset: a benchmark that quietly drops its hard cases is
reporting a different experiment than the one it describes.

---

## 7. Privacy canaries

Sentinel values are planted in fields where real PII would live — a sentinel "phone number", a sentinel
"email", a sentinel card-like string, a sentinel name — and a scan asserts none appears in any audit
event, log, metric label, prompt, cache entry, or artefact (`RR-NFR-053`, `RR-NFR-062`).

The canaries are the reason the never-log list is *enforced* rather than *intended*. On synthetic data
there is no real PII to leak, so without canaries the enforcement path would never execute and its
failure would be invisible.

---

## 8. How this dataset could be rigged

The threat model, stated plainly, with the defence for each.

### 8.1 Rigging vectors

| Vector | How it would flatter REVIVE | Defence |
|---|---|---|
| Set natural recovery near zero | Every intervention looks causal; uplift ≈ conversion | `HIGH_NATURAL` profile is mandatory; `p(i,∅)` distribution is published in the artefact |
| Make actions always help (no negative uplift) | `ENRV` filtering never needs to work | `OR-4` requires harmful cases |
| Make timing generous | Horizon choice becomes irrelevant | `OR-6` requires post-`H` recoveries |
| Make capacity abundant | Allocation is trivial; any policy ties | `SCARCE` mandatory; `ABUNDANT` reported anyway |
| Correlate value with recoverability positively | `B4 VALUE_RANK` looks bad for the wrong reason | Both correlation regimes present; § 5.2 |
| Make cause signals fully informative | Diagnosis becomes a lookup; the LLM looks essential | `DS-9`; `UNCLASSIFIED` rate is a reported metric |
| Tune parameters after seeing results | Classic overfitting | § 8.3 |
| Report only favourable seeds | Selection bias | All seeds in the declared set reported; `RR-BENCH-004` |
| Exclude adversarial cases from metrics | Hides failures | `DS-16` |
| Choose `ε`, `λ_f`, `N` after measurement | Fits the thresholds to the answer | § 8.3 |

### 8.2 The unflattering-configuration requirement

`RR-BENCH-009`: the report must include at least one configuration where REVIVE's advantage over the
best baseline is **small or absent**, and must say so in the headline rather than a footnote.
`ABUNDANT` is expected to be that configuration, because when nothing is scarce there is little for an
allocator to do.

A report in which the product wins everywhere is either a rigged benchmark or an untested one.

### 8.3 Parameter freeze

| Rule | Statement |
|---|---|
| All generator parameters, `ε`, `λ_f`, `N`, horizons, and window lengths are frozen **before** any comparative measurement | `RR-BENCH-008` |
| The frozen set is hashed into `config_hash` and published | Post-hoc changes are detectable |
| If a parameter must change after measurement, **all** prior results are discarded and re-run | Not amended, not annotated — re-run |
| Tuning is permitted only on a **separate seed set** disjoint from the reported set | And the split is declared |

The third row is the one that costs something, which is why it is written down before the first
measurement rather than after an inconvenient result.

---

## 9. Artefacts

| Artefact | Contents |
|---|---|
| `dataset/manifest.json` | seed, generator version, profile, parameter set, counts by class, `dataset_hash` |
| `dataset/domain/*` | DOMAIN-layer records (`17 § 2`) |
| `dataset/signals.ndjson` | The ordered signal stream, including injected faults |
| `dataset/oracle/*` | **Separate partition**, not loaded by the engine process |
| `dataset/injections.json` | Every adversarial case with the requirement ID it targets |
| `dataset/canaries.json` | Sentinel values, for the scan |
| `dataset/distributions.json` | Published summary of the generated distributions, including the `p(i,∅)` distribution |

`distributions.json` exists so a reviewer can judge whether the dataset was easy without reading the
generator. Publishing the natural-recovery distribution is the single most useful disclosure in the
package, because it bounds how much of any reported recovery could have happened anyway.

---

## 10. What this dataset is not

| Not | Statement |
|---|---|
| Real data | No real merchant, customer, or transaction |
| Validated against real data | No comparison to real payment behaviour has been performed. `UNVERIFIED` |
| A distributional claim | The shapes are invented; they are not estimates of anything |
| Evidence about Razorpay's rails | It reproduces REVIVE's own interfaces, not any provider's behaviour |
| Sufficient for a production go/no-go | `HACKATHON-SCOPE` |

---

## 11. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-BENCH-001` batch population | § 5 |
| `RR-BENCH-004` all seeds reported | § 8.1 |
| `RR-BENCH-005` oracle isolation | § 4.2, `DS-11`/`DS-12` |
| `RR-BENCH-006` `NO_ACTION` correctness cases | `OR-5` |
| `RR-BENCH-008` parameter freeze | § 8.3 |
| `RR-BENCH-009` unflattering configuration | § 8.2 |
| `RR-BENCH-010` synthetic disclosure | Header, § 10 |
| `RR-NFR-020`…`022` determinism | § 2.1 |
| `RR-NFR-045` signal hygiene | § 5.3 |
| `RR-NFR-053`, `RR-NFR-062` canaries | § 7 |
| `RR-NFR-063` injection resistance | § 5.3 |
| `CF-7` natural-recovery dominance testable | § 4.3 |
| `13 § 6`, `14 § 6` gate and stopping coverage | § 6 |

---

## 12. Open items

| Item | Label |
|---|---|
| All distribution shapes and parameter values | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION`; invented when chosen |
| Whether the oracle should model competitor/self-serve recovery channels | `FUTURE / NOT IMPLEMENTED` |
| Whether to model customer-initiated contact (inbound) | `PROPOSED` no for this build; noted as a fidelity gap |
| Realistic reason-code frequencies | `UNVERIFIED`; would require real data |
| Whether `MANDATE_HEALTH_RISK` population size is defensible | `UNKNOWN`; kept deliberately small |
| Seed count for the reported set | `PROPOSED` per `RR-NFR-033` (20 seeds within 60 minutes) |
| Tuning-seed / reporting-seed split | `PROPOSED`; must be declared before measurement |
