# 12 · Revenue Leakage Model

Before REVIVE can allocate effort, it must define precisely what "revenue at risk" means, how much is
at risk, and whether anything can be done about it. This document is the domain model underneath
everything else.

---

## 1. Definition

> **A revenue opportunity is a specific, identifiable sum of money the merchant expected to receive,
> has not received, and which has not yet become permanently unrecoverable.**

Four clauses, each doing work:

| Clause | Excludes |
|---|---|
| *specific, identifiable sum* | Vague notions of "lost sales", market share, or unrealised demand |
| *expected to receive* | Speculative revenue, upsell potential, hypothetical conversions from never-started checkouts |
| *has not received* | Anything already settled, including late settlements |
| *not yet permanently unrecoverable* | Written-off, refunded, charged-back-and-lost, statute-barred, or customer-deceased cases |

If any clause fails, no opportunity is created. This is the first filter, and it is deliberately strict:
an inflated opportunity book makes every downstream metric look better while making the product worse.

---

## 2. Risk classes

Five classes, each with its own detection signals, valuation rule, horizon, and feasible action set.
The first three map directly onto the Track 03 brief's named examples; the other two are the same
economic phenomenon at a different point in the lifecycle.

| Class | What leaked | Track 03 mapping |
|---|---|---|
| `PAYMENT_FAILURE` | A payment attempt on an existing order/invoice failed | "payment failures" |
| `CHECKOUT_ABANDONMENT` | A checkout with a determinable cart value was started and not completed | "checkout abandonment" |
| `OVERDUE_RECEIVABLE` | An issued invoice is past its due date | "overdue receivables" |
| `SUBSCRIPTION_RENEWAL_FAILURE` | A recurring charge failed; the subscription is at risk of involuntary lapse | Same economics as payment failure, longer horizon, larger `V` |
| `MANDATE_HEALTH_RISK` | A mandate/instrument will fail *next* cycle (expiring card, revoked or expiring mandate) | Pre-failure leakage; the only **proactive** class |

### 2.1 Why `MANDATE_HEALTH_RISK` is included

It is the only class where the money has not yet failed. Including it is justified because the
economics are identical — a definite expected sum with a definite date and a bounded action set — and
because it is where uplift is largest: fixing an instrument *before* the charge avoids the failure
entirely rather than recovering from it.

It is also the class most likely to be misused, so it is bounded hard: an opportunity is created only
when the failure is **near-certain and dated** (expiry within the next billing window, mandate
already revoked or expiring). It is never created on a *probabilistic* prediction that a payment
"might" fail. That would turn the opportunity book into a speculation list.

### 2.2 Class comparison

| Property | `PAYMENT_FAILURE` | `CHECKOUT_ABANDONMENT` | `OVERDUE_RECEIVABLE` | `SUBSCRIPTION_RENEWAL_FAILURE` | `MANDATE_HEALTH_RISK` |
|---|---|---|---|---|---|
| Money already failed | yes | no charge attempted | yes (due, unpaid) | yes | **no** |
| Natural recovery common? | **yes, very** | moderate | **yes, very** | yes | n/a (certain failure if unfixed) |
| Typical `V` | order amount | cart amount | invoice balance | expected subscription LTV slice | next-cycle charge |
| Horizon `H` | short (hours–days) | very short (hours) | long (days–weeks) | medium | until next billing date |
| Retry meaningful? | **yes** | no (no charge to retry) | no | **yes** | no |
| Communication meaningful? | yes | yes | **yes, primary** | yes | **yes, primary** |
| Incentive meaningful? | rarely | **sometimes** | as extension/instalment | rarely | no |
| Dominant failure mode of naive systems | over-retrying | blasting everyone | dunning spam | churning the customer with dunning | ignoring it entirely |

The "natural recovery common?" row is the reason this product exists. In three of five classes the
money frequently arrives with no intervention at all, which means any system measuring gross recovery
rate is largely measuring the customer's own behaviour.

---

## 3. Signals

### 3.1 Signal types

Signals are the raw inputs. They are `UNVERIFIED` with respect to real Razorpay payload shapes; the
ingestion layer defines its **own** internal schema and an adapter maps to it
([36-razorpay-integration-assumptions.md](36-razorpay-integration-assumptions.md)).

