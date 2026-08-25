"""Integer paise money type (RR-NFR-001). No floats in money paths."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, order=True)
class Paise:
    """Non-negative integer amount in paise."""

    amount: int

    def __post_init__(self) -> None:
        if not isinstance(self.amount, int):
            raise TypeError(f"Paise.amount must be int, got {type(self.amount).__name__}")
        if isinstance(self.amount, bool):
            raise TypeError("Paise.amount must not be bool")
        if self.amount < 0:
            raise ValueError(f"Paise cannot be negative: {self.amount}")

    def __add__(self, other: Paise) -> Paise:
        return Paise(self.amount + other.amount)

    def __sub__(self, other: Paise) -> Paise:
        result = self.amount - other.amount
        if result < 0:
            raise ValueError(f"Paise subtraction underflow: {self.amount} - {other.amount}")
        return Paise(result)

    def __mul__(self, factor: int) -> Paise:
        if not isinstance(factor, int) or isinstance(factor, bool):
            raise TypeError("Paise multiplication factor must be int")
        if factor < 0:
            raise ValueError("Paise multiplication factor must be non-negative")
        return Paise(self.amount * factor)

    def __str__(self) -> str:
        return f"{self.amount} paise"

    @classmethod
    def zero(cls) -> Paise:
        return cls(0)


def paise_from_rupees(rupees: int, paise_fraction: int = 0) -> Paise:
    """Convert whole rupees (+ optional paise fraction) to Paise."""
    if not isinstance(rupees, int) or isinstance(rupees, bool):
        raise TypeError("rupees must be int")
    if not isinstance(paise_fraction, int) or isinstance(paise_fraction, bool):
        raise TypeError("paise_fraction must be int")
    if rupees < 0 or paise_fraction < 0 or paise_fraction >= 100:
        raise ValueError("invalid rupee/paise values")
    return Paise(rupees * 100 + paise_fraction)


def rupees_from_paise(paise: Paise) -> tuple[int, int]:
    """Split paise into (whole_rupees, paise_remainder)."""
    return divmod(paise.amount, 100)
