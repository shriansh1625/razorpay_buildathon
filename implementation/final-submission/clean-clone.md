# Clean clone protocol

## Origin clone (mandatory — executed 2026-08-28)

Directory: `%TEMP%\payvanta-public-clone-p9`  
Command: `git clone --depth 1 https://github.com/shriansh1625/razorpay_buildathon.git`

Fresh venv in that directory, `pip install -e ".[dev]"`, then:

```
revive file = <clone>\revive\__init__.py
PRODUCT_ABSENT ModuleNotFoundError: No module named 'revive.product'
CLI: REVIVE 0.1.0 — generate-dataset, benchmark, … feasibility-gate
      (no control-room)
```

**Result: a stranger clone of origin/main cannot start PAYVANTA.**

Logged-out GitHub page: HTTP 404.

## Repeatable local run (working tree — not origin)

Assumptions: Python 3.11+, this working tree including untracked `revive/product/`.

```bash
python -m pip install -e ".[dev]"
revive control-room
```

- Host: 127.0.0.1
- Port: 8765
- Browser: http://127.0.0.1:8765/#/control
- Do not click Run Recovery for the 5-minute path (seed 14).
- Official cells: mount `artefacts/benchmark/official-cloud-final/` if verifying Benchmark Lab figures.

No global packages required beyond the venv. No `.env`.

## What must happen before the public clone matches the demo

1. Make the GitHub repository **public**.
2. **Commit and push** `revive/product/`, `tests/product/`, PAYVANTA `README.md`, `revive/cli.py`, `pyproject.toml`, evaluator docs (operator-requested — not done in this task).
3. Repeat this clone protocol against origin after the push.
4. Walk Control Room → Analyze → Workspace → Lab → Guardrails → Execution → Receipt → Audit → Benchmark → matrix seed 14.

Until then, **do not declare submission ready.**
