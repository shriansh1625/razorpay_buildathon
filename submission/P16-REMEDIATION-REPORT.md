# PAYVANTA — P16 remediation report

**Date:** 2026-08-28
**Constraint:** no commit, no push, no benchmark changes
**Source:** independent hostile panel (treated as red-team findings, not authority)

---

## 1. Findings accepted (verified)

| Finding | Severity | Fix |
|---|---|---|
| README said “does not call an LLM” while Groq exists | P1 | README engine vs sandbox overlay language |
| `docs/43` drew AI → ENRV | P1 | Parallel overlay diagram; dotted “propose only” |
| `docs/43` / `docs/08` / `docs/track3` “no LLM / no live model” | P1 | Status banners + shipped overlay |
| `docs/07` Claude table | P1 | HISTORICAL SPEC vs SHIPPED Groq overlay |
| `track03` booleans looked like proof | P1 | `capability_declaration` + implementation/test refs |
| Pulse 18 vs 129 unexplained | P1 | `evaluated_note` from actual candidate counts |
| AI events not on product audit stream | P1 | Overlay rows on `/api/audit` + snapshot ledger (**not** engine hash journal) |
| Names PAYVANTA / revive / REVIVE / repo slug | P1 | README identity table |
| User persona missing | P2 | Revenue / finance ops |
| Incremental vs gross | P1 | Hero caption + README |
| Architecture vs Analyze-as-autonomy | P1 | `run_traced_cycle` vs UI trigger in docs + pitch |
| Pitch too long / matrix unmounted | P1 | Script cut + NOT MOUNTED rule |
| `agentic-ai` topic | P2 | Removed from GitHub metadata |
| Form challenges laundry list | P1 | M13.25 + M13.27 only (`FORM-ANSWERS.md`) |
| Video missing | **P0 official** | **Not fixable in code** — owner must record |

## 2. Findings rejected or documented

| Finding | Disposition |
|---|---|
| Groq must enter ENRV to be “real AI” | **Rejected.** Would change money path and contradict safety. Documented as overlay. |
| Put 600 cells in git | **Rejected.** Intentional gitignore. Docs now say mount vs NOT MOUNTED. |
| Live Razorpay rails | **Rejected.** Out of scope; README limitations stand. |
| Rename repo/package/policy | **Rejected.** Identity table instead. |
| Rebuild AuditJournal hash chain for Groq | **Rejected.** Overlay rows on product ledger only; `money_path: false`. |
| “120B was necessary” | **Rejected.** Implementation choice; not ablated. |
| Live Groq in this pass | **Not claimed.** Key must be in env; not printed. Fallback tests remain. |

## 3. Fixes applied (local, uncommitted)

- `README.md`, `docs/43`, `docs/08`, `docs/07`, `docs/why-ai.md`, `docs/track3-evidence.md`
- `revive/product/overview.py` track03 declarations
- `revive/product/project.py` pulse `evaluated_note`
- `revive/product/server.py` audit overlay merge
- `revive/product/intelligence/diagnosis.py` event metadata
- `revive/product/ui/app.js` / `app.css` — observed/inferred/proposed, receipt layers, blocked `NOT_EXECUTED`, net ≠ gross
- Pitch + `submission/FORM-ANSWERS.md` + GitHub metadata
- Tests: overview, redteam, intelligence audit overlay

## 4. Remaining P0/P1 (owner)

1. **Record 5-minute video** (official requirement).
2. **Mount official artefacts** before recording the matrix.
3. Apply GitHub description/topics manually.
4. Rotate Groq key if not already; use env only.
5. Independent second hostile review after this pass.

## 5. Canonical story (must match every public artifact)

The model can propose. The engine decides. Controls authorize. The executor acts. Measurement proves. Audit records. The official benchmark validates the **frozen engine**, not Groq.

## 6. Tests / integrity (run in this pass)

See command results: `pytest tests/product -q` → **55 passed**. `node --check revive/product/ui/app.js` → exit 0.

Live Groq: **GROQ_API_KEY was not set in this environment.** Fallback path remains the verified path. Do not claim a live GPT-OSS call from P16.

Browser / public clone: **not re-run in P16** (no commit/push; local RC only). Prior P15 clone was at `c7a11ed`. After you commit, re-clone.

## 7. Scorecard after remediation (qualitative)

| Area | Rating | Why not STRONG |
|---|---|---|
| Track 03 | STRONG | Engine loop + batch + WST4 |
| Core engineering | STRONG | Unchanged |
| Safety | STRONG | Groq still cannot execute |
| Economics | STRONG | Incremental net labeled |
| Benchmark | ADEQUATE | Still unmounted on clone — honest now |
| AI | ADEQUATE | Overlay is defensible, not causal |
| README / architecture | STRONG if review agrees one story |
| Demo | ADEQUATE until video exists |
| Submission form | STRONG draft; video hole |
| Razorpay fit | STRONG wedge: economics vs Agent Studio ops agents |
| Agent-evaluator readability | STRONG if they read README + 43, not old spec tables blindly |

**Do not commit. Do not push.** Next: independent second hostile review.
