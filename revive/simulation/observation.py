"""Observation interface — observable state only, no hidden oracle fields."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import Any

from revive.simulation.world import SyntheticWorld

HIDDEN_KEYS = frozenset(
    {
        "intent_to_pay",
        "responsiveness_email",
        "responsiveness_sms",
        "price_sensitivity",
        "annoyance_threshold",
        "instrument_health",
        "attention_delay_minutes",
        "fatigue_sensitivity",
        "per_action_response",
        "recovers_naturally",
        "natural_recovery_at_micros",
        "fatigue_curve",
        "latent_traits",
        "oracle_counterfactual_paise",
    }
)


@dataclass(frozen=True, slots=True)
class ObservableWorldView:
    """Serializable observable snapshot for future decision pipeline."""

    merchants: tuple[dict[str, Any], ...]
    customers: tuple[dict[str, Any], ...]
    instruments: tuple[dict[str, Any], ...]
    orders: tuple[dict[str, Any], ...]
    transactions: tuple[dict[str, Any], ...]
    checkout_sessions: tuple[dict[str, Any], ...]
    subscriptions: tuple[dict[str, Any], ...]
    mandates: tuple[dict[str, Any], ...]
    invoices: tuple[dict[str, Any], ...]
    opportunities: tuple[dict[str, Any], ...]
    signals: tuple[dict[str, Any], ...]
    degradation_windows: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "merchants": list(self.merchants),
            "customers": list(self.customers),
            "instruments": list(self.instruments),
            "orders": list(self.orders),
            "transactions": list(self.transactions),
            "checkout_sessions": list(self.checkout_sessions),
            "subscriptions": list(self.subscriptions),
            "mandates": list(self.mandates),
            "invoices": list(self.invoices),
            "opportunities": list(self.opportunities),
            "signals": list(self.signals),
            "degradation_windows": list(self.degradation_windows),
        }

    def contains_hidden_keys(self) -> list[str]:
        found: list[str] = []
        for key in self._walk_keys(self.as_dict()):
            if key in HIDDEN_KEYS:
                found.append(key)
        return found

    @staticmethod
    def _walk_keys(obj: Any, prefix: str = "") -> list[str]:
        keys: list[str] = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                keys.append(str(k))
                keys.extend(ObservableWorldView._walk_keys(v, prefix))
        elif isinstance(obj, list):
            for item in obj:
                keys.extend(ObservableWorldView._walk_keys(item, prefix))
        return keys


def _record_dict(record: Any) -> dict[str, Any]:
    if is_dataclass(record):
        data = {}
        for field in fields(record):
            value = getattr(record, field.name)
            if hasattr(value, "value"):
                data[field.name] = value.value
            else:
                data[field.name] = value
        return data
    data = {}
    for key, value in vars(record).items():
        if hasattr(value, "value"):
            data[key] = value.value
        else:
            data[key] = value
    return data


def get_observable_state(world: SyntheticWorld) -> ObservableWorldView:
    """Return observable world state — never latent traits or oracle truth."""
    return ObservableWorldView(
        merchants=tuple(_record_dict(m) for m in world.merchants),
        customers=tuple(_record_dict(c) for c in world.customers),
        instruments=tuple(_record_dict(i) for i in world.instruments),
        orders=tuple(_record_dict(o) for o in world.orders),
        transactions=tuple(_record_dict(t) for t in world.transactions),
        checkout_sessions=tuple(_record_dict(s) for s in world.checkout_sessions),
        subscriptions=tuple(_record_dict(s) for s in world.subscriptions),
        mandates=tuple(_record_dict(m) for m in world.mandates),
        invoices=tuple(_record_dict(i) for i in world.invoices),
        opportunities=tuple(_record_dict(o) for o in world.opportunities),
        signals=tuple(_record_dict(s) for s in world.signals),
        degradation_windows=tuple(
            {
                "cohort_ref": w.cohort_ref,
                "start_micros": w.start_micros,
                "end_micros": w.end_micros,
                "severity": w.severity,
            }
            for w in world.degradation_windows
        ),
    )
