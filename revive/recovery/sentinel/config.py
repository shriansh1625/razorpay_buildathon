"""Sentinel configuration — recovery windows are PROVISIONAL (OQ-03)."""

from __future__ import annotations

from dataclasses import dataclass

from revive.domain.enums import RiskClass

DETECTOR_VERSION = "0.4.0-m4"

MINUTE = 1
HOUR = 60
DAY = 24 * 60

# PROVISIONAL — OQ-03. Not frozen for benchmark claims.
DEFAULT_RECOVERY_WINDOW_MINUTES: dict[RiskClass, int] = {
    RiskClass.PAYMENT_FAILURE: 14 * DAY,
    RiskClass.CHECKOUT_ABANDONMENT: 48 * HOUR,
    RiskClass.SUBSCRIPTION_FAILURE: 14 * DAY,
    RiskClass.RECEIVABLE_OVERDUE: 90 * DAY,
    RiskClass.MANDATE_HEALTH: 14 * DAY,
}

# Cart re-abandonment coalescing window (docs/12 §6.3 open item).
DEFAULT_CHECKOUT_COALESCE_MINUTES = 24 * HOUR

# Mandate pre-failure: expiry within this window (docs/12 §2.1).
DEFAULT_MANDATE_BILLING_WINDOW_MINUTES = 45 * DAY

# Degradation monitor (RR-FUNC-006) — observable failure-rate spike.
DEFAULT_DEGRADATION_WINDOW_MINUTES = 90
DEFAULT_DEGRADATION_MIN_ATTEMPTS = 3
DEFAULT_DEGRADATION_FAILURE_RATE = 0.6


@dataclass(frozen=True, slots=True)
class SentinelConfig:
    """Detection-layer config. Windows/thresholds are provisional until PolicyPack is sealed."""

    recovery_window_minutes: dict[RiskClass, int] | None = None
    checkout_coalesce_minutes: int = DEFAULT_CHECKOUT_COALESCE_MINUTES
    mandate_billing_window_minutes: int = DEFAULT_MANDATE_BILLING_WINDOW_MINUTES
    continuation_factor: float = 0.0  # ADR-007 default
    degradation_window_minutes: int = DEFAULT_DEGRADATION_WINDOW_MINUTES
    degradation_min_attempts: int = DEFAULT_DEGRADATION_MIN_ATTEMPTS
    degradation_failure_rate: float = DEFAULT_DEGRADATION_FAILURE_RATE
    detector_version: str = DETECTOR_VERSION

    def window_minutes(self, risk_class: RiskClass) -> int:
        table = self.recovery_window_minutes or DEFAULT_RECOVERY_WINDOW_MINUTES
        return table[risk_class]


def default_sentinel_config() -> SentinelConfig:
    return SentinelConfig()
