# 03 · Fintech CTO

Perspective: would I trust this as a recovery operating system, even as a prototype?

---

## What would impress me

- Incremental net recovery as the objective, with natural recovery treated as not a win.
- Portfolio allocation under resource caps, not per-event blasting.
- Integer paise; sealed PolicyPack on the official path; idempotency keys on execution.
- Structural rule: no adapter call without `AuthorizationState.AUTHORIZED` (`tests/product/test_control_room.py`).
- 12 ordered gates + SR-01…SR-11 in code, not a slide.
- Official evaluation is a frozen 20 × 6 × 5 design with `BENCHMARK_VALID`, not a cherry-picked screenshot.
- Honest sandbox labelling. Most fintech demos lie here.

## What would make me skeptical

- **Sandbox session uses `default_draft_policy_pack()`** (`revive/product/session.py`). System / Evidence shows `pol_m1_draft · DRAFT`. Official cells use `official_sealed_policy_pack()`. I am watching policy A and being asked to trust experiment B.
- **Adapters are simulated.** `revive/execution/adapters/simulated.py` resolves outcomes via the hidden oracle. There is no Payments / Subscriptions / Invoices adapter.
- **`docs/36-razorpay-integration-assumptions.md`** marks every Razorpay product assumption `UNVERIFIED`. Correct engineering — fatal if the pitch implies Razorpay recovery is live.
- Product **audit ledger** timestamps are `cyc_0003+04` style sequence labels. Hash chain exists in `revive/audit/journal.py` and is **not** what the UI ledger shows.
- Learning (`docs/35-learning-engine.md`) has no `revive/**/learn*.py` module. The loop in architecture diagrams still says LEARN.
- Control Room **Run Recovery** rebuilds the entire world on a new seed. That is a demo generator, not an operator action on a merchant book.

## What would make me reject

- Claiming production merchant money, Razorpay integration, or live mandates.
- Shipping DRAFT policy as if it were the sealed experiment.
- A public repo that does not contain the product I was pitched.
- Metrics that cannot be regenerated from seed + pack + engine.

## What I need to verify

1. Same `config_hash` on the sealed pack and the official manifest.
2. One blocked opportunity: authorization state ≠ AUTHORIZED, `execution is None`.
3. Repeat the same authorised action: second effect does not duplicate (idempotency). Not re-run in this audit.
4. M-10 on ABUNDANT × REVIVE is read from `official-cloud-final/`, not hardcoded in JS.
5. No secret, key, or PAN in git (none found; `.env` gitignored; no `.env` file present).

---

## Issues

| ID | Sev | Issue |
|---|---|---|
| CTO-1 | P1 | Demo world ≠ official policy pack (DRAFT vs SEALED) |
| CTO-2 | P1 | Execution boundary is an oracle, not a payment rail |
| CTO-3 | P1 | Product audit UI is a pipeline projection, not the hash-chained journal |
| CTO-4 | P1 | LEARN phase specified, not present as a product module |
| CTO-5 | P2 | `docs/00-project-charter.md` still says “Specification. No implementation exists.” |
| CTO-6 | P2 | Open blockers file still dated M0 / 2026-08-21 |
| CTO-7 | P3 | No encryption-at-rest; acceptable only because data is synthetic (docs already say this) |

---

## CTO one-liner

This is a **serious decision engine** demonstrated on a **toy clearing house**. I will hire the engine thinking if the submission packet is real. I will not hire a dashboard over a simulator if GitHub still says M10 and the video does not exist.
