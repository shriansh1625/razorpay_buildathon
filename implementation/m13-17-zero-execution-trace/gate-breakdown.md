# M10 Gate Breakdown — seed=1 BALANCED official config

## Baselines B1/B2/B3

| Gate / rule | Evaluations | Blocks |
|-------------|------------:|-------:|
| G1–G12 | **0** | **0** |
| SR-01–SR-11 | **0** | **0** |

**Reason:** `authorize_execution()` is never called. All baseline selections are dropped at `baseline_pipeline.py:96-98` before M10.

## REVIVE

| Outcome | Count | Share |
|---------|------:|------:|
| Total `authorize_execution()` calls | 121,107 | 100% |
| `AUTHORIZED` | 0 | 0% |
| `REQUIRES_HUMAN_APPROVAL` | 121,107 | **100%** |
| `BLOCKED` (other) | 0 | 0% |
| `STALE` / `EXPIRED` / `REPLAN_REQUIRED` | 0 | 0% |

### Gate-level (G1–G12)

All 121,107 authorizations share the same blocking pattern:

| Gate | Verdict on block | Count |
|------|------------------|------:|
| G1 | ALLOW | 121,107 |
| G2 | ALLOW | 121,107 |
| G3 | ALLOW | 121,107 |
| G4 | ALLOW | 121,107 |
| G5 | ALLOW | 121,107 |
| G6 | ALLOW | 121,107 |
| **G7** | **REQUIRE_APPROVAL** | **121,107** |
| G8–G12 | ALLOW (not reached as blocking verdict) | — |

### G7 trigger breakdown

| Trigger | Count |
|---------|------:|
| **UNCERTAINTY** | **121,107** |
| VALUE_THRESHOLD | 0 |
| ACTION_FAMILY | 0 |
| FIRST_USE | 0 |

Observed: `(enrv_hi - enrv_lo) / enrv_paise > rules.approval_uncertainty_ratio` for every authorization (`revive/policy/gates.py:223-225`).

### Stopping rules (SR)

Evaluated inside `authorize_execution()` before gates when blocking stop exists. For REVIVE trace: **0 blocking stopping rules** — all blocks originate from G7, not SR-01–SR-11.

## M11 status

| Policy | Authorized actions | `execute_authorization()` calls |
|--------|-------------------:|--------------------------------:|
| B1/B2/B3 | 0 | 0 |
| REVIVE | 0 | 0 |

M11 is **never reached** for any policy on official seed=1 BALANCED.

## M12 status

| Policy | Executions | Measurements |
|--------|----------:|-------------:|
| All | 0 | 0 |

No M12 investigation warranted — execution count is zero upstream.