| Signal type | Carries | Feeds classes |
|---|---|---|
| `PAYMENT_ATTEMPT_FAILED` | amount, method, reason string, reason code, instrument ref, order ref, attempt seq | `PAYMENT_FAILURE`, `SUBSCRIPTION_RENEWAL_FAILURE` |
| `PAYMENT_ATTEMPT_SUCCEEDED` | amount, method, order ref | Closes opportunities; feeds outcomes |
| `CHECKOUT_SESSION_ABANDONED` | cart value, stage reached, method selected (if any), session duration | `CHECKOUT_ABANDONMENT` |
| `INVOICE_ISSUED` / `INVOICE_DUE` / `INVOICE_PAID` | balance, due date, terms | `OVERDUE_RECEIVABLE` |
| `SUBSCRIPTION_CHARGE_FAILED` | amount, cycle, subscription ref | `SUBSCRIPTION_RENEWAL_FAILURE` |
| `MANDATE_STATE_CHANGED` | mandate state, expiry, limit | `MANDATE_HEALTH_RISK` |
| `INSTRUMENT_STATE_CHANGED` | expiry, block state | `MANDATE_HEALTH_RISK` |
| `REFUND_ISSUED` / `DISPUTE_OPENED` / `WRITE_OFF` | amount | Reduces or closes `V`; may make an opportunity non-addressable |
| `CUSTOMER_CONSENT_CHANGED` | channel consents | Affects eligibility, not detection |

### 3.2 Signal hygiene

| Rule | Requirement |
|---|---|
| Validate against schema; quarantine on failure with a reason | `RR-FUNC-005` |
| Never fabricate a default for a missing material field | `RR-FUNC-005` |
| Tolerate out-of-order and late arrival without corrupting state | `RR-NFR-045` |
| Idempotent ingestion: the same signal delivered twice creates one effect | `RR-FUNC-004` |
| The reason **string** is untrusted data, never an instruction | `RR-NFR-063` |

### 3.3 Late and out-of-order signals

A `PAYMENT_ATTEMPT_SUCCEEDED` arriving after REVIVE already decided to act is the common and important
case. Rules:

1. It closes the opportunity immediately and sets a stopping condition (`SR-02`).
2. If an action is already reserved but not executed, the reservation is released and the decision
   becomes `DEFERRED_STOPPED` — **not** executed and then retracted.
3. If the action already executed, the outcome is recorded and attribution examines timing. If the
   success timestamp precedes the action timestamp, the recovery is classified `NATURAL`, never
   `ATTRIBUTED`. Ambiguity always resolves against REVIVE (`RR-FUNC-071`).

---

## 4. Valuation — computing `V(i)`

`V(i)` is the **recoverable** amount in paise, not the headline amount. Per class:

| Class | `V(i)` |
|---|---|
| `PAYMENT_FAILURE` | Amount of the failed attempt, less any portion already settled by another attempt |
| `CHECKOUT_ABANDONMENT` | Cart value at abandonment, less items now unavailable or price-changed. If cart value is not determinable, the opportunity is **not addressable** — no guessing |
| `OVERDUE_RECEIVABLE` | Outstanding balance = invoiced − paid − credited − written off − disputed portion |
| `SUBSCRIPTION_RENEWAL_FAILURE` | Failed cycle amount, **plus** an optional `continuation_value` component |
| `MANDATE_HEALTH_RISK` | Next scheduled charge amount |

### 4.1 The `continuation_value` question

For a failed subscription renewal, the true economic loss is not one cycle — it is the remaining
lifetime of a customer who may lapse involuntarily. Including that makes the class dominate the
allocation; excluding it understates it.

**Resolution (`ADR-007`):**

- `V(i)` = failed cycle amount + `continuation_factor × cycle_amount`, where `continuation_factor` is
  an **explicit policy parameter**, default `0` (`ASSUMPTION`).
- With the default `0`, REVIVE **understates** subscription value. That direction is deliberate:
  understating means the system is less likely to over-invest in this class on the strength of an
  invented LTV number.
- Any run with `continuation_factor > 0` must report it prominently, and the evaluation includes a
  sensitivity result at `0` and at least one positive value.

An LTV model is `FUTURE / NOT IMPLEMENTED`.

### 4.2 Valuation prohibitions

