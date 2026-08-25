"""Deterministic OFFICIAL_BENCHMARK_CONFIG_HASH — M13 §7."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from revive.benchmark.official.config import OfficialBenchmarkConfig


def frozen_experiment_reference_hash(config: OfficialBenchmarkConfig) -> str:
    """
    Hash of the sealed experimental configuration excluding seed matrix and run id.

    Stable across preflight (1 seed) and full official (20 seeds) runs.
    """
    payload: dict[str, Any] = {
        "benchmark_version": config.benchmark_version,
        "generator_version": config.generator_version,
        "generator_template": {
            "merchant_count": config.generator_config.merchant_count,
            "customer_count": config.generator_config.customer_count,
            "opportunity_count": config.generator_config.opportunity_count,
            "simulation_window_days": config.simulation_horizon_days,
            "cycle_interval_minutes": config.cycle_length_minutes,
            "inject_signal_faults": config.generator_config.inject_signal_faults,
            "inject_adversarial_cases": config.generator_config.inject_adversarial_cases,
            "privacy_canary_count": config.generator_config.privacy_canary_count,
        },
        "PolicyPack_version": config.policy_pack_version,
        "PolicyPack_hash": config.policy_pack_hash,
        "PolicyPack_status": config.policy_pack_status,
        "epsilon": config.epsilon_paise,
        "B1_schedule_version": config.b1_schedule_version,
        "predictor_version": config.predictor_version,
        "allocator_version": config.allocator_version,
        "metric_version": config.metric_version,
        "simulation_horizon": config.simulation_horizon_days,
        "cycle_length": config.cycle_length_minutes,
        "profile_set": [p.value for p in config.profile_set],
        "approver_model_version": config.approver_model_version,
        "llm_mode": config.llm_mode,
        "allocator_mode": config.allocator_mode,
        "policy_set": list(config.policy_set),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def official_benchmark_config_hash(config: OfficialBenchmarkConfig) -> str:
    """Hash uniquely representing the frozen benchmark configuration."""
    payload: dict[str, Any] = {
        "benchmark_id": config.benchmark_id,
        "benchmark_version": config.benchmark_version,
        "generator_version": config.generator_version,
        "generator_template": {
            "merchant_count": config.generator_config.merchant_count,
            "customer_count": config.generator_config.customer_count,
            "opportunity_count": config.generator_config.opportunity_count,
            "simulation_window_days": config.simulation_horizon_days,
            "cycle_interval_minutes": config.cycle_length_minutes,
            "inject_signal_faults": config.generator_config.inject_signal_faults,
            "inject_adversarial_cases": config.generator_config.inject_adversarial_cases,
            "privacy_canary_count": config.generator_config.privacy_canary_count,
        },
        "PolicyPack_version": config.policy_pack_version,
        "PolicyPack_hash": config.policy_pack_hash,
        "PolicyPack_status": config.policy_pack_status,
        "epsilon": config.epsilon_paise,
        "B1_schedule_version": config.b1_schedule_version,
        "predictor_version": config.predictor_version,
        "allocator_version": config.allocator_version,
        "metric_version": config.metric_version,
        "simulation_horizon": config.simulation_horizon_days,
        "cycle_length": config.cycle_length_minutes,
        "seed_set": list(config.seed_set),
        "profile_set": [p.value for p in config.profile_set],
        "approver_model_version": config.approver_model_version,
        "llm_mode": config.llm_mode,
        "allocator_mode": config.allocator_mode,
        "policy_set": list(config.policy_set),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()
