# M4 Checkpoint — Revenue Sentinel

**Milestone:** M4 — Revenue Sentinel (SEE)  
**Date:** 2026-08-21  
**Status:** COMPLETE

---

## Purpose

Detect observable revenue-at-risk and emit structured `RevenueOpportunity` records. The Sentinel does **not** choose recovery actions, compute ENRV, or allocate effort.

---

## Implemented capabilities

| Capability | Location | Requirement |
|------------|----------|-------------|
| Signal ingest + quarantine | `revive/recovery/sentinel/signals.py` | `RR-FUNC-005` |
| Opportunity detection | `revive/recovery/sentinel/detect.py` | `RR-FUNC-001` |
| Class-specific `V(i)` | `revive/recovery/sentinel/valuation.py` | `RR-FUNC-002` |
| Natural-key dedupe | `revive/recovery/sentinel/identity.py` | `RR-FUNC-003`, docs/12 §6 |
| Recovery windows | `SentinelConfig` + detect | `RR-FUNC-004` |
| Addressability | `revive/recovery/sentinel/addressability.py` | `RR-FUNC-007` |
| Receivable ageing buckets | `AgeingBucket` | `RR-FUNC-008` |
| Observable degradation flag | `revive/recovery/sentinel/degradation.py` | `RR-FUNC-006` |
| Mandate near-expiry | detect path | docs/12 `MANDATE_HEALTH_RISK` |

Entry point: `detect(ObservableWorldView, now_micros, config) -> SentinelResult`

---

## Detection rules

| Class (M1 enum) | Observable evidence | Natural key |
|-----------------|---------------------|-------------|
| `PAYMENT_FAILURE` | Failed payment attempt on an order | `(customer, order, billing_period)` |
| `CHECKOUT_ABANDONMENT` | Abandoned session at CART or later with determinable cart value | `(customer_or_session, cart_fingerprint=session_id)` |
| `SUBSCRIPTION_FAILURE` | Subscription `PAST_DUE` / charge due | `(subscription_id, cycle_number)` |
| `RECEIVABLE_OVERDUE` | Invoice due at `now` with outstanding balance | `(invoice_id)` |
| `MANDATE_HEALTH` | Mandate `EXPIRING`/`REVOKED` or expiry inside billing window | `(mandate_id, next_charge_date)` |

Not detected: LANDING-only sessions, events with `timestamp > now`, paid invoices, successful settlements.

---

## Opportunity schema

`DetectedOpportunity` mirrors docs/17 fields used at detection: id, merchant, customer, risk_class, natural_key, value_at_risk_paise, original_value_paise, continuation_value_paise, addressable, non_addressable_reason, state (`DETECTED` or `NOT_ADDRESSABLE`), timestamps, attempt_seq, ageing_bucket, degradation_flag, structured evidence, detector_version.

`value_at_risk_paise` is recoverable `V(i)`, not a claim of money that will be recovered.

---

## Observable inputs

Consumes `ObservableWorldView` (M2 observation interface). **Ignores** generator `opportunities` and `degradation_windows` so hidden cohort labels cannot drive detection.

---

## Oracle boundary

- Sentinel lives under `revive.recovery` (already in decision-path import guard).
- No import of `revive.simulation.oracle`, `_partition`, or `latent`.
- Opportunity `to_dict()` scanned for hidden keys.
- Detection identical when hidden degradation windows / generator opportunities are injected into the view.

---

## Deduplication

Repeated failures on the same order update `attempt_seq` (LK-2). Duplicate `dedupe_hash` signals are ingested once. Cross-class overlap records a `secondary_class` on the first natural key rather than a second `V`.

---

## Temporal guarantees

Virtual time only. At `T`, only events with timestamps `≤ T` are used. Mandate expiry in the next billing window is treated as an **observable scheduled** future event (docs/12 §2.1), not oracle lookahead.

---

## Tests

`tests/recovery/` — detection, valuation, dedupe, quarantine, addressability, degradation, no lookahead, oracle isolation, determinism, generator recall.

**Result:** 82 passed (full suite)

---

## Known limitations

- Checkout cart fingerprint = `session_id` (generator has no separate fingerprint field).
- Mandate `V(i)` uses `max_amount_paise` when next-cycle charge is not a separate field.
- `continuation_factor = 0` (ADR-007).
- Full C-01 audit-event persistence deferred to M17.
- Recall/precision ≥ 0.99 vs generator is exercised on the tiny fixture, not a frozen benchmark batch.

---

## Assumptions

- Recovery windows: OQ-03 provisional (checkout 48h, payment/subscription 14d, receivable 90d).
- Degradation: rolling 90-minute window, ≥3 attempts, failure rate ≥ 0.6 — observable heuristic, not hidden cohorts.
- Risk class names remain M1 enums (`SUBSCRIPTION_FAILURE`, `RECEIVABLE_OVERDUE`, `MANDATE_HEALTH`).

---

## Deviations

None vs frozen `docs/` semantics. Generator `natural_key` format is **not** reused; Sentinel uses docs/12 §6 keys.

---

## Deferred

Diagnosis (M5), candidates (M6), ENRV (M7), allocator (M9), gates (M10).

---

## Next milestone

**M5 — Context + diagnosis** — NOT AUTHORIZED.


> No recovery, ENRV, or benchmark claims are made from M4 detection output.
