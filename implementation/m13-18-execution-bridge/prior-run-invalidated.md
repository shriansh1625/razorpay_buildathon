# Prior Official Run — Invalidated

**Status:** `INVALIDATED_BY_M13.17_EXECUTION_BRIDGE_DEFECT`

## Run record

| Field | Value |
|-------|-------|
| Path | `artefacts/benchmark/official/` |
| Cells | 600 / 600 |
| Config hash | `62438f185d9ffd95dc7fa75eaed933ebbed236152194d2c0c4e748f5ad15c8a7` |
| Validator | `BENCHMARK_VALID` (structural only) |
| Admissible as benchmark evidence | **NO** |

## Why invalidated

M13.17 established two integration defects prevented intended execution:

1. **Baselines:** world `opportunity_id` ≠ sentinel `opportunity_id_for(natural_key)` — 100% sentinel lookup miss.
2. **REVIVE:** `simulated_v1` approver not wired — 100% G7 `REQUIRES_HUMAN_APPROVAL`.

## Preservation policy

- Artifacts **NOT modified**
- Artifacts **NOT deleted**
- Retained as evidence of the failed integration run

## Corrected rerun (future)

Same frozen experimental configuration; new implementation revision:

- `IMPLEMENTATION_REVISION = m13.18-execution-bridge-v1`
- `BENCHMARK_RUNNER_VERSION = 0.13.18-m13.18`

Config hash unchanged — runner revision distinguishes runs.
