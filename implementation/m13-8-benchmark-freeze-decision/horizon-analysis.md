# Horizon Analysis

## Configuration A — 30-day window

- Label: 500 opps / 100 customers / 30-day window
- Virtual cycles: 30 days × 96 cycles/day (15 min) = 2,880 allocation cycles
- Mid-cycle snapshot: day 15
- Documented in `official_scale_config` / ADR-012 proposal

## Configuration B — 21-day window

- Label: 500 opps / 100 customers / 21-day window (calibration scale)
- Virtual cycles: 21 days × 96 cycles/day = 2,016 cycles
- Mid-cycle snapshot: day 10.5
- Documented in `calibration_config` horizon (40 opps dev scale)

## Recovery-horizon validity (docs/19, ADR-011 OQ-03)

| Window | Payment 14d | Checkout 48h | Subscription 14d | Receivable 90d |
|--------|-------------|----------------|------------------|----------------|
| 21-day | Full window | Full window | Full window | Partial (ageing begins) |
| 30-day | Full window | Full window | Full window | More ageing exposure |

**Recommendation:** 21-day window provides sufficient virtual time for payment/checkout/subscription recovery workflows while keeping receivable ageing meaningful without dominating the batch. 30-day mid-cycle produces a homogeneous retry-only candidate pool (M13.7).

**Chosen candidate:** B