| Prohibition | Why |
|---|---|
| No LLM produces or adjusts `V(i)` | `RR-GUARD-020` |
| No estimated or inferred amounts | If the amount is not determinable from records, the opportunity is non-addressable |
| No inclusion of disputed portions | Recovering a disputed amount is not a recovery |
| No double counting across opportunities | § 6 identity rules |
| No inflation for "goodwill" or "brand value" | Not a determinable sum |

---

## 5. Addressability

`addressable = false` means REVIVE detected and valued the opportunity but will take **no action** on
it. It still appears in the book, still appears in reports, and is counted separately. Detection and
addressability are distinct so that the system cannot improve its own metrics by declining to see
things.

| Non-addressable because | Rule |
|---|---|
| Amount not determinable | § 4 |
| Already settled / refunded / written off | `RR-FUNC-007` |
| Disputed or charged back | Recovery attempts on disputes are out of scope (`OS-09`) |
| Recovery window already expired | `SR-01` |
| No consented channel and no non-contact action available | `RR-GUARD-001` |
| Customer flagged deceased, bankrupt, or under legal hold | Hard block, `RR-GUARD-008` |
| Risk block (fraud suspicion) | `RR-GUARD-008` — REVIVE does **not** adjudicate fraud, it defers to the flag (`OS-24`) |
| Test / internal / zero-amount records | Data hygiene |
| Explicit merchant suppression | Merchant authority |

**Reporting rule.** The non-addressable set is reported with its total value and reason breakdown.
A large non-addressable set is a finding about data quality or policy, not something to hide.

---

## 6. Identity and deduplication

The most common way a recovery system corrupts its own metrics is by counting one economic loss as
several opportunities — three failed attempts on one invoice becoming three recoveries.

### 6.1 The identity rule

> **One opportunity per distinct economic loss**, not per event.

The natural key per class:

| Class | Natural key |
|---|---|
| `PAYMENT_FAILURE` | `(customer, order_or_invoice_ref, billing_period)` |
| `CHECKOUT_ABANDONMENT` | `(customer_or_session_identity, cart_fingerprint)` within a coalescing window |
| `OVERDUE_RECEIVABLE` | `(invoice_ref)` |
| `SUBSCRIPTION_RENEWAL_FAILURE` | `(subscription_ref, cycle_number)` |
| `MANDATE_HEALTH_RISK` | `(mandate_ref, next_charge_date)` |

### 6.2 Consequences

- **Repeated failures update, never duplicate.** A second failed attempt on the same invoice
  increments `attempt_seq` on the existing opportunity.
- **Cart re-abandonment within the coalescing window updates** the same opportunity; a genuinely new
  cart creates a new one.
- **Cross-class overlap must be resolved.** A failed subscription charge that also becomes an overdue
  invoice is **one** opportunity, classified by the earliest-detected class, with the other class
  recorded as a secondary tag. A test asserts no `V` is counted twice across classes for the same
  underlying money.
- **A merged opportunity keeps its original id**, so the audit trail stays continuous.

### 6.3 Anti-inflation invariants

| # | Invariant |
|---|---|
| LK-1 | `Σ V(i)` over open opportunities never exceeds total genuinely outstanding money in the dataset |
| LK-2 | No two open opportunities share a natural key |
| LK-3 | Closing an opportunity is idempotent |
| LK-4 | `M-06 Gross Recovered` cannot exceed `Σ V(i)` over closed opportunities |
| LK-5 | Detected count is independent of how many actions were taken |

---

## 7. Ageing, windows, and urgency

| Concept | Definition |
|---|---|
| `first_detected_at` | When the opportunity was created (virtual clock) |
| `ageing_bucket` | Class-specific bands, e.g. receivables `0–7 / 8–30 / 31–60 / 60+` days past due |
| `recovery_window_expires_at` | The point after which recovery is treated as unrecoverable; class-specific, policy-pack parameter |
| `time_to_window_close` | A predictor feature and an urgency driver |
| `next_eligible_at` | Earliest cycle this opportunity may be acted on again (cooldown, `RR-GUARD-004`) |

### 7.1 How ageing enters the decision

Ageing does **not** get a hand-tuned priority boost. It enters through the model, in two places:

1. It is a predictor feature, so `p(i,a)` and `p(i,∅)` both change with age. Empirically-shaped
   expectation: natural recovery falls with age, which *raises* uplift even as `p(i,a)` falls.
2. A closing window compresses the horizon `H = min(H_class, window_close − now)`, which lowers
   `p(i,∅)` and mechanically raises urgency.

