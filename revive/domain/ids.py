"""Entity identifiers — `<prefix>_<ULID>` (docs/17 § header)."""

from __future__ import annotations

import secrets
import string
from dataclasses import dataclass
from typing import Final

# Crockford base32 without I, L, O, U — ULID-compatible alphabet subset for M1.
_ULID_ALPHABET: Final = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


@dataclass(frozen=True, slots=True)
class EntityId:
    prefix: str
    value: str

    def __post_init__(self) -> None:
        if not self.prefix or "_" in self.prefix:
            raise ValueError(f"invalid id prefix: {self.prefix!r}")
        if len(self.value) != 26:
            raise ValueError(f"ULID component must be 26 chars, got {len(self.value)}")

    def __str__(self) -> str:
        return f"{self.prefix}_{self.value}"


def _random_ulid_component() -> str:
    return "".join(secrets.choice(_ULID_ALPHABET) for _ in range(26))


def new_id(prefix: str) -> EntityId:
    return EntityId(prefix=prefix, value=_random_ulid_component())
