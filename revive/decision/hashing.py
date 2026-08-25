"""Deterministic decision IDs and configuration hashing."""

from __future__ import annotations

import hashlib
import json

from revive.allocation.config import AllocatorConfig
from revive.allocation.models import ResourceCapacities
from revive.config.policy_pack import PolicyPack
from revive.domain.enums import ActionCode


def decision_id_for(
    cycle_id: str,
    opportunity_id: str,
    allocation_hash: str,
    configuration_hash: str,
) -> str:
    digest = hashlib.sha256(
        f"{cycle_id}:{opportunity_id}:{allocation_hash}:{configuration_hash}".encode()
    ).hexdigest()
    return f"dec_{digest[:26]}"


def reservation_id_for(decision_id: str, resource_key: str) -> str:
    digest = hashlib.sha256(f"{decision_id}:{resource_key}".encode()).hexdigest()
    return f"res_{digest[:26]}"


def idempotency_key_for(
    opportunity_id: str,
    action_code: ActionCode,
    attempt_seq: int,
    cycle_id: str,
) -> str:
    digest = hashlib.sha256(
        f"{opportunity_id}:{action_code.value}:{attempt_seq}:{cycle_id}".encode()
    ).hexdigest()
    return f"idem_{digest[:32]}"


def capacities_digest(capacities: ResourceCapacities) -> str:
    payload = {
        "retry_slots": capacities.retry_slots,
        "message_capacity": capacities.message_capacity,
        "voice_minutes": capacities.voice_minutes,
        "human_review_slots": capacities.human_review_slots,
        "incentive_budget_paise": capacities.incentive_budget_paise,
        "contact_allowance_per_customer": capacities.contact_allowance_per_customer,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def configuration_hash(
    policy: PolicyPack,
    allocator_config: AllocatorConfig,
    valuation_versions: tuple[str, ...],
    strategy_versions: tuple[str, ...],
    capacities: ResourceCapacities,
) -> str:
    payload = {
        "policy_hash": policy.config_hash(),
        "policy_version": policy.version,
        "policy_status": policy.status.value,
        "allocator_version": allocator_config.allocator_version,
        "allocator_k_max": allocator_config.k_max,
        "allocator_step_scale": allocator_config.step_scale,
        "valuation_versions": sorted(valuation_versions),
        "strategy_versions": sorted(strategy_versions),
        "capacities_digest": capacities_digest(capacities),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
