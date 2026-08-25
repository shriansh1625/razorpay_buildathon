"""Context assembly configuration — history windows are PROVISIONAL assumptions."""

from __future__ import annotations

from dataclasses import dataclass

FEATURE_SCHEMA_VERSION = "0.5.0-m5"

MINUTE = 1
HOUR = 60
DAY = 24 * 60

# Customer payment history lookback — not benchmark-tuned.
DEFAULT_CUSTOMER_HISTORY_DAYS = 90

# Contact/fatigue window (RR-FUNC-014).
DEFAULT_FATIGUE_WINDOW_DAYS = 30
DEFAULT_FATIGUE_7D_DAYS = 7

# Payment attempt clustering window for temporal patterns.
DEFAULT_FAILURE_CLUSTER_MINUTES = 20

# Baseline failure rate for merchant-level comparison (observable heuristic).
DEFAULT_BASELINE_FAILURE_RATE = 0.15


@dataclass(frozen=True, slots=True)
class ContextConfig:
    customer_history_days: int = DEFAULT_CUSTOMER_HISTORY_DAYS
    fatigue_window_days: int = DEFAULT_FATIGUE_WINDOW_DAYS
    fatigue_7d_days: int = DEFAULT_FATIGUE_7D_DAYS
    failure_cluster_minutes: int = DEFAULT_FAILURE_CLUSTER_MINUTES
    baseline_failure_rate: float = DEFAULT_BASELINE_FAILURE_RATE
    degradation_window_minutes: int = 90
    degradation_min_attempts: int = 3
    degradation_failure_rate: float = 0.6
    feature_schema_version: str = FEATURE_SCHEMA_VERSION


def default_context_config() -> ContextConfig:
    return ContextConfig()
