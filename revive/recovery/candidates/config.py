"""Candidate generator configuration — provisional policy defaults (docs/13)."""

from __future__ import annotations

from dataclasses import dataclass

GENERATOR_VERSION = "0.6.0-m6"

# Communication window — merchant local hours (PROVISIONAL).
DEFAULT_COMM_WINDOW_START_HOUR = 9
DEFAULT_COMM_WINDOW_END_HOUR = 19

# Retry / contact caps (PROVISIONAL until PolicyPack sealed).
DEFAULT_MAX_RETRY_ATTEMPTS = 5
DEFAULT_CONTACT_CAP_PER_CUSTOMER = 2
DEFAULT_CONTACT_CAP_7D = 8

# Incentive policy (PROVISIONAL).
DEFAULT_INCENTIVE_MAX_PCT_OF_V = 0.05
DEFAULT_INCENTIVE_MAX_PAISE = 5000

# Approval thresholds (PROVISIONAL).
DEFAULT_APPROVAL_VALUE_THRESHOLD_PAISE = 50_000

# Timing (PROVISIONAL).
DEFAULT_SCHEDULED_RETRY_DELAY_MINUTES = 60
DEFAULT_ISSUER_DOWNTIME_DELAY_MINUTES = 120
DEFAULT_COOLDOWN_MINUTES = 30


@dataclass(frozen=True, slots=True)
class CandidateConfig:
    comm_window_start_hour: int = DEFAULT_COMM_WINDOW_START_HOUR
    comm_window_end_hour: int = DEFAULT_COMM_WINDOW_END_HOUR
    max_retry_attempts: int = DEFAULT_MAX_RETRY_ATTEMPTS
    contact_cap_per_customer: int = DEFAULT_CONTACT_CAP_PER_CUSTOMER
    contact_cap_7d: int = DEFAULT_CONTACT_CAP_7D
    incentive_max_pct_of_v: float = DEFAULT_INCENTIVE_MAX_PCT_OF_V
    incentive_max_paise: int = DEFAULT_INCENTIVE_MAX_PAISE
    approval_value_threshold_paise: int = DEFAULT_APPROVAL_VALUE_THRESHOLD_PAISE
    scheduled_retry_delay_minutes: int = DEFAULT_SCHEDULED_RETRY_DELAY_MINUTES
    issuer_downtime_delay_minutes: int = DEFAULT_ISSUER_DOWNTIME_DELAY_MINUTES
    cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES
    generator_version: str = GENERATOR_VERSION


def default_candidate_config() -> CandidateConfig:
    return CandidateConfig()


def config_from_policy_pack(metadata: dict) -> CandidateConfig:
    """Overlay CandidateConfig from PolicyPack.metadata when present."""
    base = default_candidate_config()
    if not metadata:
        return base
    return CandidateConfig(
        comm_window_start_hour=int(
            metadata.get("comm_window_start_hour", base.comm_window_start_hour)
        ),
        comm_window_end_hour=int(metadata.get("comm_window_end_hour", base.comm_window_end_hour)),
        max_retry_attempts=int(metadata.get("max_retry_attempts", base.max_retry_attempts)),
        contact_cap_per_customer=int(
            metadata.get("contact_cap_per_customer", base.contact_cap_per_customer)
        ),
        contact_cap_7d=int(metadata.get("contact_cap_7d", base.contact_cap_7d)),
        incentive_max_pct_of_v=float(
            metadata.get("incentive_max_pct_of_v", base.incentive_max_pct_of_v)
        ),
        incentive_max_paise=int(metadata.get("incentive_max_paise", base.incentive_max_paise)),
        approval_value_threshold_paise=int(
            metadata.get("approval_value_threshold_paise", base.approval_value_threshold_paise)
        ),
        scheduled_retry_delay_minutes=int(
            metadata.get("scheduled_retry_delay_minutes", base.scheduled_retry_delay_minutes)
        ),
        issuer_downtime_delay_minutes=int(
            metadata.get("issuer_downtime_delay_minutes", base.issuer_downtime_delay_minutes)
        ),
        cooldown_minutes=int(metadata.get("cooldown_minutes", base.cooldown_minutes)),
        generator_version=base.generator_version,
    )
