"""Immutable official benchmark configuration — docs/20, M13 §6."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from revive.allocation.config import ALLOCATOR_VERSION
from revive.benchmark.config import B1_RETRY_SCHEDULE
from revive.measurement.config import MEASUREMENT_VERSION
from revive.recovery.valuation.config import (
    BENCHMARK_STRATEGY_VERSION,
    STRATEGY_VERSION,
    VALUATION_VERSION,
)
from revive.simulation.config import GENERATOR_VERSION, GeneratorConfig
from revive.simulation.types import GenerationProfile
from revive.benchmark.official.freeze_constants import (
    OFFICIAL_BENCHMARK_ID,
    OFFICIAL_B1_SCHEDULE_VERSION,
    OFFICIAL_APPROVER_VERSION,
    OFFICIAL_CUSTOMER_COUNT,
    OFFICIAL_CYCLE_LENGTH_MINUTES,
    OFFICIAL_HORIZON_DAYS,
    OFFICIAL_OPPORTUNITY_COUNT,
    PREFLIGHT_BENCHMARK_ID,
)

BENCHMARK_VERSION = "0.13.0-m13"
METRIC_VERSION = MEASUREMENT_VERSION
PREDICTOR_VERSION_OFFICIAL = f"{VALUATION_VERSION}:{BENCHMARK_STRATEGY_VERSION}"
PREDICTOR_VERSION_DEV = f"{VALUATION_VERSION}:{STRATEGY_VERSION}"
PREDICTOR_VERSION = PREDICTOR_VERSION_OFFICIAL  # legacy alias
ALLOCATOR_VERSION_REF = ALLOCATOR_VERSION
APPROVER_MODEL_VERSION = OFFICIAL_APPROVER_VERSION
B1_SCHEDULE_VERSION = OFFICIAL_B1_SCHEDULE_VERSION
LLM_MODE_OFFICIAL = "LLM_OFF"
ALLOCATOR_MODE_OFFICIAL = "LAGRANGIAN"

# PROPOSED official scale — ADR-012 pending; recorded in config, not executed until freeze.
OFFICIAL_SEED_COUNT = 20
OFFICIAL_PROFILE_SET: tuple[GenerationProfile, ...] = (
    GenerationProfile.BALANCED,
    GenerationProfile.HIGH_NATURAL,
    GenerationProfile.SCARCE,
    GenerationProfile.ABUNDANT,
    GenerationProfile.HOSTILE,
    GenerationProfile.DEGRADED,
)

OFFICIAL_SEED_SET: tuple[int, ...] = tuple(range(1, OFFICIAL_SEED_COUNT + 1))


class BenchmarkMode(str, Enum):
    OFFICIAL = "OFFICIAL"
    DEVELOPMENT = "DEVELOPMENT"
    PREFLIGHT = "PREFLIGHT"


@dataclass(frozen=True, slots=True)
class OfficialBenchmarkConfig:
    """Frozen benchmark configuration representation — M13 §6."""

    benchmark_id: str
    benchmark_version: str
    generator_version: str
    generator_config: GeneratorConfig
    policy_pack_version: str
    policy_pack_hash: str
    policy_pack_status: str
    epsilon_paise: int
    b1_schedule_version: str
    predictor_version: str
    allocator_version: str
    metric_version: str
    simulation_horizon_days: int
    cycle_length_minutes: int
    seed_set: tuple[int, ...]
    profile_set: tuple[GenerationProfile, ...]
    approver_model_version: str
    llm_mode: str
    allocator_mode: str
    policy_set: tuple[str, ...]
    code_revision: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "benchmark_version": self.benchmark_version,
            "generator_version": self.generator_version,
            "generator_config": self.generator_config.config_hash(),
            "generator_config_detail": {
                "seed": self.generator_config.seed,
                "profile": self.generator_config.profile.value,
                "merchant_count": self.generator_config.merchant_count,
                "customer_count": self.generator_config.customer_count,
                "opportunity_count": self.generator_config.opportunity_count,
                "simulation_window_days": self.generator_config.simulation_window_days,
                "cycle_interval_minutes": self.generator_config.cycle_interval_minutes,
            },
            "PolicyPack_version": self.policy_pack_version,
            "PolicyPack_hash": self.policy_pack_hash,
            "PolicyPack_status": self.policy_pack_status,
            "epsilon": self.epsilon_paise,
            "B1_schedule_version": self.b1_schedule_version,
            "predictor_version": self.predictor_version,
            "allocator_version": self.allocator_version,
            "metric_version": self.metric_version,
            "simulation_horizon": self.simulation_horizon_days,
            "cycle_length": self.cycle_length_minutes,
            "seed_set": list(self.seed_set),
            "profile_set": [p.value for p in self.profile_set],
            "approver_model_version": self.approver_model_version,
            "llm_mode": self.llm_mode,
            "allocator_mode": self.allocator_mode,
            "policy_set": list(self.policy_set),
            "code_revision": self.code_revision,
            "b1_schedule_classes": len(B1_RETRY_SCHEDULE),
        }


def _code_revision() -> str:
    import subprocess

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _base_generator_config(seed: int, profile: GenerationProfile) -> GeneratorConfig:
    """Official frozen generator scale — ADR-012 ACCEPTED (M13.10)."""
    return GeneratorConfig(
        seed=seed,
        profile=profile,
        merchant_count=1,
        customer_count=OFFICIAL_CUSTOMER_COUNT,
        opportunity_count=OFFICIAL_OPPORTUNITY_COUNT,
        simulation_window_days=OFFICIAL_HORIZON_DAYS,
        cycle_interval_minutes=OFFICIAL_CYCLE_LENGTH_MINUTES,
        inject_signal_faults=True,
        inject_adversarial_cases=False,
        privacy_canary_count=3,
    )


def official_benchmark_config(
    *,
    policy_pack,
    benchmark_id: str = OFFICIAL_BENCHMARK_ID,
) -> OfficialBenchmarkConfig:
    """Immutable official benchmark configuration — requires SEALED PolicyPack."""
    if not policy_pack.is_frozen_for_benchmark:
        raise ValueError(
            "official_benchmark_config requires a SEALED PolicyPack "
            f"(got status={policy_pack.status.value})"
        )
    base = _base_generator_config(seed=1, profile=GenerationProfile.BALANCED)
    return OfficialBenchmarkConfig(
        benchmark_id=benchmark_id,
        benchmark_version=BENCHMARK_VERSION,
        generator_version=GENERATOR_VERSION,
        generator_config=base,
        policy_pack_version=policy_pack.version,
        policy_pack_hash=policy_pack.config_hash(),
        policy_pack_status=policy_pack.status.value,
        epsilon_paise=policy_pack.epsilon_paise,
        b1_schedule_version=B1_SCHEDULE_VERSION,
        predictor_version=PREDICTOR_VERSION_OFFICIAL,
        allocator_version=ALLOCATOR_VERSION_REF,
        metric_version=METRIC_VERSION,
        simulation_horizon_days=base.simulation_window_days,
        cycle_length_minutes=base.cycle_interval_minutes,
        seed_set=OFFICIAL_SEED_SET,
        profile_set=OFFICIAL_PROFILE_SET,
        approver_model_version=APPROVER_MODEL_VERSION,
        llm_mode=LLM_MODE_OFFICIAL,
        allocator_mode=ALLOCATOR_MODE_OFFICIAL,
        policy_set=("B0", "B1", "B2", "B3", "REVIVE"),
        code_revision=_code_revision(),
    )


def preflight_benchmark_config(
    *,
    policy_pack,
    seeds: tuple[int, ...] = (1,),
    benchmark_id: str = PREFLIGHT_BENCHMARK_ID,
) -> OfficialBenchmarkConfig:
    """
    M13.19 corrected execution preflight — frozen official experiment, reduced seed matrix.

    Uses sealed PolicyPack and official scale (21d / 500 opps / 100 customers / ε=100).
    NOT admissible for benchmark superiority claims.
    """
    full = official_benchmark_config(policy_pack=policy_pack)
    return OfficialBenchmarkConfig(
        benchmark_id=benchmark_id,
        benchmark_version=full.benchmark_version,
        generator_version=full.generator_version,
        generator_config=full.generator_config,
        policy_pack_version=full.policy_pack_version,
        policy_pack_hash=full.policy_pack_hash,
        policy_pack_status=full.policy_pack_status,
        epsilon_paise=full.epsilon_paise,
        b1_schedule_version=full.b1_schedule_version,
        predictor_version=full.predictor_version,
        allocator_version=full.allocator_version,
        metric_version=full.metric_version,
        simulation_horizon_days=full.simulation_horizon_days,
        cycle_length_minutes=full.cycle_length_minutes,
        seed_set=seeds,
        profile_set=full.profile_set,
        approver_model_version=full.approver_model_version,
        llm_mode=full.llm_mode,
        allocator_mode=full.allocator_mode,
        policy_set=full.policy_set,
        code_revision=full.code_revision,
    )


def development_benchmark_config(
    *,
    policy_pack,
    seeds: tuple[int, ...] = (1,),
    profiles: tuple[GenerationProfile, ...] = (GenerationProfile.BALANCED,),
) -> OfficialBenchmarkConfig:
    """Small matrix for development validation — not an official claim."""
    from revive.simulation.fixtures import tiny_config

    base = tiny_config(seed=seeds[0], profile=profiles[0])
    return OfficialBenchmarkConfig(
        benchmark_id="revive_dev_m13",
        benchmark_version=BENCHMARK_VERSION,
        generator_version=GENERATOR_VERSION,
        generator_config=base,
        policy_pack_version=policy_pack.version,
        policy_pack_hash=policy_pack.config_hash(),
        policy_pack_status=policy_pack.status.value,
        epsilon_paise=policy_pack.epsilon_paise,
        b1_schedule_version=B1_SCHEDULE_VERSION,
        predictor_version=PREDICTOR_VERSION_DEV,
        allocator_version=ALLOCATOR_VERSION_REF,
        metric_version=METRIC_VERSION,
        simulation_horizon_days=base.simulation_window_days,
        cycle_length_minutes=base.cycle_interval_minutes,
        seed_set=seeds,
        profile_set=profiles,
        approver_model_version=APPROVER_MODEL_VERSION,
        llm_mode=LLM_MODE_OFFICIAL,
        allocator_mode=ALLOCATOR_MODE_OFFICIAL,
        policy_set=("B0", "B1", "B2", "B3", "REVIVE"),
        code_revision=_code_revision(),
    )


def generator_config_for_cell(
    template: OfficialBenchmarkConfig,
    seed: int,
    profile: GenerationProfile,
) -> GeneratorConfig:
    """Per seed/profile generator config — same parameters, different seed/profile."""
    base = template.generator_config
    return GeneratorConfig(
        seed=seed,
        profile=profile,
        merchant_count=base.merchant_count,
        customer_count=base.customer_count,
        opportunity_count=base.opportunity_count,
        simulation_window_days=base.simulation_window_days,
        cycle_interval_minutes=base.cycle_interval_minutes,
        opportunity_rate=base.opportunity_rate,
        failure_mix_payment=base.failure_mix_payment,
        failure_mix_checkout=base.failure_mix_checkout,
        failure_mix_subscription=base.failure_mix_subscription,
        failure_mix_receivable=base.failure_mix_receivable,
        failure_mix_mandate=base.failure_mix_mandate,
        abandonment_rate=base.abandonment_rate,
        subscription_rate=base.subscription_rate,
        receivable_rate=base.receivable_rate,
        degradation_frequency=base.degradation_frequency,
        natural_recovery_horizon_minutes=base.natural_recovery_horizon_minutes,
        default_outcome_horizon_minutes=base.default_outcome_horizon_minutes,
        inject_signal_faults=base.inject_signal_faults,
        inject_adversarial_cases=base.inject_adversarial_cases,
        privacy_canary_count=base.privacy_canary_count,
        metadata=dict(base.metadata),
    )
