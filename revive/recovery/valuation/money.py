"""Integer money conversion — banker's rounding once at persistence (RR-NFR-002)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN

_ONE = Decimal("1")


def bankers_round_paise(value: float) -> int:
    """Convert a float rupee-equivalent expression to integer paise."""
    return int(Decimal(str(value)).quantize(_ONE, rounding=ROUND_HALF_EVEN))
