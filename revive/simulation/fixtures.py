"""Small deterministic fixtures for unit tests."""

from __future__ import annotations

from revive.domain.enums import ActionCode, OpportunityState, RiskClass
from revive.domain.timestamps import VirtualTimestamp
from revive.simulation.config import GeneratorConfig
from revive.simulation.generator import generate_dataset
from revive.simulation.latent import LatentTraits
from revive.simulation.models import RevenueOpportunityRecord
from revive.simulation.oracle._partition import ActionResponse, OraclePartition, OracleRow
from revive.simulation.oracle.resolve import resolve_outcome
from revive.simulation.types import GenerationProfile
from revive.simulation.world import SyntheticWorld

MINUTE_MICROS = 60 * 1_000_000


def tiny_config(seed: int = 1, profile: GenerationProfile = GenerationProfile.BALANCED) -> GeneratorConfig:
    return GeneratorConfig(
        seed=seed,
        profile=profile,
        customer_count=8,
        opportunity_count=12,
        simulation_window_days=14,
        inject_signal_faults=False,
        inject_adversarial_cases=False,
        privacy_canary_count=1,
    )


def payment_failure_fixture() -> tuple[SyntheticWorld, OraclePartition, RevenueOpportunityRecord]:
    dataset = generate_dataset(
        GeneratorConfig(
            seed=1001,
            profile=GenerationProfile.BALANCED,
            customer_count=3,
            opportunity_count=5,
            failure_mix_payment=1.0,
            failure_mix_checkout=0.0,
            failure_mix_subscription=0.0,
            failure_mix_receivable=0.0,
            failure_mix_mandate=0.0,
            inject_signal_faults=False,
            privacy_canary_count=0,
        )
    )
    opp = next(o for o in dataset.world.opportunities if o.risk_class == RiskClass.PAYMENT_FAILURE)
    return dataset.world, dataset.oracle_partition, opp


def natural_recovery_fixture() -> OracleRow:
    partition = OraclePartition()
    row = OracleRow(
        opportunity_id="opp_natural",
        customer_id="cust_natural",
        recovers_naturally=True,
        natural_recovery_at_micros=60 * MINUTE_MICROS,
        natural_amount_paise=10_000,
        per_action_response={"A00": ActionResponse(False, 0, 0)},
        fatigue_curve={0: 1.0},
    )
    partition.add_row(row)
    return partition.get_row("opp_natural")


def action_variation_fixture() -> OraclePartition:
    partition = OraclePartition()
    base = 1_000_000
    partition.add_row(
        OracleRow(
            opportunity_id="opp_var",
            customer_id="cust_var",
            recovers_naturally=False,
            natural_recovery_at_micros=None,
            natural_amount_paise=0,
            per_action_response={
                "A01": ActionResponse(True, base + 30 * MINUTE_MICROS, 5000),
                "A05": ActionResponse(False, base + 60 * MINUTE_MICROS, 5000),
            },
            fatigue_curve={0: 1.0, 1: 0.8},
        )
    )
    return partition


def resolve_fixture_comparison(partition: OraclePartition) -> tuple[bool, bool]:
    t = VirtualTimestamp(0)
    a01 = resolve_outcome(
        partition,
        "opp_var",
        ActionCode.A01,
        t,
        horizon_minutes=120,
        value_at_risk_paise=5000,
    )
    a05 = resolve_outcome(
        partition,
        "opp_var",
        ActionCode.A05,
        t,
        horizon_minutes=120,
        value_at_risk_paise=5000,
    )
    return a01.recovered_amount_paise > 0, a05.recovered_amount_paise > 0
