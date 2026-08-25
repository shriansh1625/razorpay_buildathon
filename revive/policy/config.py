"""Policy rule defaults — PROVISIONAL until PolicyPack sealed."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

AUTHORIZATION_VERSION = "0.10.0-m10"

# PROVISIONAL — docs/13 §10, docs/14 §10.
DEFAULT_MAX_CONTACTS_PER_CUSTOMER = 2
DEFAULT_MAX_RETRIES_PER_OPPORTUNITY = 3
DEFAULT_COMMUNICATION_START_HOUR = 9
DEFAULT_COMMUNICATION_END_HOUR = 19
DEFAULT_MAX_INCENTIVE_PCT = 5.0
DEFAULT_APPROVAL_VALUE_THRESHOLD_PAISE = 8_000_000  # ₹80,000
DEFAULT_APPROVAL_UNCERTAINTY_RATIO = 0.5
DEFAULT_OPPORTUNITY_CONTACT_CAP = 3
DEFAULT_SR07_CONSECUTIVE_CYCLES = 3
DEFAULT_AMOUNT_SANITY_MAX_PAISE = 100_000_000
DEFAULT_AUTHORIZATION_TTL_MICROS = 15 * 60 * 1_000_000
DEFAULT_APPROVAL_VALIDITY_MICROS = 24 * 60 * 60 * 1_000_000

DEFAULT_APPROVAL_REQUIRED_ACTIONS = frozenset({"A10", "A11", "A12", "A14"})

TIER_INCENTIVE_PCT: dict[str, float] = {
    "TIER_0": 0.0,
    "TIER_1": 2.0,
    "TIER_2": 5.0,
    "TIER_3": 10.0,
}


@dataclass(frozen=True, slots=True)
class PolicyRules:
    max_contacts_per_customer: int = DEFAULT_MAX_CONTACTS_PER_CUSTOMER
    max_retries_per_opportunity: int = DEFAULT_MAX_RETRIES_PER_OPPORTUNITY
    communication_start_hour: int = DEFAULT_COMMUNICATION_START_HOUR
    communication_end_hour: int = DEFAULT_COMMUNICATION_END_HOUR
    max_incentive_pct: float = DEFAULT_MAX_INCENTIVE_PCT
    approval_value_threshold_paise: int = DEFAULT_APPROVAL_VALUE_THRESHOLD_PAISE
    approval_uncertainty_ratio: float = DEFAULT_APPROVAL_UNCERTAINTY_RATIO
    opportunity_contact_cap: int = DEFAULT_OPPORTUNITY_CONTACT_CAP
    sr07_consecutive_cycles: int = DEFAULT_SR07_CONSECUTIVE_CYCLES
    amount_sanity_max_paise: int = DEFAULT_AMOUNT_SANITY_MAX_PAISE
    authorization_ttl_micros: int = DEFAULT_AUTHORIZATION_TTL_MICROS
    approval_required_actions: frozenset[str] = DEFAULT_APPROVAL_REQUIRED_ACTIONS

    @classmethod
    def from_policy_metadata(cls, metadata: dict[str, Any]) -> PolicyRules:
        rules = metadata.get("policy_rules", {})
        return PolicyRules(
            max_contacts_per_customer=int(
                rules.get("max_contacts_per_customer", DEFAULT_MAX_CONTACTS_PER_CUSTOMER)
            ),
            max_retries_per_opportunity=int(
                rules.get("max_retries_per_opportunity", DEFAULT_MAX_RETRIES_PER_OPPORTUNITY)
            ),
            communication_start_hour=int(
                rules.get("communication_start_hour", DEFAULT_COMMUNICATION_START_HOUR)
            ),
            communication_end_hour=int(
                rules.get("communication_end_hour", DEFAULT_COMMUNICATION_END_HOUR)
            ),
            max_incentive_pct=float(rules.get("max_incentive_pct", DEFAULT_MAX_INCENTIVE_PCT)),
            approval_value_threshold_paise=int(
                rules.get(
                    "approval_value_threshold_paise",
                    DEFAULT_APPROVAL_VALUE_THRESHOLD_PAISE,
                )
            ),
            approval_uncertainty_ratio=float(
                rules.get("approval_uncertainty_ratio", DEFAULT_APPROVAL_UNCERTAINTY_RATIO)
            ),
            opportunity_contact_cap=int(
                rules.get("opportunity_contact_cap", DEFAULT_OPPORTUNITY_CONTACT_CAP)
            ),
            sr07_consecutive_cycles=int(
                rules.get("sr07_consecutive_cycles", DEFAULT_SR07_CONSECUTIVE_CYCLES)
            ),
            amount_sanity_max_paise=int(
                rules.get("amount_sanity_max_paise", DEFAULT_AMOUNT_SANITY_MAX_PAISE)
            ),
            authorization_ttl_micros=int(
                rules.get("authorization_ttl_micros", DEFAULT_AUTHORIZATION_TTL_MICROS)
            ),
            approval_required_actions=frozenset(
                rules.get("approval_required_actions", list(DEFAULT_APPROVAL_REQUIRED_ACTIONS))
            ),
        )


def default_policy_rules() -> PolicyRules:
    return PolicyRules()
