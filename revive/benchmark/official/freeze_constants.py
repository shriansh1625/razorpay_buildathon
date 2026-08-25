"""M13.10 human-approved official benchmark freeze constants.

Recorded in implementation/checkpoints/M13.10-official-freeze.md.
Do not change without a new benchmark version and ADR update.
"""

from __future__ import annotations

# Human acceptance — M13.10 governance seal (2026-08-23)
ADR_011_ACCEPTED = True
ADR_012_ACCEPTED = True
ADR_013_ACCEPTED = True

OFFICIAL_EPSILON_PAISE = 100
OFFICIAL_HORIZON_DAYS = 21
OFFICIAL_OPPORTUNITY_COUNT = 500
OFFICIAL_CUSTOMER_COUNT = 100
OFFICIAL_CYCLE_LENGTH_MINUTES = 15

OFFICIAL_POLICY_PACK_VERSION = "pol_m13_official_v1"
OFFICIAL_B1_SCHEDULE_VERSION = "adr-013_v1"
OFFICIAL_APPROVER_VERSION = "simulated_v1"

OFFICIAL_BENCHMARK_ID = "revive_official_v1"
PREFLIGHT_BENCHMARK_ID = "revive_official_preflight_m13_19"

# M13.18 — distinguishes same frozen config from prior integration-defect run.
IMPLEMENTATION_REVISION = "m13.18-execution-bridge-v1"
BENCHMARK_RUNNER_VERSION = "0.13.18-m13.18"
