# 06 · Trust risks

Five skeptic sentences. Evidence, not vibes.

---

## 1. “This is a sophisticated mockup.”

**Could they say it? Yes.**

Why it lands:

- All customers, payments, mandates, invoices are **generated** (`generate_shared_world`).
- Execution: `revive/execution/adapters/simulated.py` → `resolve_outcome(...)` on the **oracle partition**.
- No Razorpay test-mode key, webhook, or captured payment.
- Control Room is a local stdlib HTTP server over one in-memory `ProductSession`.
- Analyze / guided demo are UX over **already computed** traces.

Why a fair evaluator should **not** stop there:

- Money is not CSS. Incremental net is summed paise from measurement records.
- Authorization is not a green pill glued on: `test_no_execution_without_authorization`.
- The 600-cell artefact tree is a real experiment output (locally), not a Figma table.
- Idempotency keys and gate traces are engine objects.

**Precise verdict:** the **decision and control plane is real**; the **clearing house is a mock**. If the pitch says “we recover Razorpay payments,” that is a disqualifying overclaim. If the pitch says “bounded recovery OS on a synthetic merchant book, evaluated in 600 official cells,” the mockup attack weakens.

| ID | Sev |
|---|---|
| TR-1 | P1 | Simulated rails + oracle outcomes |
| TR-2 | P0 | Overclaim of live merchant / Razorpay (not currently in README; still a pitch risk) |

---

## 2. “The benchmark is interesting, but I cannot connect it to the product.”

**Yes.** Full argument in `05-track3.md`. Short form:

- DRAFT pack vs SEALED pack.
- 18×34 demo world vs 20×6×5 official design.
- `artefacts/` gitignored.
- UI insists they are different datasets (true) without a durable “same engine” artefact in the **public** repo.

| ID | Sev |
|---|---|
| TR-3 | P1 | Policy-pack split |
| TR-4 | P0 | Official cells not in git |

---

## 3. “There is an agent somewhere, but the intelligence is deterministic hardcoding.”

**Yes.** Full argument in `04-ai-evaluator.md`.

| ID | Sev |
|---|---|
| TR-5 | P1 | Docs/08 LLM agents vs `llm_used=False` |
| TR-6 | P1 | Copy Composer specified, not implemented |

---

## 4. “It executes, but I cannot tell whether execution is safe.”

**Partially yes.**

Visible and real:

- Six guardrail families in UI; 12 gates in engine.
- AUTHORIZED vs BLOCKED with reasons (seed 14 blocked opp: Approval Denied, NOT_EXECUTED).
- Stopping rules evaluated in `authorize.py` via `evaluate_stopping_rules`.
- Official writes return 405.

Unclear to a skeptic:

- Adapters cannot mis-fire against a bank; they cannot *prove* they would not.
- G7 “human review” is a state, not a reviewer.
- Demo pack is DRAFT; sealed pack is what official cells used.
- Product ledger does not show `prev_hash` / content hash (`revive/audit/journal.py` does).
- Idempotent re-click is not part of the five-minute script.

| ID | Sev |
|---|---|
| TR-7 | P1 | Safety proven only in simulation |
| TR-8 | P1 | Hash chain not on the Audit Ledger screen |
| TR-9 | P2 | Repeat-execute / idempotency not in the default demo |

---

## 5. Hidden assumptions / fake-looking metrics

| Risk | Finding | Sev |
|---|---|---|
| Hardcoded hero rupees in UI | Not in `app.js`; projected from snapshot | — |
| Hardcoded wow IDs | QA scripts and checklist only, not the renderer | P3 |
| Fake live activity | Pulse is last-cycle counts; `ar-live` CSS pulse is decorative | P2 |
| Credentials | No `.env` in tree; `.env` gitignored; no API keys in `revive/product/` | — |
| User-agent branching | Not found | — |
| `docs/README.md` “no source / no benchmark” | Directly contradicts reality | P1 |
| Charter “no implementation exists” | Same | P1 |

---

## Reliability / security (narrow)

- Stdlib server, bind 127.0.0.1 by default — fine for demo, not a product deployment.
- No auth on `/api/*` — acceptable for localhost; **P1** if they deploy the port publicly during judging.
- Official tree classified; invalidated `artefacts/benchmark/official/` is not used as product proof (good).
- Playwright QA scripts assume `:8765` already up.

No secrets found in this audit pass. Do not treat that as a full secret scan.
