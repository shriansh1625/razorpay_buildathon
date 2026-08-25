"""Addressability classification (docs/12 §5, RR-FUNC-007)."""

from __future__ import annotations

from revive.domain.enums import AgeingBucket, NonAddressableReason, OpportunityState, RiskClass


def ageing_bucket_days(age_days: int) -> AgeingBucket:
    if age_days <= 15:
        return AgeingBucket.D0_15
    if age_days <= 30:
        return AgeingBucket.D16_30
    if age_days <= 60:
        return AgeingBucket.D31_60
    if age_days <= 90:
        return AgeingBucket.D61_90
    return AgeingBucket.D90_PLUS


def classify_addressability(
    *,
    risk_class: RiskClass,
    value_at_risk_paise: int,
    customer_id: str | None,
    window_expired: bool,
    disputed: bool = False,
    written_off: bool = False,
    already_settled: bool = False,
    amount_determinable: bool = True,
) -> tuple[bool, NonAddressableReason | None, OpportunityState]:
    if not amount_determinable:
        return False, NonAddressableReason.AMOUNT_NOT_DETERMINABLE, OpportunityState.NOT_ADDRESSABLE
    if value_at_risk_paise <= 0:
        if already_settled:
            return False, NonAddressableReason.ALREADY_SETTLED, OpportunityState.NOT_ADDRESSABLE
        if written_off:
            return False, NonAddressableReason.WRITTEN_OFF, OpportunityState.NOT_ADDRESSABLE
        return False, NonAddressableReason.ZERO_AMOUNT, OpportunityState.NOT_ADDRESSABLE
    if disputed:
        return False, NonAddressableReason.DISPUTED, OpportunityState.NOT_ADDRESSABLE
    if window_expired:
        return False, NonAddressableReason.WINDOW_EXPIRED, OpportunityState.NOT_ADDRESSABLE
    if risk_class == RiskClass.CHECKOUT_ABANDONMENT and not customer_id:
        return False, NonAddressableReason.ANONYMOUS_CHECKOUT, OpportunityState.NOT_ADDRESSABLE
    return True, None, OpportunityState.DETECTED
