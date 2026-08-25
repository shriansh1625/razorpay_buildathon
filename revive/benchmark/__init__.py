"""
Benchmark harness — baselines B0–B3 (M3) + official engine (M13).
"""

DECISION_PATH_MODULES = (
    "revive.recovery",
    "revive.allocation",
    "revive.decision",
    "revive.policy",
)

BASELINE_MODULES = (
    "revive.benchmark",
    "revive.benchmark.baselines",
)

ORACLE_MODULE = "revive.simulation.oracle"
