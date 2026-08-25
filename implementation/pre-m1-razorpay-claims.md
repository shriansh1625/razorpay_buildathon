# Pre-M1 Razorpay Claims Audit

**Rule:** No unverified claim may be treated as production integration (`36`, IC-04).

---

## 1. Document-level posture

| Document | Claim type | Classification |
|----------|------------|----------------|
| `36-razorpay-integration-assumptions.md` | All Razorpay products/APIs | **UNVERIFIED** (explicit) |
| `README` C-8 | No Razorpay endpoint asserted as fact | **DOCUMENTED** |
| `00` constraints | No verified Razorpay integration | **KNOWN** |
| `07` §9 | Real payment/comms providers absent | **DOCUMENTED** |
| `32` IC-04 | Never invent APIs | **DOCUMENTED** |

---

## 2. Claim inventory (from `36` and cross-refs)

### Products assumed (all UNVERIFIED)

| Claim | Classification | Implementation treatment |
|-------|----------------|--------------------------|
| Payments API — create/query/webhooks | UNVERIFIED | SIMULATED adapter |
| Orders API — checkout abandonment | UNVERIFIED | SIMULATED |
| Subscriptions API — mandate failures | UNVERIFIED | SIMULATED |
| Invoices API — overdue receivables | UNVERIFIED | SIMULATED |
| Payment Links API — recovery links | UNVERIFIED | SIMULATED |
| Smart Collect — alt collections | UNVERIFIED | SIMULATED |

### Behaviors assumed (all UNVERIFIED)

| Claim | Classification |
|-------|----------------|
| Payment retry via API | UNVERIFIED |
| Idempotency keys on payment create | UNVERIFIED |
| Webhook error_code machine-readable | UNVERIFIED |
| Status enum captured/refunded/etc. | UNVERIFIED |
| Mandate retry after failure | UNVERIFIED |
| Invoice due_date and status enum | UNVERIFIED |

### Error codes in taxonomy (`36` §3)

| Claim | Classification |
|-------|----------------|
| INSUFFICIENT_BALANCE, CARD_EXPIRED, etc. | UNVERIFIED — **design-time mapping table only** |

### Channels (`36` §4)

| Claim | Classification |
|-------|----------------|
| Razorpay Payment Links for recovery | UNVERIFIED |
| SMS/Email/WhatsApp/Voice providers | UNVERIFIED — third-party |
| Hackathon: all channels simulated | **DOCUMENTED** |

### Consent / regulatory (`36` §5)

| Claim | Classification |
|-------|----------------|
| Razorpay collects consent at checkout | UNVERIFIED |
| TRAI/RBI handled by Razorpay | UNVERIFIED |
| Hackathon: synthetic consent | **DOCUMENTED** |

### Rate limits (`36` §6)

| Claim | Classification |
|-------|----------------|
| 25 req/s API limit | UNVERIFIED PROPOSED |

---

## 3. Implied production capabilities — search result

| Phrasing in docs | Found? | Classification |
|------------------|--------|----------------|
| "production integration implemented" | **No** | — |
| "production-ready" | Explicitly **denied** (`02` §9, `04` PP-4) | DOCUMENTED |
| Real Razorpay endpoints in code | **No code exists** | N/A |
| "Verified integration" | **No** — only UNVERIFIED + adapter | DOCUMENTED |
| Track 03 uses Razorpay data | **No** — synthetic only | DOCUMENTED |
| `03` real Razorpay test-mode | T3 conditional after verification | FUTURE |

---

## 4. VERIFIED claims

**None** at rank-2 (official Razorpay docs cited as verified). Entire package is pre-implementation.

---

## 5. SIMULATED (hackathon build)

| Surface | Label |
|---------|-------|
| All payment effects | SIMULATED |
| All messaging/voice | SIMULATED |
| Webhook ingestion | SIMULATED / cycle-based signals |
| Merchant data | SYNTHETIC |

---

## 6. PROPOSED (future adapter shape)

| Item | Notes |
|------|-------|
| Adapter interface in `18` | PROPOSED contract |
| Error code mapping table | PROPOSED until verified |
| Rate limit 25 rps | PROPOSED assumption |

---

## 7. Submission language requirements

Must include on every artefact/slide:

> Results are from a reproducible **synthetic** evaluation environment. Razorpay integration is **not verified**. No production payment rails are used.

(`21` §8, `RR-BENCH-010`)

---

## 8. Verdict

**No undocumented Razorpay production claims in spec.** Safe to implement with **SIMULATED-only adapters** in P0. **No blocker for M1.**
