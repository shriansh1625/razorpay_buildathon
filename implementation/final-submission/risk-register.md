# Final competition risk register

Status language: **open** until the operator publishes. This document does **not** declare submission ready.

## P0 — could invalidate submission

| ID | Risk | Evidence | Mitigation | State |
|---|---|---|---|---|
| P0-1 | **Public clone is not PAYVANTA** | `origin/main` = `25dc006`; `revive/product/` untracked; origin README still “REVIVE / M10 / 170 tests” | Commit + push product sources when operator asks | **OPEN** |
| P0-2 | **GitHub not demonstrably public** | Logged-out fetch of `https://github.com/shriansh1625/razorpay_buildathon` → **404** | Make the repo public before judging | **OPEN** |
| P0-3 | Official evidence not in Git | `artefacts/` gitignored | Documented mount path; do not regenerate | Accepted strategy — clone without mount still must run Control Room |
| P0-4 | Accidental official write / rerun | Operator error | Product HTTP 405; this task did not rerun | Closed in product; process remains |

Until P0-1 and P0-2 close, **do not claim the public repository shows PAYVANTA.**

## P1 — could materially reduce score

| ID | Risk | Mitigation | State |
|---|---|---|---|
| P1-1 | Spec docs still describe two LLM agents as if built | Status banner on `docs/08`; `docs/why-ai.md`; overview `intelligence.llm_used=false` | **Closing in this change** |
| P1-2 | Sandbox money read as official M-10 | README, UI SANDBOX, integrity flags | Mitigated in product; must be spoken in pitch |
| P1-3 | No pitch **video file** in the workspace | Script packet in `submission/pitch/` | **OPEN** (recording is out of band) |
| P1-4 | Demo seed destroyed by Run Recovery | Script forbids the button | Process |
| P1-5 | Draft policy pack on sandbox vs sealed official pack | Honest: sandbox demonstration vs sealed experiment | Documented, not silently “fixed” |

## P2 — presentation

| ID | Risk | State |
|---|---|---|
| P2-1 | Origin landing page still REVIVE until commit | Follows P0-1 |
| P2-2 | Large untracked QA screenshot trees | Optional; `docs/assets/control-room.png` is the README hero |
| P2-3 | Viewport polish remaining | No redesign this pass |

## P3 — optional

| ID | Note |
|---|---|
| P3-1 | Live Razorpay adapters |
| P3-2 | Implementing C-05 LLM residual / C-10 copy — **not** for frozen benchmark |
