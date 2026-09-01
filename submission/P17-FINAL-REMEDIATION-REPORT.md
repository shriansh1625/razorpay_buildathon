# P17 final remediation report

**Date:** 2026-08-28
**Mode:** implementation + verification. **No commit. No push.**
**HEAD (local and origin):** `c7a11ed`
**Working tree:** P16 honesty + P17 remaining fixes (uncommitted)

Official Track 03 source: https://razorpay.com/buildathon/

---

## What a stranger sees today (public origin)

GitHub `main` is still **P15** (`c7a11ed`).

- Repo description: `null`
- Topics: `[]`
- Origin `README.md` still sequences `AI DIAGNOSIS → ENRV`
- Origin `docs/why-ai.md` still puts AI diagnosis before economics
- Origin `overview.track03` is seven bare `true` booleans
- Origin `docs/08` banner says “no live model call” while Groq is on that commit

**LOCAL ≠ ORIGIN.** Public parity is **not** achieved until the owner commits and pushes this working tree.

---

## Remediation matrix

| Finding | Source | Verified? | Severity | This pass | Test / re-verification |
|---|---|---|---|---|---|
| Public architecture AI → ENRV | origin README / why-ai | Yes | P0 public | Local diagrams now show overlay **after** `run_traced_cycle`; no Groq→ENRV edge | Docs grep; remaining: origin unchanged |
| docs/08 two LLM agents / Copy Composer / three agents | docs/08 body | Yes | P1 | SHIPPED vs HISTORICAL tables; C-05/C-10 labeled historical | File read |
| track03 self-certifying booleans | origin overview.py | Yes | P1 | `capability_declaration` + `status=implemented` + references | `test_overview.py` |
| observed_evidence ungrounded | schemas.py | Yes | P1 | Ungrounded claims downgraded to inference | `test_intelligence.py` |
| Realized net looks like gross | workspace KPIs | Yes | P1 | At risk / natural / incremental / cost / net + equation | Code + API |
| Analyze implies click-autonomy | app.js | Yes | P1 | **Inspect opportunity**; copy that the cycle already ran | UI strings |
| Official tree not in git | .gitignore | Yes | P1 | README mount language + screenshot caption | README |
| GitHub metadata empty | GitHub API | Yes | P1 | Documented; **not applied** (no `gh` auth) | `GITHUB-METADATA.md` |
| Pitch checklist “say no LLM” | VIDEO-RECORDING-CHECKLIST | Yes | P1 | Groq proposal vs engine decision | File |
| Public / local diverge | git | Yes | P0 until push | **Not closed** — STOP before commit | `git status` |
| AI is not economic decision-maker | code | Yes | Honesty | Kept. Not wired into ENRV | Import search + tests |
| Execution simulated | adapters | Yes | Honesty | Kept. CTA says sandbox / not live payments | UI copy |
| Sandbox vs benchmark confusion | UI/README | Yes | P1 | SANDBOX BATCH ≠ official M-10 | overview `financial.kind` |
| First-view density | JUDGE PREFERENCE | Partial | P2 | CTA + empty-runs copy only; no redesign | Code |
| Wire Groq to ENRV / live Razorpay / 600 cells in git | hostile prefs | Rejected | — | Would lie or unfreeze the experiment | — |
| Fabricate natural > 0 | demo suspicion | Rejected | — | Added “NATURAL RECOVERY IS ZERO IN THIS SEEDED SCENARIO.” | hero.natural_note |

---

## Fixes

### Architecture (actual call graph)

Money path: `run_traced_cycle`
Overlay: `POST /api/opportunity/{id}/ai-diagnosis` **after** engine state
No arrow from Groq into ENRV, allocation, policy, authorization, or adapters.

Canonical statement in README and `docs/why-ai.md`.

### AI evidence

`classify_observed_claims`: only grounded `k=v` / distinctive values stay **Observed**. Invented strings become **Inferred**. Invalid cause/action still reject the proposal (fallback).

### UI copy

- Inspect opportunity (not Analyze)
- Run sandbox recovery (not live payments)
- Engine selected (not “PAYVANTA recommends” as if it were the model)
- SANDBOX BATCH RESULT · not official M-10
- Workspace money hierarchy + equation
- Empty recent-runs explains demo cycles already ran at load
- AI proposal vs PAYVANTA ECONOMIC DECISION
- System page: role + execution authority NONE

### Track 03 API

Each capability: `status=implemented`, `implementation_reference`, `test_reference`, `ui_reference` / `api_reference` where real. `not_independent_proof: true`.

---

## Tests

```
pytest tests/product -q
58 passed
node --check revive/product/ui/app.js   # exit 0
git diff --check                        # clean after whitespace fix
```

New / extended: grounded observation, fabricated observation, malformed payload, unknown cause, diagnose-time ungrounded claims, overview `SANDBOX_BATCH` + capability `status`.

