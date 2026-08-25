"""
Latent behavioral traits — ORACLE PARTITION ONLY.

Decision-path modules must not import this module (AI-6, DS-11).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LatentTraits:
    """Hidden customer traits influencing oracle outcomes (docs/19 §3)."""

    customer_id: str
    intent_to_pay: float
    responsiveness_email: float
    responsiveness_sms: float
    price_sensitivity: float
    annoyance_threshold: int
    instrument_health: float
    attention_delay_minutes: int
    fatigue_sensitivity: float

    def to_dict(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "intent_to_pay": self.intent_to_pay,
            "responsiveness_email": self.responsiveness_email,
            "responsiveness_sms": self.responsiveness_sms,
            "price_sensitivity": self.price_sensitivity,
            "annoyance_threshold": self.annoyance_threshold,
            "instrument_health": self.instrument_health,
            "attention_delay_minutes": self.attention_delay_minutes,
            "fatigue_sensitivity": self.fatigue_sensitivity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LatentTraits:
        return cls(**data)
