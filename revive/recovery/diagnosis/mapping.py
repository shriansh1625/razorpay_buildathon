"""Deterministic raw failure-reason → cause taxonomy mapping (RR-FUNC-011)."""

from __future__ import annotations

from revive.domain.enums import CauseCode

# Pure lookup — unmapped values route to UNCLASSIFIED, never a new code.
RAW_REASON_TO_CAUSE: dict[str, CauseCode] = {
    "INSUFFICIENT_FUNDS": CauseCode.INSUFFICIENT_FUNDS,
    "INSUFFICIENT_BALANCE": CauseCode.INSUFFICIENT_FUNDS,
    "EXPIRED_CARD": CauseCode.CARD_EXPIRED,
    "CARD_EXPIRED": CauseCode.CARD_EXPIRED,
    "ISSUER_DOWN": CauseCode.ISSUER_DOWNTIME,
    "NETWORK_ERROR": CauseCode.GATEWAY_TIMEOUT,
    "GATEWAY_ERROR": CauseCode.GATEWAY_ERROR,
    "GATEWAY_TIMEOUT": CauseCode.GATEWAY_TIMEOUT,
    "INVALID_INSTRUMENT": CauseCode.INSTRUMENT_INVALID,
    "INSTRUMENT_BLOCKED": CauseCode.INSTRUMENT_BLOCKED,
    "DECLINED": CauseCode.DO_NOT_HONOUR_AMBIGUOUS,
    "DO_NOT_HONOUR": CauseCode.DO_NOT_HONOUR_AMBIGUOUS,
    "CARD_DECLINED": CauseCode.ISSUER_DECLINE_SOFT,
    "ISSUER_DECLINE": CauseCode.ISSUER_DECLINE_SOFT,
    "AUTHENTICATION_ERROR": CauseCode.AUTH_SYSTEM_FAILURE,
    "AUTH_TIMEOUT": CauseCode.AUTH_TIMEOUT,
    "AUTH_ABANDONED": CauseCode.AUTH_ABANDONED_BY_CUSTOMER,
}


def map_raw_reason(raw: str | None) -> CauseCode:
    if not raw:
        return CauseCode.UNCLASSIFIED
    normalized = raw.strip().upper()
    return RAW_REASON_TO_CAUSE.get(normalized, CauseCode.UNCLASSIFIED)
