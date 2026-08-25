"""Simulation-specific enumerations."""

from __future__ import annotations

from enum import Enum


class GenerationProfile(str, Enum):
    """Named parameter sets from docs/19 §2.3."""

    BALANCED = "BALANCED"
    HIGH_NATURAL = "HIGH_NATURAL"
    SCARCE = "SCARCE"
    ABUNDANT = "ABUNDANT"
    HOSTILE = "HOSTILE"
    DEGRADED = "DEGRADED"


class CheckoutStage(str, Enum):
    LANDING = "LANDING"
    CART = "CART"
    CHECKOUT = "CHECKOUT"
    PAYMENT_INIT = "PAYMENT_INIT"
    PAYMENT_ATTEMPT = "PAYMENT_ATTEMPT"
    SUCCESS = "SUCCESS"


class PaymentFailureReason(str, Enum):
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    EXPIRED_CARD = "EXPIRED_CARD"
    ISSUER_DOWN = "ISSUER_DOWN"
    NETWORK_ERROR = "NETWORK_ERROR"
    INVALID_INSTRUMENT = "INVALID_INSTRUMENT"
    DECLINED = "DECLINED"


class OutcomeKind(str, Enum):
    """Oracle-resolved outcome classes for simulation (M2)."""

    RECOVERED = "RECOVERED"
    NOT_RECOVERED = "NOT_RECOVERED"
    PARTIALLY_RECOVERED = "PARTIALLY_RECOVERED"
    NATURAL_RECOVERY = "NATURAL_RECOVERY"
    EXPIRED = "EXPIRED"
    CUSTOMER_DECLINED = "CUSTOMER_DECLINED"
    ACTION_FAILED = "ACTION_FAILED"


class AdapterResult(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    REJECTED_BY_PROVIDER = "REJECTED_BY_PROVIDER"
    TIMEOUT_UNKNOWN = "TIMEOUT_UNKNOWN"
