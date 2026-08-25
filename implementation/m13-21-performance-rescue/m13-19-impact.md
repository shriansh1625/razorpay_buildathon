# M13.19 Preflight Impact

Preflight: 30 cells in ~3.5 h ⇒ **~420 s/cell average** (includes B0 fast cells).

Per-cell telemetry (seed=1):

| Profile | REVIVE elapsed (s) |
|---------|-------------------|
| BALANCED | 690 (Run 4) / preflight completed |
| HIGH_NATURAL | ~697 |
| SCARCE | ~447 |

Preflight already showed REVIVE **>480 s** before Run 4. Regression did not begin at Run 4 — it began when **execution bridge made cells do real work** (M13.18), visible as soon as preflight ran with live execution.

M13.19 preflight time is consistent with Run 4 per-cell measurements, not evidence of a new Run 4-specific bug.
