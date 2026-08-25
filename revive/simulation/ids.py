"""Deterministic entity IDs for reproducible generation."""

from __future__ import annotations

import hashlib


_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def deterministic_id(prefix: str, material: str) -> str:
    """SHA-256 → Crockford base32 ULID component — same mapping as hex-pair decode."""
    digest = hashlib.sha256(f"{prefix}:{material}".encode()).digest()
    value = "".join(_CROCKFORD[digest[i] & 31] for i in range(26))
    return f"{prefix}_{value}"
