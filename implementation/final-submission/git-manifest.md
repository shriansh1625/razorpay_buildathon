# Public submission manifest — PAYVANTA

**Date:** 2026-08-28  
**Purpose:** Files to ship on `origin/main` so a stranger gets the final PAYVANTA product.

Official benchmark cell JSON (`artefacts/benchmark/official-cloud-final/`) stays **local-only**
and gitignored. README and API explain evidence mounting.

---

## SOURCE FILES TO SHIP

| Path | Role |
|---|---|
| `revive/product/` | Control Room UI, HTTP API, sandbox session, benchmark lab reader |
| `revive/cli.py` | `revive control-room` entry |
| `revive/__init__.py` | Package init |
| `pyproject.toml` | Install metadata, `revive` console script, UI package-data |
| `README.md` | Public landing page, setup, Track 03, benchmark contract |

Engine modules under `revive/` (recovery, benchmark harness, execution, etc.) are already
on `origin/main` at `25dc006`. This commit adds the product layer above them.

---

## TESTS TO SHIP

| Path | Role |
|---|---|
| `tests/product/test_control_room.py` | Control Room / sandbox smoke |
| `tests/product/test_overview.py` | `/api/product/overview`, Track 03, intelligence |
| `tests/product/test_official_evidence.py` | Official evidence reader (read-only) |
| `tests/product/test_benchmark_story.py` | Benchmark story + contract APIs |
| `tests/product/test_submission_redteam.py` | Rejects writes to official benchmark APIs |

---

## DOCS TO SHIP

### New evaluator / submission docs

| Path | Role |
|---|---|
| `docs/42-official-benchmark.md` | Official experiment evidence |
| `docs/43-operating-architecture.md` | Operating architecture diagrams |
| `docs/why-ai.md` | AI credibility (LLM off, deterministic diagnosis) |
| `docs/claim-evidence-matrix.md` | Claim → source → test → UI → API |
| `docs/track3-evidence.md` | Track 03 requirement mapping |
| `docs/competition-differentiation.md` | Competition positioning |
| `docs/assets/control-room.png` | README hero screenshot |

### Updated spec / architecture docs

All modified files under `docs/` (README index, architecture, agent status banner,
UI spec, demo script, glossary, etc.) — aligned to PAYVANTA vocabulary.

### Submission integrity (internal, public)

| Path | Role |
|---|---|
| `implementation/final-submission/` | Source-of-truth, risk register, clone protocol, this manifest |
| `implementation/final-evaluator-audit/` | Final evaluator audit findings |
| `implementation/checkpoints/M13.26-abundant-revive-forensics.md` | Engineering forensics checkpoint |

---

## PITCH FILES TO SHIP

| Path | Role |
|---|---|
| `submission/pitch/5-minute-script.md` | Demo narration |
| `submission/pitch/shot-list.md` | Camera / screen plan |
| `submission/pitch/screen-order.md` | Screen sequence |
| `submission/pitch/speaker-notes.md` | Speaker notes |
| `submission/pitch/judge-questions.md` | Q&A prep |
| `submission/pitch/failure-contingency.md` | Failure fallback |

Video file is produced separately; not required in Git.

---

## LOCAL-ONLY FILES (do not stage)

| Path | Why |
|---|---|
| `artefacts/` | Official 600-cell evidence tree; frozen; gitignored; mount locally |
| `.venv/`, `venv/` | Machine-local Python environment |
| `__pycache__/`, `*.pyc` | Bytecode |
| `.pytest_cache/` | Test cache |
| `.env` | Secrets (none required for sandbox) |
| `.claude/` | Local IDE / launcher config |
| `llm_cache/` | Runtime cache |
| `revive.db` | Local sandbox database |
| `implementation/m13-26-abundant-revive-forensics/*.json`, `*.prof` | Raw forensic captures |
| `implementation/ui-v3/qa-screenshots/` | Regenerable QA captures |
| `implementation/ui-v3/final-screenshots/` | Regenerable viewport captures |
| `scripts/qa_*.py`, `scripts/capture_*.py` | Local QA automation (optional, not submission-critical) |

---

## Pre-push verification (completed before commit)

- [x] `pytest tests/product -q` → 34 passed
- [x] `node --check revive/product/ui/app.js` → pass
- [x] Secret scan → no API keys, tokens, or credentials in candidate files
- [x] `revive/product/` and `tests/product/` are **not** gitignored
- [x] `artefacts/` remains gitignored
- [x] Official benchmark artifacts not modified