This is a design choice worth stating: a hand-tuned "escalate at day 30" rule would be simpler and is
what most dunning systems do, but it cannot be evaluated, cannot produce a shadow price, and cannot
tell the merchant *why* day 30 is the right day. Letting ageing act through the model means the answer
is measurable.

---

## 8. Cause taxonomy

A closed set. The Root Cause Analyst (C-05) may rank within it and may return `UNCLASSIFIED`. It may
never invent a code (`RR-FUNC-011`).

### 8.1 The taxonomy

| Group | Cause codes |
|---|---|
| **Instrument** | `CARD_EXPIRED`, `INSUFFICIENT_FUNDS`, `INSTRUMENT_BLOCKED`, `INSTRUMENT_INVALID` |
| **Mandate** | `MANDATE_REVOKED`, `MANDATE_EXPIRED`, `MANDATE_LIMIT_EXCEEDED`, `MANDATE_NOT_PRESENTED` |
| **Issuer / network** | `ISSUER_DECLINE_SOFT`, `ISSUER_DECLINE_HARD`, `ISSUER_DOWNTIME`, `ISSUER_RISK_DECLINE`, `DO_NOT_HONOUR_AMBIGUOUS` |
| **Authentication** | `AUTH_TIMEOUT`, `AUTH_ABANDONED_BY_CUSTOMER`, `SECOND_FACTOR_NOT_COMPLETED`, `AUTH_SYSTEM_FAILURE` |
| **Technical** | `GATEWAY_TIMEOUT`, `GATEWAY_ERROR`, `METHOD_UNAVAILABLE`, `CONFIGURATION_ERROR` |
| **Checkout friction** | `PREFERRED_METHOD_NOT_OFFERED`, `CHECKOUT_STEP_FRICTION`, `PRICE_OR_FEE_HESITATION`, `SESSION_INTERRUPTED` |
| **Receivable-side** | `INVOICE_NOT_RECEIVED`, `BUYER_APPROVAL_PENDING`, `QUERY_OR_DISPUTE_RAISED`, `BUYER_CASHFLOW_CONSTRAINT`, `OVERSIGHT_OR_FORGOTTEN` |
| **Terminal** | `CUSTOMER_DECLINED_TO_PAY`, `ORDER_NO_LONGER_WANTED` |
| **Unknown** | `UNCLASSIFIED` |

### 8.2 The honesty rule about causes

Most of these codes are **not observable**. A gateway reason code of `DO_NOT_HONOUR` is compatible
with insufficient funds, an issuer risk decision, a blocked card, and issuer downtime. `OVERSIGHT_OR_FORGOTTEN`
is never observable at all — it is an inference about a person's mental state.

Therefore:

| Rule | Requirement |
|---|---|
| The output is a **ranked set of candidate causes**, never a single asserted cause | `RR-FUNC-010` |
| Each carries a confidence **band**, never a fabricated percentage | `RR-FUNC-012` |
| Each carries **evidence references** to actual rows | `RR-FUNC-012` |
| `UNCLASSIFIED` is a legitimate, non-penalised output routing to a conservative default candidate set | `RR-FUNC-016` |
| No screen or report renders a candidate cause as a determined fact | `RR-UI-002`, `PP-4` |

`UNCLASSIFIED` being non-penalised matters: if the system were rewarded for classifying, it would
classify confidently and wrongly, and every downstream price would inherit that error.

### 8.3 Cause → actionability

This mapping is the primary reason diagnosis exists. It is a deterministic rule table (C-06), not a
model output.

