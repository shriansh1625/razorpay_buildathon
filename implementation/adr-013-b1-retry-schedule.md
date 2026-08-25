# ADR-013 — B1 FIXED_RETRY Published Schedule

**Status:** ACCEPTED  
**Date accepted:** 2026-08-23  
**Milestone:** M13.10 official freeze  
**Authority:** `docs/20-benchmark.md` §2 (B1), BF-9

---

## Decision

Freeze schedule as **`adr-013_v1`** in `revive/benchmark/config.py` `B1_RETRY_SCHEDULE`.

Per-class delay/action tuples unchanged from draft — schedule content was credible; version promoted to frozen.

| Risk class | Steps (delay min → action) |
|------------|----------------------------|
| `PAYMENT_FAILURE` | 0→A01, 30→A02, 120→A02, 360→A03 |
| `CHECKOUT_ABANDONMENT` | 60→A09, 180→A05, 360→A04 |
| `SUBSCRIPTION_FAILURE` | 0→A01, 60→A08, 240→A02 |
| `RECEIVABLE_OVERDUE` | 0→A05, 1440→A05, 4320→A08 |
| `MANDATE_HEALTH` | 0→A08, 1440→A11 |

B1 `strategy_version`: `b1_adr-013_v1`

---

## Consequences

- Recorded in official benchmark `config_hash` as `B1_schedule_version=adr-013_v1`
- Published in benchmark disclosure artefacts at run time
