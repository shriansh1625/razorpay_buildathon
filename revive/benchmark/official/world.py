"""Shared synthetic world per seed/profile — M13 §10."""

from __future__ import annotations

import copy
from dataclasses import dataclass

from revive.domain.enums import OpportunityState
from revive.simulation.config import GeneratorConfig
from revive.simulation.generator import GeneratedDataset, generate_dataset
from revive.simulation.models import RevenueOpportunityRecord
from revive.simulation.world import SyntheticWorld

MINUTE_MICROS = 60 * 1_000_000
DAY_MICROS = 24 * 60 * MINUTE_MICROS


@dataclass(frozen=True, slots=True)
class SharedWorldBundle:
    """One frozen world per seed/profile — policy-neutral oracle truth."""

    seed: int
    profile: str
    config: GeneratorConfig
    dataset_hash: str
    world: SyntheticWorld
    oracle_partition: object
    cycle_times_micros: tuple[int, ...]


def cycle_times_for_config(config: GeneratorConfig) -> tuple[int, ...]:
    interval = config.cycle_interval_minutes * MINUTE_MICROS
    end = config.simulation_window_days * DAY_MICROS
    times: list[int] = []
    t = interval
    while t <= end:
        times.append(t)
        t += interval
    return tuple(times)


def generate_shared_world(config: GeneratorConfig) -> SharedWorldBundle:
    """Generate exactly one world for a seed/profile cell."""
    dataset = generate_dataset(config)
    return SharedWorldBundle(
        seed=config.seed,
        profile=config.profile.value,
        config=config,
        dataset_hash=dataset.dataset_hash,
        world=dataset.world,
        oracle_partition=dataset.oracle_partition,
        cycle_times_micros=cycle_times_for_config(config),
    )


def clone_world(world: SyntheticWorld) -> SyntheticWorld:
    """Deep copy observable world for independent policy simulation."""
    return copy.deepcopy(world)


def clone_shared_world(bundle: SharedWorldBundle) -> SharedWorldBundle:
    """Clone world only — oracle partition is read-only shared truth."""
    return SharedWorldBundle(
        seed=bundle.seed,
        profile=bundle.profile,
        config=bundle.config,
        dataset_hash=bundle.dataset_hash,
        world=clone_world(bundle.world),
        oracle_partition=bundle.oracle_partition,
        cycle_times_micros=bundle.cycle_times_micros,
    )


def find_opportunity(world: SyntheticWorld, opportunity_id: str) -> RevenueOpportunityRecord | None:
    for opp in world.opportunities:
        if opp.opportunity_id == opportunity_id:
            return opp
    return None


def update_opportunity_state(
    world: SyntheticWorld,
    opportunity_id: str,
    *,
    state: OpportunityState | None = None,
    contacts_made: int | None = None,
    attempt_seq: int | None = None,
) -> None:
    """Replace immutable opportunity record with updated fields."""
    for idx, opp in enumerate(world.opportunities):
        if opp.opportunity_id != opportunity_id:
            continue
        world.opportunities[idx] = RevenueOpportunityRecord(
            opportunity_id=opp.opportunity_id,
            merchant_id=opp.merchant_id,
            customer_id=opp.customer_id,
            risk_class=opp.risk_class,
            natural_key=opp.natural_key,
            value_at_risk_paise=opp.value_at_risk_paise,
            original_value_paise=opp.original_value_paise,
            continuation_value_paise=opp.continuation_value_paise,
            addressable=opp.addressable,
            state=state if state is not None else opp.state,
            first_detected_at_micros=opp.first_detected_at_micros,
            recovery_window_expires_at_micros=opp.recovery_window_expires_at_micros,
            attempt_seq=attempt_seq if attempt_seq is not None else opp.attempt_seq,
            contacts_made=contacts_made if contacts_made is not None else opp.contacts_made,
            linked_refs=dict(opp.linked_refs),
            failure_reason=opp.failure_reason,
            checkout_stage=opp.checkout_stage,
            invoice_age_days=opp.invoice_age_days,
            in_degradation_window=opp.in_degradation_window,
        )
        break


def mark_recovered(world: SyntheticWorld, opportunity_id: str) -> None:
    update_opportunity_state(
        world,
        opportunity_id,
        state=OpportunityState.RECOVERED,
    )


def increment_contact(world: SyntheticWorld, opportunity_id: str) -> None:
    opp = find_opportunity(world, opportunity_id)
    if opp is None:
        return
    update_opportunity_state(
        world,
        opportunity_id,
        contacts_made=opp.contacts_made + 1,
        state=OpportunityState.AWAITING_OUTCOME,
    )