| Cause | Retry helps? | Instrument update? | Reminder? | Incentive? | Human? |
|---|---|---|---|---|---|
| `CARD_EXPIRED` | **no** (will fail again) | **yes, primary** | supporting | no | no |
| `INSUFFICIENT_FUNDS` | **yes, with delay** (salary-cycle timing) | maybe | supporting | maybe (extension) | no |
| `ISSUER_DOWNTIME` | **yes, after the window closes** | no | no | no | no |
| `ISSUER_DECLINE_HARD` | **no** | yes (alternate method) | supporting | no | no |
| `DO_NOT_HONOUR_AMBIGUOUS` | maybe once | maybe | supporting | no | if high value |
| `MANDATE_REVOKED` | **no** | **yes, re-authorise** | supporting | no | no |
| `AUTH_ABANDONED_BY_CUSTOMER` | no | no | **yes, link resend** | maybe | no |
| `PREFERRED_METHOD_NOT_OFFERED` | no | no | yes, with alternate method | no | no |
| `PRICE_OR_FEE_HESITATION` | no | no | maybe | **yes, the main case for `A10`** | no |
| `OVERSIGHT_OR_FORGOTTEN` | no | no | **yes, primary** | no | no |
| `BUYER_APPROVAL_PENDING` | no | no | yes, low-frequency | no | maybe |
| `BUYER_CASHFLOW_CONSTRAINT` | no | no | yes | **yes, extension/instalment** | if high value |
| `QUERY_OR_DISPUTE_RAISED` | no | no | **no** | no | **yes, route to human** |
| `CUSTOMER_DECLINED_TO_PAY` | no | no | **no** | no | no — stop (`SR-08`) |
| `UNCLASSIFIED` | conservative single retry only if class permits | maybe | conservative reminder | **no** | if high value |

Note the two rows where the correct action is *nothing or a human*: `QUERY_OR_DISPUTE_RAISED` and
`CUSTOMER_DECLINED_TO_PAY`. A system that treats every open balance as a dunning target will keep
messaging both, and both are cases where messaging destroys value.

Note also that `ISSUER_DOWNTIME` prescribes **waiting** — the intervention is a delay, and delay is
cheap. This is where the degradation monitor (C-03) pays for itself: without it, a retry-happy system
burns its retry slots against a temporarily broken issuer.

---

## 9. What is not revenue leakage

Stated so the opportunity book cannot expand into adjacent problems (`AG-12`).

| Not leakage | Reason |
|---|---|
| Customers who never started a checkout | No determinable expected sum |
| Price optimisation / discount strategy | Not a recovery problem (`OS-27`) |
| Voluntary churn (deliberate cancellation) | The customer decided; recovery would be win-back, a different product |
| Fraud losses | Adjudicated elsewhere; REVIVE defers to the flag (`OS-24`) |
| Chargebacks and disputes | Dispute management is a separate discipline (`OS-09`) |
| Refunds the merchant chose to issue | Not leakage |
| Tax, fee, or FX differences | Accounting, not recovery (`OS-28`) |
| Under-billing / pricing errors | Revenue assurance, a different product |
| Failed payouts to vendors | Outbound, not receivable |
| Cross-sell and upsell shortfalls | Growth, not recovery |

---

## 10. Requirement mapping

| Requirement | Where satisfied |
|---|---|
| `RR-FUNC-001` detect payment failures | § 2, § 3 |
| `RR-FUNC-002` detect checkout abandonment | § 2, § 3 |
| `RR-FUNC-003` detect overdue receivables | § 2, § 3 |
| `RR-FUNC-004` deduplicate to one per economic loss | § 6 |
| `RR-FUNC-005` signal validation and quarantine | § 3.2 |
| `RR-FUNC-006` degradation detection | § 8.3 (`ISSUER_DOWNTIME` row), C-03 |
| `RR-FUNC-007` value at risk computation | § 4 |
| `RR-FUNC-008` addressability | § 5 |
| `RR-FUNC-009` ageing and windows | § 7 |
| `RR-FUNC-010`…`012` cause taxonomy, ranking, evidence | § 8 |
| `RR-FUNC-016` `UNCLASSIFIED` handling | § 8.2 |
| `RR-NFR-045` out-of-order signals | § 3.3 |

---

## 11. Open items

| Item | Label |
|---|---|
| Real Razorpay signal shapes, event names, and reason-code vocabulary | `UNVERIFIED` — the single largest verification debt ([36](36-razorpay-integration-assumptions.md)) |
| Whether real reason codes map cleanly onto this taxonomy | `UNKNOWN`; the adapter absorbs the mismatch and unmapped codes become `UNCLASSIFIED` |
| Recovery-window lengths per class | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION` |
| Cart-abandonment coalescing window | `PROPOSED`; affects the dedupe rule in § 6 |
| `continuation_factor` default | `ASSUMPTION` `0`; understates subscription value by design (§ 4.1) |
| Whether `MANDATE_HEALTH_RISK` should be in T1 or T2 | `PROPOSED` T1 detection, T2 action, because it is the highest-uplift class and the easiest to over-extend |
| Ageing bucket boundaries | `PROPOSED`; must be frozen before measurement so they cannot be tuned to results |
