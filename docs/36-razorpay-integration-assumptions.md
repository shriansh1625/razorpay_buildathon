# 36 · Razorpay Integration Assumptions

Every claim about a Razorpay product, API, behaviour, or constraint in this package is
**`UNVERIFIED`**. This document collects them in one place so they can be checked against
official documentation before any code depends on them.

> **Rule (`RR-BENCH-010`).** No Razorpay endpoint, parameter, field name, error code, or product
> behaviour is asserted as fact anywhere in this package. Everything below is an assumption
> needed to design the system. If an assumption is wrong, the adapter layer absorbs the
> difference — the decision core does not change.

---

## 1. Assumed Razorpay products

| Product | Assumed capability | Used for | Status |
|---|---|---|---|
| **Payments API** | Create payment; query payment status; receive webhooks for payment events | SEE: detecting payment failures; ACT: retry payments | `UNVERIFIED` |
| **Orders API** | Create order; query order status | SEE: detecting checkout abandonment | `UNVERIFIED` |
| **Subscriptions API** | Manage subscriptions; query subscription status; detect mandate failures | SEE: detecting subscription failures | `UNVERIFIED` |
| **Invoices API** | Create invoice; query invoice status; detect overdue invoices | SEE: detecting receivable overdue | `UNVERIFIED` |
| **Payment Links API** | Generate payment links for recovery | ACT: send payment links | `UNVERIFIED` |
| **Smart Collect** | Virtual account–based collections | ACT: alternative payment method | `UNVERIFIED` |

---

## 2. Assumed API behaviours

### 2.1 Payment retry

| Assumption | Status | Impact if wrong |
|---|---|---|
| A failed payment can be retried via API with the original order and instrument | `UNVERIFIED` | Retry action becomes infeasible; alternative actions still available |
| Retry returns a synchronous success/failure or an async webhook | `UNVERIFIED` | Adapter handles both; timeout path covers async |
| Idempotency key is supported on payment creation | `UNVERIFIED` | Critical for `RR-FUNC-060`; if not supported, adapter must simulate |
| Failed payment webhook includes a machine-readable `error_code` | `UNVERIFIED` | If absent, diagnosis falls back to `UNCLASSIFIED` |

### 2.2 Payment status

| Assumption | Status | Impact if wrong |
|---|---|---|
| Payment status can be queried by `payment_id` | `UNVERIFIED` | Outcome observation must use webhooks only |
| Statuses include at least: `created`, `authorized`, `captured`, `failed`, `refunded` | `UNVERIFIED` | State mapping may need adjustment |
| `captured` means funds settled to the merchant | `UNVERIFIED` | Recovery confirmation may require additional settlement check |

### 2.3 Webhooks

| Assumption | Status | Impact if wrong |
|---|---|---|
| Razorpay sends webhooks for payment success, failure, and refund | `UNVERIFIED` | SEE phase relies on webhooks; polling is the fallback |
| Webhooks are delivered at least once (may duplicate) | `UNVERIFIED` | Deduplication already required by `RR-FUNC-003` |
| Webhooks carry a signature for verification | `UNVERIFIED` | If absent, adapter cannot verify authenticity |
| Webhook payload includes `payment_id`, `order_id`, `amount`, `status`, `error_code` | `UNVERIFIED` | Missing fields degrade context; diagnosis may be less precise |

### 2.4 Subscriptions and mandates

| Assumption | Status | Impact if wrong |
|---|---|---|
| Subscription API exposes mandate status | `UNVERIFIED` | Mandate retry action may be infeasible |
| Failed mandate charge triggers a webhook | `UNVERIFIED` | Detection relies on webhook or polling |
| A mandate can be retried after failure | `UNVERIFIED` | If not, retry action is removed from the candidate set |

### 2.5 Invoices

| Assumption | Status | Impact if wrong |
|---|---|---|
| Invoice API returns `status` including `issued`, `paid`, `partially_paid`, `expired` | `UNVERIFIED` | Ageing bucket computation may need adjustment |
| Invoice `due_date` is available | `UNVERIFIED` | If absent, overdue detection uses a default window |
| Payment against an invoice is linkable to the invoice | `UNVERIFIED` | If not linkable, outcome observation is impaired |

---

## 3. Assumed error codes

The following error codes are assumed to exist for the purpose of designing the diagnosis
taxonomy. They are `UNVERIFIED`.

