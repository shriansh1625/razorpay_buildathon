# Baseline Identity — Root Cause (M13.17 → M13.18)

See `implementation/m13-17-zero-execution-trace/root-cause.md`.

**Summary:** `run_baseline_cycle_full()` matched baseline decisions by world `opportunity_id` against sentinel `detect()` results keyed by `opportunity_id_for(natural_key)` — zero overlap.

**Fix:** Resolve via canonical `natural_key` using sentinel identity functions (`revive/recovery/sentinel/identity_bridge.py`).
