# M13.22 Baseline Profile

**Label:** DEVELOPMENT_FORENSIC_ONLY — NOT official evidence

**Cell:** seed=2 BALANCED REVIVE, frozen official scale, 2016 cycles

## M13.21 reference (pre-M13.22)

| Stage | Seconds | Share | Calls |
|-------|---------|-------|-------|
| M4 | 28.3 | 5.5% | 2016 |
| M5 | 68.2 | 13.3% | — |
| **M6** | **151.0** | **29.4%** | 753479 |
| **M7** | **156.7** | **30.5%** | 753479 |
| M8 | 59.7 | 11.6% | 2016 |
| M9–M12 | ~21.8 | 4.2% | — |
| **Total (instrumented loop)** | **514** | | |

Counters: 5,547,419 candidates / valuations; 121,120 authorizations; 101,615 executions.

## Hotspot inventory (measured structure, not speculation)

| Counter | Per cell |
|---------|----------|
| Opportunities (M4) | 753,479 |
| Candidates (M6) | 5,547,419 |
| Valuations (M7) | 5,547,419 |
| Natural probability calls | 1 per opportunity (already reused across actions) |
| Predictor / shrinkage | 1 per candidate |
| Cost / fatigue / ENRV | 1 per non-A00 candidate |
| `bankers_round_paise` | several Decimal(str) ops per valued candidate |
| Candidate ID SHA-256 | 1 per candidate |

M6+M7 remain ~60% of loop time.