| Assumed code | Meaning | Diagnosis mapping |
|---|---|---|
| `BAD_REQUEST_ERROR` | Malformed request | Not a revenue-loss event |
| `GATEWAY_ERROR` | Payment gateway timeout or error | `NETWORK_TIMEOUT` cause |
| `AUTHENTICATION_ERROR` | Card authentication failed | `AUTHENTICATION_FAILURE` cause |
| `NETWORK_ERROR` | Network connectivity issue | `NETWORK_TIMEOUT` cause |
| `INSUFFICIENT_BALANCE` | Card/account has insufficient funds | `INSUFFICIENT_FUNDS` cause |
| `CARD_EXPIRED` | Card past expiry date | `INSTRUMENT_EXPIRED` cause |
| `CARD_DECLINED` | Issuer declined the transaction | `ISSUER_DECLINE` cause |
| `DO_NOT_HONOUR` | Generic issuer decline | `ISSUER_DECLINE` cause (generic) |
| `INTERNATIONAL_TRANSACTION_NOT_ALLOWED` | Cross-border restriction | `REGULATORY_BLOCK` cause |

If Razorpay's actual error codes differ, the taxonomy mapping table in C-05 must be updated.
The mapping is a lookup table, so the change is localised.

---

## 4. Assumed communication channels

| Channel | Assumed mechanism | Status |
|---|---|---|
| SMS | Third-party SMS provider (not Razorpay) | `UNVERIFIED` — provider TBD |
| Email | Standard SMTP or transactional email service | `UNVERIFIED` — provider TBD |
| WhatsApp | WhatsApp Business API (third-party) | `UNVERIFIED` — provider TBD |
| Payment Link | Razorpay Payment Links API | `UNVERIFIED` |
| Voice | Third-party telephony provider | `UNVERIFIED` — provider TBD; MAY tier |

In the hackathon build, all channels use simulated adapters. No real messages are sent.

---

## 5. Assumed consent model

| Assumption | Status |
|---|---|
| Razorpay collects customer consent for transactional communications at checkout | `UNVERIFIED` |
| Consent scope includes payment failure notifications and recovery communications | `UNVERIFIED` |
| Consent is queryable via API | `UNVERIFIED` |
| TRAI DND registry compliance is the merchant's responsibility | `UNVERIFIED` |
| RBI notification requirements for mandate debits are handled by Razorpay | `UNVERIFIED` |

In the hackathon build, consent is generated synthetically. Consent semantics are simplified.

---

## 6. Assumed rate limits

| Resource | Assumed limit | Status |
|---|---|---|
| API rate limit | 25 requests/second per API key | `UNVERIFIED` — default assumption |
| Webhook delivery rate | No assumed limit | `UNVERIFIED` |
| Payment Link generation | No assumed limit | `UNVERIFIED` |

If real rate limits are lower, the adapter layer throttles. The decision core does not change.

---

## 7. How wrong assumptions are absorbed

The adapter layer ([18-api-contracts.md](18-api-contracts.md), C-18) is designed to absorb API
differences:

| If this assumption is wrong… | The adapter… | The decision core… |
|---|---|---|
| Error codes differ | Maps actual codes to the REVIVE taxonomy | Unchanged |
| API parameters differ | Transforms request format | Unchanged |
| Webhooks are not available | Polls for status changes | Unchanged |
| Idempotency is not supported | Implements client-side dedup | Unchanged |
| A product doesn't exist | Marks the action as infeasible | Removes it from candidates |
| Rate limits are lower | Throttles and defers | Sees `DEFER` from the adapter |

This is the purpose of the adapter interface: **the decision core makes choices; the adapter
translates those choices into provider-specific API calls.** A wrong assumption about Razorpay
changes the adapter, not the allocator.

---

## 8. Verification checklist (for implementation phase)

Before any code calls a real Razorpay endpoint:

- [ ] Verify each assumed product exists and is accessible with the available API key
- [ ] Verify each assumed error code against official documentation
- [ ] Verify webhook event types and payload schema
- [ ] Verify idempotency key support
- [ ] Verify rate limits
- [ ] Verify consent and notification requirements
- [ ] Record each verification in this document with date, source URL, and verified status
- [ ] Promote verified assumptions from `UNVERIFIED` to `KNOWN` with citation
- [ ] Record any assumption that was wrong, with the actual behaviour and the adapter change made
