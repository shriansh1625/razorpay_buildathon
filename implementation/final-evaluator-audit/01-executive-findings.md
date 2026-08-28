# 01 · Executive findings

**Role.** Hostile but fair Razorpay technical evaluator.  
**Date.** 2026-08-28.  
**Contract.** [Official Buildathon page](https://razorpay.com/buildathon/) only. No invented scorecards.

**Official process:** pick a track → build something real → show a **public repo**, a **5-minute pitch video**, and the **architecture**. If it has signal, panel.

**Official Track 03 bar:** an agent that **detects revenue at risk**, **determines the right intervention**, and **executes a bounded recovery workflow**, and that **shows measured money recovered across a batch**, with **compliant escalation**, **stopping rules**, and an **audit trail**.

**This audit did not** modify code, commit, push, or rerun the official benchmark.

---

## Verdict

Locally, PAYVANTA is a real recovery **engine** with a real (sandbox) **product surface**. That is not the same as a **submittable Track 03 package**.

A skeptical evaluator cloning what is currently on `origin/main` would not see PAYVANTA. They would see **REVIVE — Revenue Recovery Autopilot**, status **M10 Authorization Gates**, 170 tests, no Control Room, no `/api/product/overview`, and no official 600-cell tree in git.

**That is the primary way an otherwise excellent submission still loses.**

---

## Answers to the five critical questions

| Question | Answer |
|---|---|
| Could a skeptic call this a sophisticated mockup? | **Yes, reasonably — of the rails, not of the decision core.** Execution hits a simulated adapter + hidden outcome oracle. Money is integer paise computed by the engine, but no Razorpay rail is involved. See `06-trust-risks.md`. |
| Could a skeptic fail to connect the 600-cell benchmark to the product they just saw? | **Yes.** Sandbox uses `default_draft_policy_pack()` (DRAFT). Official cells use the sealed pack. Populations differ. `artefacts/` is gitignored. The UI honestly says they are not the same dataset — and then asks the judge to believe “same engine.” See `05-track3.md`. |
| Could a skeptic say the agent is mostly deterministic hardcoding? | **Yes, and the code agrees.** Diagnosis is `rank_causes` rules. `allow_llm=False`. Official `llm_mode=LLM_OFF`. Copy Composer (docs C-10) is not implemented. See `04-ai-evaluator.md`. |
| Could a skeptic say they cannot tell whether execution is safe? | **Partially.** Gates, authorization, and “no execution without AUTHORIZED” are real and tested. Safety is proven **inside a synthetic world**. Human review is a gate outcome, not a human. See `06-trust-risks.md`. |
| Could an evaluator understand the system without founders present? | **Not from `origin/main`.** Locally, yes *if* they start the uncommitted Control Room and ignore contradictory docs. See `08-submission-risks.md`. |

---

## P0 — could lose or fail the process bar

| ID | Finding | Evidence |
|---|---|---|
| **P0-1** | **Public repository does not present PAYVANTA.** Unauthenticated fetch of `https://github.com/shriansh1625/razorpay_buildathon` returned **404**. `gh` is not authenticated here, so visibility cannot be proven public. Official process requires a **public** repo. |
| **P0-2** | **`origin/main` is a different product.** HEAD `25dc006` README: “REVIVE — Revenue Recovery Autopilot / M10 Authorization Gates complete.” No `revive/product/`. No Control Room CLI. `revive/product/` is **untracked** locally. |
| **P0-3** | **Official evidence cannot travel with the repo.** `.gitignore` line 11: `artefacts/`. `git ls-files artefacts` → **0 files**. Benchmark Lab has nothing to verify on a clean clone. |
| **P0-4** | **No 5-minute pitch video** in the workspace (no `.mp4` / `.mov` / `.webm` / `.mkv`). Official process names the video as a submission artefact. |
| **P0-5** | **Stated reproduce path is false on origin.** Local README: `revive control-room` → `:8765`. Origin CLI has no `control-room` subcommand. A judge following the *current local* README after cloning origin gets a missing command. |

---

## What is actually strong (do not over-correct)

These are real, and they are why the project can still win **if P0 is fixed**:

- Track 03 loop is implemented in engine code: detect → diagnose → candidates → allocate → 12 gates → authorize → simulated execute → measure.
- Batch measurement exists on the sandbox Control Room (seed 14: incremental net ₹19,799.25 from engine paise, not a pasted headline).
- Authorization is structural: `test_no_execution_without_authorization`.
- Stopping rules SR-01…SR-11 exist in `revive/policy/stopping.py`.
- Audit journal is hash-chained in `revive/audit/journal.py`; product ledger is a projection.
- Official 600-cell tree exists **locally** and verifies; product layer is read-only toward it.
- Honesty about sandbox vs official is better than most demos — it is also the source of the “cannot connect” attack.

---

## How a 5-minute panel actually fails

Not because the allocator is weak.

Because:

1. The GitHub link 404s or opens an M10 engine README.
2. There is no pitch video.
3. The first-time judge cannot tell **PAYVANTA** from **REVIVE** from **`revive`**.
4. Someone asks “where is the AI?” and the honest answer is “LLM is off; diagnosis is rules.”
5. Someone clicks **Run Recovery** during the live demo and seed 14 disappears.

---

## Files in this audit

| File | Audience |
|---|---|
| `02-human-judge.md` | First-time judge + buildathon reviewer |
| `03-fintech-cto.md` | Fintech CTO |
| `04-ai-evaluator.md` | Staff AI engineer + AI evaluator |
| `05-track3.md` | Clause-by-clause against the public Track 03 bar |
| `06-trust-risks.md` | Mockup / safety / benchmark-disconnect |
| `07-demo-risks.md` | Five-minute path failure modes |
| `08-submission-risks.md` | Public repo, video, architecture, reproducibility |
| `09-priority-fixes.md` | What to do after this audit (not done here) |

**Stop.** No code was changed for this audit.
