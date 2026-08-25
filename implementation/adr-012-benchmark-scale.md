# ADR-012 — Official Benchmark Scale and Horizon

**Status:** ACCEPTED  
**Date accepted:** 2026-08-23  
**Milestone:** M13.10 official freeze

---

## Decision

Official generator configuration:

| Parameter | Value |
|-----------|-------|
| `opportunity_count` | 500 |
| `customer_count` | 100 |
| `simulation_window_days` | **21** |
| `cycle_interval_minutes` | 15 |
| `profiles` | all six documented profiles |
| `seeds` | 1–20 |

---

## Rejected

- 30-day horizon at 500/100 — portfolio thesis invalid (M13.7/M13.8/M13.9 evidence)

---

## Evidence

21-day window exercises multi-resource portfolio competition, matches calibration development horizon, and covers documented recovery windows without trivializing receivable ageing within the virtual month.

---

## Implementation

- `revive/benchmark/official/config.py` `_base_generator_config`
- `revive/benchmark/official/freeze_constants.py`