Existing: AI vs engine selection (engine wins), blocked opp stays `NOT_EXECUTED`, no intelligence→execution imports, key non-leak, fallback / 401 path.

---

## API verification (local working tree)

In-process server, `GROQ_API_KEY` **unset**:

| Endpoint | Result |
|---|---|
| GET `/api/product/overview` | PAYVANTA; `track03.kind=capability_declaration`; `financial.kind=SANDBOX_BATCH`; `not_official_m10=true`; `ai.execution_authority=none` |
| GET `/api/intelligence/status` | DETERMINISTIC_FALLBACK; role `diagnosis_and_proposal` |
| GET `/api/audit` | 504 events (engine projection) |
| GET `/api/runs` | seed 14 |
| GET `/api/receipt/{success}` | natural + incremental_net present |
| GET `/api/benchmark/story` | M-10 |
| GET `/api/benchmark/official/contract` | cells 600 |
| POST `.../ai-diagnosis` | DETERMINISTIC_FALLBACK; economic authority `deterministic_engine`; no key leak |

This machine has artefacts mounted → overview official `verified=true`. A bare clone will not.

---

## Browser / mobile

**Not re-verified in a live browser this pass.** Copy and structure changes are in `app.js`. First-view layout was not redesigned. 390/375 wrapping uses existing KPI container queries (5 KPIs → 2 columns on narrow). Do not claim mobile excellence.

---

## Public clone

**Not re-cloned.** Origin is still `c7a11ed`. A fresh clone today is P15, not this working tree. Cloning origin would not validate P17.

---

## AI verification

- Disabled (this environment): DETERMINISTIC_FALLBACK — verified.
- Enabled live Groq: **not run** (`GROQ_API_KEY` unset). Do not paste keys. Rotate any key that was ever pasted in chat.

---

## Benchmark integrity

```
git diff -- artefacts/benchmark/official-cloud-final/    # no output
git diff -- revive/benchmark/official/                   # no output
```

No rerun. No PolicyPack change. Official `LLM_OFF` unchanged.

---

## Security / authorship

- No live `gsk_` / Razorpay live keys in source. Test fixture `gsk_test_secret_value_xyz` only.
- Git authors: `shriansh1625 <omshriansh16@gmail.com>` only. No Co-authored-by trailers.
- Do not commit `.claude/`, `implementation/ui-v3/`, QA scripts.

---

## Remaining P0 (owner, not code)

1. **Record the 5-minute video** (`submission/pitch/FINAL-5-MINUTE-SCRIPT.md`). Mount artefacts or stay on contract. Do not press Run sandbox recovery.
2. **Commit + push this working tree** (when authorized) so public GitHub matches local architecture.
3. **Apply GitHub description + topics** (`submission/GITHUB-METADATA.md`). No `agentic-ai`.

Until (2), an AI evaluator on GitHub will still see AI → ENRV.

---

## Remaining P1

- Live Groq overlay not verified in this pass.
- Mobile not live-tested after KPI change.
- Historical docs (`docs/08` module tables, `P15` topic list) still contain spec language; banners now mark HISTORICAL.
- README screenshot still *shows* `BENCHMARK_VALID`; caption now says the tree is not in Git.

## Remaining P2

- Untracked audit/QA dumps must stay untracked.
- License still none on GitHub.
- Repo slug remains `razorpay_buildathon`.

---

## Scorecard (local working tree)

| Item | Grade | If not STRONG |
|---|---|---|
| Track 03 | STRONG | Written bar |
| Agent | STRONG | `run_traced_cycle` |
| AI | ADEQUATE | Real overlay; not money-path causal |
| Autonomy | ADEQUATE | Real batch; UI now says inspect |
| Economics / ENRV / counterfactual | STRONG | |
| Allocation | ADEQUATE | Real; academic-looking in a pitch |
| Safety / stopping / audit | STRONG | |
| Execution | ADEQUATE | Simulated |
| Measurement / batch | STRONG | Presentation now equation-first |
| Escalation | ADEQUATE | Simulated approver |
| Benchmark | ADEQUATE | Strong experiment; gitignored proof |
| Engineering / performance | STRONG | |
| UI / UX | ADEQUATE | Copy fixed; not live-browsered |
| README / architecture | STRONG locally | Origin still stale |
| Public repo / cloneability / AI-eval readability | WEAK until push | P15 on GitHub |
| Security | ADEQUATE | Rotate leaked key |
| Originality / Razorpay fit | ADEQUATE | Wedge documented; no Agent Studio superiority claim |
| Video | WEAK | Missing |
| Submission form | ADEQUATE | Draft ready; video empty |

---

## Verdict

**Code remediation for verified P17 findings is done locally.**
**Do not declare submission-ready:** video missing, origin still P15, GitHub chrome empty.

**Do not commit until the owner asks.**
