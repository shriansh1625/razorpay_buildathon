# 08 · Submission risks

Official process (Buildathon page): **public repo**, **5-minute pitch video**, **architecture**.

---

## Public repository

| Check | Result | Sev |
|---|---|---|
| Remote | `origin` = `https://github.com/shriansh1625/razorpay_buildathon.git` | — |
| Unauthenticated GET of that URL | **HTTP 404** | **P0** |
| `gh repo view` | Not logged in; cannot prove public | **P0** until proven |
| `origin/main` HEAD | `25dc006` “Complete M13.27 cloud validation gate…” | — |
| Origin README title | **REVIVE — Revenue Recovery Autopilot** / M10 / 170 tests | **P0** |
| `revive/product/` on origin | **Absent** | **P0** |
| `revive control-room` on origin CLI | **Absent** | **P0** |
| `artefacts/` in git | **0 files** (`.gitignore`) | **P0** for evidence portability |
| Local uncommitted / untracked | Entire product UI, product tests, README rewrite, screenshot trees, audits | **P0** if submit happens now |

Even if the GitHub 404 is “private repo,” the official instruction is **public**. Private fails the process. Public-but-M10 also fails the *show the work* intent.

---

## 5-minute pitch video

No media file in the workspace. **P0**.

---

## Architecture

| Artefact | Usable by a stranger? |
|---|---|
| `docs/07-system-architecture.md` | Yes as a spec; cycle model is the real idea |
| `docs/08-agent-architecture.md` | **Stale LLM agent roster** |
| `docs/README.md` header | Says implemented |
| `docs/README.md` status table | Says **source none, benchmark none** |
| `docs/00-project-charter.md` | “No implementation exists” |
| Origin architecture | Same spec pack, plus engine; **no product architecture** (`revive/product/` server → projection → UI) |

A reviewer told to “read the architecture” can conclude the project was never built.

---

## Reproducibility

Local README:

```bash
python -m pip install -e ".[dev]"
revive control-room
```

On a clean clone of **origin/main** that command is invalid.

Further:

- Official evidence must be present on disk for Benchmark Lab; it is not in git.
- First Control Room request builds a 4-cycle world; slow cold start can look like a hang.
- `PLAYWRIGHT_BROWSERS_PATH` and screenshot scripts are QA, not judge path.
- Python 3.11+ declared; no lockfile (empty `dependencies` — stdlib product, pytest in dev). That part is fine.

---

## Repository hygiene (if they dump the working tree as-is)

Untracked / noisy (P2–P3 unless they ship the whole desktop folder):

- `implementation/ui-v3/**` screenshots (dozens of PNGs)
- `implementation/m13-26-abundant-revive-forensics/` profiles and raw JSON
- `implementation/productization-audit/`, `ui-v2-audit/`
- `.claude/launch.json`
- `scripts/qa_*.py` (fine as evidence if explained; look like debug if not)

`implementation/open-blockers.md` still M0.

No `.env` or credential files found.

---

## Documentation drift (P1)

| Document | Says | Reality |
|---|---|---|
| Origin README | REVIVE M10 | Local PAYVANTA Control Room |
| `docs/README.md` § Status | No source, no benchmark | Engine + local UI + local 600 cells |
| `docs/00` | Spec only | Implemented |
| `docs/08` | 2 LLM agents | 0 LLM calls on money path |
| `docs/26` | PLACEHOLDER metrics | Seed-14 numbers exist |
| `docs/01` | Future demo beats | Product routes exist locally |
| Product README | `revive control-room` | Only true after commit + push |

Broken links: several docs point at `README.md#c-7--the-deterministic-authority-rule`. C-7 lives in **`docs/README.md`**, not the package README.

---

## Architecture discovery for a stranger (question 5)

**Without founders, from origin:** they can reconstruct a **benchmarked recovery engine**. They cannot reconstruct PAYVANTA.

**Without founders, from a laptop with uncommitted files and artefacts extracted:** they can run the OS if they guess `python -m revive.product.server`. Remaining ambiguities:

1. Why DRAFT pack in the UI vs SEALED in Benchmark Lab.
2. Why Run Recovery is forbidden in the pitch.
3. Where the LLM is.
4. Whether ₹19,799 is official.
5. Which README is true.
6. Whether GitHub is the submission.

That is enough to lose a silent AI-evaluator pass.
