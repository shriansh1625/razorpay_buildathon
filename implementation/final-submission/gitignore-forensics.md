# .gitignore forensics

`.gitignore` (working tree):

```
__pycache__/
*.py[cod]
*.egg-info/
.eggs/
dist/
build/
.pytest_cache/
.mypy_cache/
.ruff_cache/
revive.db
artefacts/
llm_cache/
.env
.venv/
venv/
revive.egg-info/
```

## PAYVANTA product code — not ignored

`git check-ignore revive/product/ui/app.js` → no match.

`revive/product/` and `tests/product/` are **untracked because they were never added**, not because they are ignored.

That is the P0 publishing gap. Adding them to Git is a commit (operator-requested), not a gitignore change.

## Intentionally ignored

| Rule | What it hides | Submission strategy |
|---|---|---|
| `artefacts/` | Official 600-cell tree, datasets, development dumps | Keep ignored. Mount locally. README explains access. |
| `.env` | Credentials | None required for sandbox. Do not add. |
| `.venv/` | Local interpreter | Fresh venv on clone. |
| `llm_cache/` | Specified LLM cache dir | No LLM runtime in this submission. |
| `__pycache__/`, pytest caches | Bytecode | Never commit. |

## Do not ignore

- `revive/product/`
- `tests/product/`
- `docs/`
- `submission/`
- `README.md`
- `pyproject.toml`

## Screenshot assets

`docs/assets/control-room.png` is a small landing-page image. It is **not** ignored. Official QA dumps under `implementation/ui-v3/` may stay untracked (large, local).
