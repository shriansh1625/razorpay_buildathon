# 05 · Track 03 — public bar only

Source: [https://razorpay.com/buildathon/](https://razorpay.com/buildathon/) (fetched 2026-08-28).

> Build an agent that detects revenue at risk, determines the right intervention, and executes a bounded recovery workflow: from payment failures and checkout abandonment to overdue receivables.

> The bar: Don’t just identify the problem. Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail.

No other scoring dimensions are treated as official. “Meaningful AI” is discussed in `04` as panel risk, not as a hidden rubric.

---

## Clause matrix (engine + local product)

| Clause | Engine | Local UI | Origin/main | Sev if missing at submit |
|---|---|---|---|---|
| Detect revenue at risk | `revive/recovery/sentinel/` | System pulse DETECTED; pipeline 01 | Engine yes, UI no | P0 for *shown* bar |
| Determine the right intervention | valuations + allocator | Recovery Lab, PAYVANTA recommends | Engine yes, UI no | P0 for *shown* bar |
| Bounded recovery workflow | authorize → adapter | Execution + guardrails | Engine yes, UI no | P0 for *shown* bar |
| Payment failures / checkout / receivables / subscription | four `RiskClass` values | explorer filters | Engine yes | OK |
| Measured money recovered **across a batch** | measurement + waterfall | Control Room hero + pulse | Engine metrics exist; product hero not shipped | **P0 if they cannot *show* a batch** |
| Compliant escalation | `AuthorizationState` + G7 | Blocked path, families | Engine yes | P1 if UI absent |
| Stopping rules | SR-01…SR-11 | Guardrails table | Engine yes | P1 if UI absent |
| Audit trail | hash-chained journal | ledger projection + receipts | Engine yes | P1 if UI absent |

**Important:** Track 03 says **show**. An unpushed Control Room does not count as shown.

---

## Batch evidence — two batches, easy to confuse

| Batch | What it is | Where | Policy |
|---|---|---|---|
| Sandbox Control Room | 18 customers, 34 opportunities, 4 cycles, seed 14 | Uncommitted UI | **DRAFT** pack |
| Official experiment | 20 seeds × 6 profiles × 5 policies = 600 cells | Local `artefacts/benchmark/official-cloud-final/` (gitignored) | **SEALED** pack |

A reviewer can accept both **if** the pitch says: sandbox shows the loop on one world; official cells evaluate the engine. A reviewer can reject the connection **if** they think ₹19,799.25 is an official result or that ABUNDANT×REVIVE is the Control Room.

Local UI does **not** hardcode ₹19,799.25; it projects `hero.incremental_net_recovery` from the session. Checklist files *do* quote that figure as demo lore (`implementation/track3-readiness/track3-checklist.md`).

---

## Critical question 2 — “benchmark interesting, cannot connect to the product”

**Yes.** Exact reasons:

1. **Different policy objects:** `build_demo_session` → `default_draft_policy_pack()` vs official `official_sealed_policy_pack()`.
2. **Different worlds:** demo generator `customer_count=18`, `opportunity_count=34`, profile BALANCED vs 600-cell factorial design.
3. **Evidence not in git:** clone has zero cells.
4. **UI tells the truth too well:** “This receipt is not an official benchmark cell.” Without a one-sentence bridge (“same engine binary / same loop”), the judge files them as unrelated projects.
5. **M-10 vs Control Room net:** matrix cells are incremental-vs-B0 experiment metrics; Control Room net is a single synthetic session. Mixing them in speech is a P0 honesty fail; *separating* them without a bridge is a P1 comprehension fail.
6. **Origin README** never mentions PAYVANTA, Control Room, or 600 official cells as a product proof surface.

---

## Escalation / stopping / audit — caveats (not absences)

- Escalation: BLOCKED / REVIEW / AUTHORIZED are real states. “Human review” does not wait on a human in the demo.
- Stopping: all 11 rules are coded. The UI may show many **Clear** rows on seed 14; a skeptic may say they never saw a stop *fire*. Need a demo opportunity where a named SR fires, not only G7 approval denied.
- Audit: engine chain vs UI projection (`CTO-3`). Still an audit trail of consequential stages.

---

## Issues

| ID | Sev | Issue |
|---|---|---|
| T3-1 | P0 | Track bar is “show”; origin cannot show the product |
| T3-2 | P1 | Sandbox batch and official batch are easy to treat as one number |
| T3-3 | P1 | DRAFT pack in the only interactive demo |
| T3-4 | P1 | Stopping rules implemented; seed-14 wow path is authorize/succeed, not stop-fire |
| T3-5 | P2 | `docs/01-track-alignment.md` still talks in spec-future tense and “demo beat” placeholders |
| T3-6 | P2 | `docs/26-demo-script.md` still has `[PLACEHOLDER — INSERT FROM BENCHMARK]` |

---

## Fit vs example directions

Building a **general recovery OS** covering all four leak classes is inside the track. Not building Hinglish voice is not a miss. Claiming voice would be a miss.
