# ADR-011 — ENRV ε Threshold Resolution

**Status:** ACCEPTED  
**Date accepted:** 2026-08-23  
**Milestone:** M13.10 official freeze  
**Related:** OQ-01, `docs/11-counterfactual-engine.md` §5.3

---

## Decision

**ε = 100 paise (₹1)** for the official benchmark.

Rationale: aligns with `docs/11` §5.3 sub-threshold noise filter; M13.8 sensitivity showed stable portfolio behavior vs ε=0 on 21-day calibration config.

---

## Implementation

- Sealed in `pol_m13_official_v1` PolicyPack (`epsilon_paise=100`)
- Authoritative ε via PolicyPack; valuation derives from PolicyPack in official path
- Recorded in `OFFICIAL_BENCHMARK_CONFIG_HASH`

---

## Consequences

- DM-13 and allocator eligibility use ε=100 paise for official benchmark
- Development draft pack (`pol_m1_draft`, ε=0) remains for non-official runs only
