# Final source of truth — PAYVANTA submission

**Date:** 2026-08-28  
**Inspected HEAD:** `25dc006` (`main`, equals `origin/main`)  
**Remote:** `https://github.com/shriansh1625/razorpay_buildathon.git`

This file records what is true on disk versus what a stranger gets from Git.
It is not a claim that the public repository is ready.

**Do not commit from this document. Commit only when the operator explicitly asks.**

---

## 1. What is the final product?

**PAYVANTA** — autonomous revenue recovery intelligence (Razorpay Track 03).

It detects revenue at risk, diagnoses cause, compares counterfactual interventions,
allocates under constraints, gates execution, executes only when authorized,
measures incremental net recovery, and writes an audit trail.

Internal names (do not rename):

| Name | Role |
|---|---|
| PAYVANTA | Public product |
| REVIVE | Official benchmark policy id |
| `revive` | Python / CLI namespace |

The Control Room is a **sandbox demonstration**. The official 600-cell tree is
**independent evaluation evidence**. They are not the same run.

---

## 2. Where it lives (working tree)

| Layer | Path |
|---|---|
| Product UI + HTTP API | `revive/product/` |
| Sandbox session | `revive/product/session.py` (DEMO_SEED = 14) |
| Engine (detect → audit) | `revive/recovery/`, `revive/policy/`, `revive/execution/`, `revive/measurement/`, `revive/audit/` |
| Official benchmark harness | `revive/benchmark/official/` — **do not modify** |
| Official evidence | `artefacts/benchmark/official-cloud-final/` — **do not modify, do not rerun** |
| Product tests | `tests/product/` |
| Spec + evaluator docs | `docs/` |
| Pitch packet | `submission/pitch/` |

Startup (working tree):

```bash
python -m pip install -e ".[dev]"
revive control-room
```

Open http://127.0.0.1:8765

---

## 3. Git reality (P0)

| Fact | Evidence |
|---|---|
| Branch | `main` |
| HEAD | `25dc006` — *Complete M13.27 cloud validation gate for metrics tail rescue* |
| `origin/main` | **identical to HEAD** |
| Logged-out GitHub URL | **404** — repository is not demonstrably public |
| Origin README | Still titled **REVIVE**, “M10 Authorization Gates complete. 170 tests passing.” No Control Room. |
| `revive/product/` | **Untracked** — not on origin |
| `tests/product/` | **Untracked** — not on origin |
| Local `README.md`, `revive/cli.py`, `pyproject.toml` | **Modified, uncommitted** |
| Official cell JSON | **gitignored** via `artefacts/` |

A clean clone of `origin/main` into `%TEMP%\payvanta-public-clone-p9` contains
`revive/` engine modules and **does not contain** `revive/product/`.

**If a stranger clones origin/main, they do not get PAYVANTA.**

They cannot run `revive control-room`. They cannot open Benchmark Lab.
They cannot follow the local README, because that README is not on origin.

---

## 4. What must be in Git (for the submitted product)

These paths exist locally and are **not ignored**. They must be committed
and pushed **when the operator requests it**, or the public repo stays engine-only:

- `revive/product/` (entire tree, including `ui/`)
- `tests/product/`
- `README.md` (PAYVANTA landing page)
- `pyproject.toml` (`package-data` for `product/ui/*`)
- `revive/cli.py` (`control-room` subcommand)
- `revive/__init__.py`
- `docs/42-official-benchmark.md`
- `docs/why-ai.md`
- `docs/claim-evidence-matrix.md`
- `docs/track3-evidence.md`
- `docs/assets/control-room.png`
- `docs/43-operating-architecture.md`
- `submission/pitch/`
- `implementation/final-submission/`
- other modified `docs/*` that name PAYVANTA honestly

Do **not** add: `.env`, `.venv/`, `__pycache__/`, `.claude/`, `llm_cache/`.

---

## 5. What must remain local / gitignored

| Path | Why |
|---|---|
| `artefacts/` | Generated worlds, cell JSON, official-cloud-final (~600 cells). Too large for a default clone; frozen; must not be regenerated into Git. |
| `.venv/`, `__pycache__/`, `.pytest_cache/` | Machine-local |
| `.env` | Secrets — none required for sandbox |

**Official evidence access:** mount `artefacts/benchmark/official-cloud-final/` locally.
README and `GET /api/benchmark/story` explain this. Cell counts are reported only after verification.

---

## 6. What is official evidence?

Read-only tree:

`artefacts/benchmark/official-cloud-final/`

Contract: 20 seeds × 6 profiles × 5 policies = **600 cells**, **120 groups**,
`workers=8`, `BENCHMARK_VALID`, `blocked=false`.

Do not modify. Do not rerun. Do not treat a sandbox session as a cell.

---

## 7. What is sandbox state?

| | |
|---|---|
| Environment | PAYVANTA Sandbox |
| Seed | **14** (do not click Run Recovery in the 5-minute demo) |
| Data | Synthetic test population |
| Execution | Bounded local, simulated adapters |
| Policy pack | Draft pack for the demo world (not the sealed official pack) |
| Prepared success | `opp_CQ6VCH7HPPW9WG284G5EFRMDN0` |
| Prepared blocked | `opp_WST4PPPH81VPNTNC18K0YGRAW9` |

Sandbox incremental net is **this session**. Official M-10 is
`NetRecovered(policy) − NetRecovered(B0)` on a frozen cell.

---

## 8. Old REVIVE files

The Python package is still `revive`. That is intentional.

Origin/main is the **engine + official harness** through M13.27.
PAYVANTA productization (`revive/product/`) was built on top and has not been published.

Do not delete engine modules. Do not rename the package.

---

## 9. Clean-clone verdict (this inspection)

| Check | Result |
|---|---|
| Clone origin | Succeeds **with credentials** (private or unlisted) |
| Logged-out HTTPS | **404** |
| `revive/product` on clone | **Absent** |
| `revive control-room` on clone | **Cannot run** |
| Working-tree Control Room | Present (untracked + modified CLI) |

**P0 remains open until:** (1) GitHub is public, (2) PAYVANTA sources are committed and pushed, (3) a stranger clone + fresh venv follows README and reaches Control Room.
