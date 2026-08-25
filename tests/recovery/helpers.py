"""Shared ObservableWorldView builders for Sentinel tests."""

from __future__ import annotations

from typing import Any

from revive.simulation.observation import ObservableWorldView

_EMPTY: tuple = ()


def view(**overrides: Any) -> ObservableWorldView:
    kwargs = {
        "merchants": (
            {
                "merchant_id": "mer_1",
                "name_token": "m",
                "timezone": "Asia/Kolkata",
                "net_retention_factor": 1.0,
                "policy_pack_ref": "pol",
            },
        ),
        "customers": (
            {
                "customer_id": "cust_1",
                "customer_ref": "c1",
                "merchant_id": "mer_1",
                "segment": "NEW",
                "tenure_band": "LT_3M",
                "value_band": "MID",
                "prior_self_recovery_rate": 0.2,
            },
        ),
        "instruments": _EMPTY,
        "orders": _EMPTY,
        "transactions": _EMPTY,
        "checkout_sessions": _EMPTY,
        "subscriptions": _EMPTY,
        "mandates": _EMPTY,
        "invoices": _EMPTY,
        "opportunities": _EMPTY,
        "signals": _EMPTY,
        "degradation_windows": _EMPTY,
    }
    kwargs.update(overrides)
    return ObservableWorldView(**kwargs)
