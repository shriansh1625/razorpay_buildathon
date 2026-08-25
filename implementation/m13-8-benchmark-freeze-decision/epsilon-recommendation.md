# Epsilon Recommendation (ADR-011 preparation)

ADR-011 **not auto-accepted**. Analysis on recommended 21-day config, seed 1 BALANCED.

| ε (paise) | B3 selected | REVIVE selected | differing |
|-----------|-------------|-----------------|-----------|
| 0 | 150 | 136 | 43 |
| 100 | 150 | 136 | 43 |
| 500 | 150 | 138 | 41 |
| 1000 | 150 | 136 | 43 |
| 5000 | 150 | 125 | 35 |

## Recommendation

**Proposed ε = 100 paise (₹1)** — aligns with `docs/11` §5.3 noise filter.

- At ε=0 and ε=100 on 21d/500 scale, selection counts are stable in this sample.
- ε=100 suppresses sub-threshold dust without materially changing portfolio conflicts.
- **Not selected based on REVIVE advantage** — identical differing counts in sweep.

**Status recommendation:** PROVISIONAL until ADR-011 formally ACCEPTED.
