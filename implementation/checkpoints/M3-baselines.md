# M3 Checkpoint — Baseline Policies + Evaluation Control

**Milestone:** M3 — Baseline Policies B0–B3  
**Date:** 2026-08-21  
**Status:** COMPLETE

---

## Baselines implemented

| ID | Name | Module | Source |
|----|------|--------|--------|
| B0 | `NO_ACTION` | `revive/benchmark/baselines/b0_no_action.py` | `docs/20` §2 |
| B1 | `FIXED_RETRY` | `revive/benchmark/baselines/b1_fixed_retry.py` | `docs/20` §2, `15` §7.1 |
| B2 | `CONTACT_ALL` | `revive/benchmark/baselines/b2_contact_all.py` | `docs/20` §2 |
| B3 | `GREEDY_ENRV` | `revive/benchmark/baselines/b3_greedy_enrv.py` | `docs/20` §2, `10` §5.2 |

B4–B6 deferred to P1 per implementation plan.

---

## Decision rules

| Baseline | Philosophy |
|----------|------------|
| B0 | Never acts — natural recovery floor |
| B1 | Class-based fixed retry schedule indexed by `attempt_seq`; waits until delay elapsed |
| B2 | Contacts every eligible opportunity in `opportunity_id` order until capacity exhausted |
| B3 | Ranks eligible opportunities by raw heuristic ENRV (observable-only); greedy assignment |

---

## Configuration

| Item | Location | Status |
|------|----------|--------|
| B1 retry schedule | `revive/benchmark/config.py` → `B1_RETRY_SCHEDULE` | **PROVISIONAL** (ADR-013 draft) |
| Action costs | `DEFAULT_ACTION_COSTS_PAISE` | PROVISIONAL |
| Shared capacities | `BaselineEnvironmentConfig` | PROVISIONAL |
| ε | `PolicyPack.epsilon_paise` | PROVISIONAL (ADR-011) |
| B3 ENRV heuristic | `revive/benchmark/pricing.py` | Observable-only stub until M7 predictor |

---

## Fairness controls

- All baselines use `BaselineCycleContext` with identical capacity limits (BF-4)
- Eligibility filter shared (`baselines/eligibility.py`)
- Resource reservation shared (`baselines/resources.py`)
- Same observable opportunity set per cycle (fairness test)
- No policy identity in simulation oracle (M2 preserved)

---

## Integrity checks

- `assert_baseline_modules_do_not_import_oracle()` — AST import guard
- `assert_decision_path_does_not_import_oracle()` — unchanged
- Baseline decisions contain no hidden oracle fields

---

## Tests

| Module | Focus |
|--------|-------|
| `tests/benchmark/test_b0_no_action.py` | Control behaviour |
| `tests/benchmark/test_b1_fixed_retry.py` | Schedule + wait |
| `tests/benchmark/test_b2_contact_all.py` | Capacity exhaustion |
| `tests/benchmark/test_b3_greedy_enrv.py` | ENRV ranking |
| `tests/benchmark/test_fairness.py` | Cross-baseline fairness + reproducibility |

**Result:** 60 tests passing (full suite)

---

## Development validation

- `run_baseline_cycle()` executes one decision cycle on observable world view
- Produces structured `BaselineDecision` traces (policy ID, reason codes, ranks)
- **No official benchmark metrics or headline recovery claims**

---

## Known limitations

- B3 uses observable heuristic ENRV, not full counterfactual engine (M7)
- Full guardrail gate execution deferred to M10 — baselines respect capacity skeleton only
- No execution adapter invocation or outcome measurement in M3
- B1 schedule not frozen for benchmark

---

## Provisional parameters

- B1 `B1_RETRY_SCHEDULE` — see `implementation/adr-013-b1-retry-schedule.md`
- Action costs and cycle capacities — `revive/benchmark/config.py`

---

## Next milestone

**M4 — Revenue Sentinel** — NOT AUTHORIZED

---

> **Official benchmark results are not frozen or claimed at M3.**
