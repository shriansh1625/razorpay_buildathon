# 02 · Human judge + buildathon reviewer

Perspectives: **first-time judge** and **buildathon reviewer**. Official contract only.

---

## First-time judge (30 seconds / 2 minutes / 5 minutes)

### What would impress me

- The Control Room looks like a revenue command center, not a notebook dump.
- One number: incremental net recovery, with incr − cost = net.
- One opportunity that is AUTHORIZED → SUCCEEDED → MEASURED, with a rupee amount.
- One blocked path with NO EXECUTION.
- A ribbon that says 600 / 600 official cells, BENCHMARK_VALID.

If I am sitting in front of the **local** uncommitted UI, those are all present on seed 14.

### What would make me skeptical

- Every rupee is labelled SANDBOX. I cannot see a merchant.
- **Analyze** is a 5-second cinematic over state that already exists. Nothing new is computed.
- **Run Recovery** is the most prominent system CTA, and the team’s own notes say *do not click it* in the five-minute path.
- Product name **PAYVANTA**, CLI **`revive`**, policy **REVIVE**, GitHub folder **razorpay_buildathon**. I do not know which one to search.
- Docs/README still contains a status table: “Source code: **None. Not started.** Benchmark results: **None.**”

### What would make me reject

- I opened the **public GitHub** and got 404, or I got “REVIVE / M10 / 170 tests” with no product.
- There is no 5-minute pitch, so I never see the Control Room.
- I clone, follow README, and `revive control-room` does not exist.
- I cannot tell Track 03 from “we built a benchmark harness.”

### What I need to verify

| Claim I heard | What I click / clone |
|---|---|
| It recovers money | Control Room hero + one receipt with measured net |
| It is an agent | One end-to-end loop, not a slideshow |
| It is safe | Blocked opportunity, reason, no adapter call |
| It is proven | Benchmark Lab, one official cell, checksum |
| It is submittable | Public URL, video, architecture doc that match the running app |

---

## Buildathon reviewer (process officer)

Official page: *“show your work (a public repo, a 5 minute pitch video, the architecture)”*.

| Artefact | Local workspace | `origin/main` | Risk |
|---|---|---|---|
| Public repo | Remote configured | Unauthenticated GitHub **404** | **P0** |
| Architecture | `docs/07-system-architecture.md` exists | Present on origin, but still “spec” voice | **P1** if it contradicts the product |
| 5-minute pitch | **Not found** | **Not found** | **P0** |
| Working product in repo | `revive/product/` **untracked** | **Absent** | **P0** |

This reviewer does not need to dislike the engine. They can fail the packet for missing process artefacts.

---

## Issues

| ID | Sev | Issue |
|---|---|---|
| HJ-1 | P0 | Public GitHub 404 / not demonstrably public |
| HJ-2 | P0 | Origin README is the old engine, not PAYVANTA |
| HJ-3 | P0 | Pitch video missing |
| HJ-4 | P1 | Dual-name fog (PAYVANTA / REVIVE / revive) on first screen and in git |
| HJ-5 | P1 | `docs/README.md` status table still says source code none, benchmark none |
| HJ-6 | P1 | Guided demo + “don’t click Run Recovery” makes the product feel like a scripted exhibit |
| HJ-7 | P2 | Analyze cinematic can read as theatre over a finished decision |
| HJ-8 | P2 | 40+ spec files; judge reading order is longer than the pitch |

---

## Would I score Track 03 *if I had the local UI*?

Yes, on **detect / intervene / execute / measure / escalate / stop / audit**, as a **synthetic bounded agent**.

I would still mark down **AI meaningfulness** (see `04`) and **real-world execution** (see `06`) unless the pitch names those limits in the first minute.
