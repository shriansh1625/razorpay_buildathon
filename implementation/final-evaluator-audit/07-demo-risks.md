# 07 · Demo risks

Five-minute path as specified in local `README.md` and `implementation/track3-readiness/track3-checklist.md`.

---

## The path (intended)

Control Room → active opportunity → Analyze → Lab → Guardrails → Execution → Receipt → Audit → batch on Control Room → Benchmark → 20×6×5=600 → ABUNDANT×REVIVE×seed 14.

That path **works on the local uncommitted UI** with server seed 14 (verified in prior QA: Analyze, blocked, system, palette, matrix cell).

---

## Ways the live five minutes die

| ID | Sev | Failure | Why |
|---|---|---|---|
| D-1 | P0 | Judge clones GitHub instead of watching a laptop | Product not on origin; no video |
| D-2 | P0 | Pitch video missing | Official process artefact |
| D-3 | P1 | **Run Recovery** clicked | `POST /api/recovery-run` rebuilds world; wow opportunity and ₹19,799.25 vanish; README says do not click the primary CTA |
| D-4 | P1 | Server not restarted | Seed ≠ 14; blocked/success IDs in the checklist rot |
| D-5 | P1 | Matrix cell below the fold | ABUNDANT×REVIVE×14 needs palette / `S.bmCell` — a judge clicking the visible cells never reaches the scripted cell |
| D-6 | P1 | Analyze cinematic + clock | ~4.6s overlay; if reduced-motion, skip; if they talk over it, it feels fake |
| D-7 | P1 | Guided demo is NEXT×10 | Official product should feel operate-not-slideshow; director still exists and is prominent in the rail |
| D-8 | P2 | “Decision receipt” clipped in subnav | Ambiguous labels under time pressure |
| D-9 | P2 | Phone / 1024 viewport | First viewport contract fails; laptop demo assumed |
| D-10 | P2 | `docs/26-demo-script.md` still PLACEHOLDER | If someone reads spec instead of README, they think numbers are missing |

---

## Script vs product language

| Spec demo script (`docs/26`) | Product README |
|---|---|
| Placeholders, M-16=0 required before demo | Concrete seed-14 rupees |
| “Revenue Command Center (Screen 1)” | Control Room |
| Synthetic-data banners on every screen | SANDBOX · seed N (better) |

Two scripts is a demo risk: the founder might read the wrong one.

---

## What must be true before walking on stage

1. `origin/main` **is** the PAYVANTA product (not this audit’s job to push).
2. Pitch video recorded from the **frozen seed-14** UI, without Run Recovery.
3. Palette items “Restore demo seed 14” and “ABUNDANT × REVIVE · seed 14” rehearsed as recovery if the world is blown.
4. One spoken sentence: sandbox batch vs official 600 cells vs same engine.
5. One spoken sentence: LLM off; intelligence is constrained optimization + rules + gates.

Until (1) and (2), the demo can be perfect on a laptop and still lose.
