"""PolicyPack skeleton — FOUNDATION ONLY, NOT FROZEN for benchmark claims."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from revive.errors.exceptions import ConfigurationError


class PolicyPackStatus(str, Enum):
    DRAFT = "DRAFT"
    SEALED = "SEALED"


@dataclass(frozen=True, slots=True)
class PolicyPack:
    """
    Versioned policy configuration.

    M1: structure only. ε (epsilon_paise) is PROVISIONAL — see ADR-011.
    Benchmark claims require a SEALED pack with config_hash recorded before runs.
    """

    version: str
    status: PolicyPackStatus
    epsilon_paise: int
    profile: str = "BALANCED"
    gate_sequence: tuple[str, ...] = (
        "G1",
        "G2",
        "G3",
        "G4",
        "G5",
        "G6",
        "G7",
        "G8",
        "G9",
        "G10",
        "G11",
        "G12",
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.epsilon_paise < 0:
            raise ValueError("epsilon_paise must be non-negative")
        if self.status == PolicyPackStatus.SEALED and not self.version:
            raise ConfigurationError("sealed policy pack requires version")

    @property
    def is_frozen_for_benchmark(self) -> bool:
        return self.status == PolicyPackStatus.SEALED

    def config_hash(self) -> str:
        payload = {
            "version": self.version,
            "epsilon_paise": self.epsilon_paise,
            "profile": self.profile,
            "gate_sequence": list(self.gate_sequence),
            "metadata": self.metadata,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


def policy_pack_to_frozen_payload(pack: PolicyPack) -> dict[str, Any]:
    """Immutable serializable representation for cross-process worker propagation."""
    return {
        "version": pack.version,
        "status": pack.status.value,
        "epsilon_paise": pack.epsilon_paise,
        "profile": pack.profile,
        "gate_sequence": list(pack.gate_sequence),
        "metadata": dict(pack.metadata),
        "config_hash": pack.config_hash(),
    }


def policy_pack_from_frozen_payload(
    payload: dict[str, Any],
    *,
    expected_hash: str | None = None,
    require_sealed: bool = False,
) -> PolicyPack:
    """Reconstruct PolicyPack from frozen payload with fail-closed validation."""
    if not payload:
        raise ValueError("policy pack payload is empty")
    required = ("version", "status", "epsilon_paise", "config_hash")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"policy pack payload missing fields: {', '.join(missing)}")

    status = PolicyPackStatus(str(payload["status"]))
    if require_sealed and status != PolicyPackStatus.SEALED:
        raise ValueError(
            f"official worker requires SEALED PolicyPack (got status={status.value})"
        )

    pack = PolicyPack(
        version=str(payload["version"]),
        status=status,
        epsilon_paise=int(payload["epsilon_paise"]),
        profile=str(payload.get("profile", "BALANCED")),
        gate_sequence=tuple(payload.get("gate_sequence") or ()),
        metadata=dict(payload.get("metadata") or {}),
    )
    computed_hash = pack.config_hash()
    payload_hash = str(payload["config_hash"])
    if computed_hash != payload_hash:
        raise ValueError(
            "policy pack hash mismatch: "
            f"payload={payload_hash} computed={computed_hash}"
        )
    if expected_hash is not None and computed_hash != expected_hash:
        raise ValueError(
            "policy pack hash mismatch: "
            f"expected={expected_hash} computed={computed_hash}"
        )
    return pack


def default_draft_policy_pack() -> PolicyPack:
    """
    Provisional defaults for development only.

    epsilon_paise=0 follows OQ-01 PROPOSED default; NOT for official benchmark.
    """
    return PolicyPack(
        version="pol_m1_draft",
        status=PolicyPackStatus.DRAFT,
        epsilon_paise=0,
        profile="BALANCED",
        metadata={"source": "M1-foundation", "frozen": False},
    )


def official_sealed_policy_pack() -> PolicyPack:
    """
    M13.10 sealed PolicyPack — ADR-011 ACCEPTED, ε=100 paise.

    Immutable for official benchmark claims. Mutations require a new version.
    """
    return PolicyPack(
        version="pol_m13_official_v1",
        status=PolicyPackStatus.SEALED,
        epsilon_paise=100,
        profile="BALANCED",
        metadata={
            "source": "M13.10-official-freeze",
            "frozen": True,
            "adr_011": "ACCEPTED",
            "approval_value_threshold_paise": 500000,
            "approval_uncertainty_ratio": 0.5,
        },
    )
