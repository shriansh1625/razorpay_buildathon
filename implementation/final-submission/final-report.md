# P9 war-room report — 2026-08-28

**Do not read this as SUBMISSION READY.** P0 public-repo parity is open.

## PUBLIC REPO STATUS

**FAIL for a stranger.** `origin/main` = `25dc006`. Logged-out GitHub URL **404**. Origin README is still REVIVE / M10 / 170 tests. `revive/product/` is **untracked**.

## CLEAN CLONE STATUS

Fresh venv on origin clone: `ModuleNotFoundError: No module named 'revive.product'`. CLI has no `control-room`.

Working tree **does** run `revive control-room` (local, uncommitted product).

## AI CREDIBILITY

**Pass (honest).** No LLM in the binary. `llm_used=False`. Official `LLM_OFF`. Copy Composer not implemented. Spec vs ship: `docs/08` banner + `docs/why-ai.md`. Overview exposes `intelligence.llm_used=false`.

## TRACK 03 COVERAGE

Mapped in `docs/track3-evidence.md`: detect, determine, bounded execute, batch measure, escalation, stopping, audit.

## BATCH MEASUREMENT

Sandbox Control Room = this session. Official M-10 = frozen cells. Not conflated.

## ESCALATION / STOPPING / AUDIT

Engine + tests + UI. Prepared blocked opportunity for the pitch.

## BENCHMARK

600 / 120 / 20×6×5 / `BENCHMARK_VALID` / blocked=false when the tree is mounted. Not modified this task.

## SECURITY

POST/PUT/PATCH/DELETE `/api/benchmark/official*` → 405. Cell traversal rejected. Tests in `tests/product/test_submission_redteam.py`.

## BROWSER / RESPONSIVENESS

No redesign. Compact forensic hero already in place. Full viewport sweep not re-run this pass (P2).

## TESTS

Run `pytest tests/product -q` after these edits.

## README / ARCHITECTURE

PAYVANTA landing, Track 03 flow, mermaid, `docs/43-operating-architecture.md`.

## VIDEO

Script packet in `submission/pitch/`. **No video file.**

## SCREENSHOTS

`docs/assets/control-room.png` for README. Prior QA set under `implementation/ui-v3/`.

## ARTIFACT INTEGRITY

Must remain: `git diff -- artefacts/benchmark/official-cloud-final/` empty.

## REMAINING

| Sev | Item |
|---|---|
| **P0** | Commit+push PAYVANTA sources (operator) |
| **P0** | Make GitHub public |
| **P1** | Record 5-minute video |
| **P1** | Re-clone origin after publish and walk the UI |
| P2 | Viewport QA recapture |
| P3 | Live adapters / optional LLM residual |

Until P0 closes, the product you demonstrate is **not** the product a stranger can clone.
