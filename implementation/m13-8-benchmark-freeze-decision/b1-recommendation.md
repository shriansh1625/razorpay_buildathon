# B1 Schedule Recommendation (ADR-013)

Schedule in `revive/benchmark/config.py` is internally coherent:
- Per risk class delays with escalating actions
- Payment: immediate retry → scheduled → instrument change
- Receivable: reminder progression → mandate update

**Recommendation:** ACCEPT ADR-013 schedule as-is (`adr-013_v1`).
- Credible status-quo baseline (BF-9)
- Not weakened or strengthened for REVIVE
- Publish in benchmark disclosures at freeze
