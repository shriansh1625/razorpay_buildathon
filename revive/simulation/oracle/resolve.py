"""Narrow oracle outcome resolution — evaluator / simulation adapter boundary."""

from __future__ import annotations

from dataclasses import dataclass

from revive.domain.enums import ActionCode, AttributionClass
from revive.domain.timestamps import VirtualTimestamp
from revive.simulation.oracle._partition import OraclePartition, OracleRow
from revive.simulation.types import AdapterResult, OutcomeKind


@dataclass(frozen=True, slots=True)
class OutcomeResult:
    outcome_kind: OutcomeKind
    recovered_amount_paise: int
    recovered_at: VirtualTimestamp | None
    observed_within_horizon: bool
    late_recovery: bool
    attribution_class: AttributionClass
    adapter_result: AdapterResult


def _fatigue_multiplier(row: OracleRow, contact_count: int) -> float:
    if contact_count in row.fatigue_curve:
        return row.fatigue_curve[contact_count]
    keys = sorted(row.fatigue_curve.keys())
    if not keys:
        return 1.0
    if contact_count <= keys[0]:
        return row.fatigue_curve[keys[0]]
    return row.fatigue_curve[keys[-1]]


def resolve_outcome(
    partition: OraclePartition,
    opportunity_id: str,
    action_code: ActionCode,
    action_time: VirtualTimestamp,
    *,
    contact_count: int = 0,
    horizon_minutes: int,
    value_at_risk_paise: int,
    in_degradation_window: bool = False,
) -> OutcomeResult:
    """
    Resolve the actual outcome for an action at a point in time.

    Policy-neutral: no policy identity parameter. Used by simulation adapters
    and evaluation infrastructure only — not by decision engines.
    """
    row = partition.get_row(opportunity_id)
    if row is None:
        raise KeyError(f"no oracle row for opportunity {opportunity_id}")

    horizon_micros = horizon_minutes * 60 * 1_000_000
    action_micros = action_time.epoch_micros

    if action_code == ActionCode.A00:
        if row.recovers_naturally and row.natural_recovery_at_micros is not None:
            natural_at = row.natural_recovery_at_micros
            within = natural_at <= action_micros + horizon_micros
            late = natural_at > action_micros + horizon_micros
            return OutcomeResult(
                outcome_kind=OutcomeKind.NATURAL_RECOVERY,
                recovered_amount_paise=row.natural_amount_paise if within else 0,
                recovered_at=VirtualTimestamp(natural_at),
                observed_within_horizon=within,
                late_recovery=late and row.recovers_naturally,
                attribution_class=AttributionClass.NATURAL,
                adapter_result=AdapterResult.SUCCESS,
            )
        return OutcomeResult(
            outcome_kind=OutcomeKind.NOT_RECOVERED,
            recovered_amount_paise=0,
            recovered_at=None,
            observed_within_horizon=True,
            late_recovery=False,
            attribution_class=AttributionClass.NATURAL,
            adapter_result=AdapterResult.SUCCESS,
        )

    response = row.per_action_response.get(action_code.value)
    if response is None:
        return OutcomeResult(
            outcome_kind=OutcomeKind.ACTION_FAILED,
            recovered_amount_paise=0,
            recovered_at=None,
            observed_within_horizon=True,
            late_recovery=False,
            attribution_class=AttributionClass.AMBIGUOUS,
            adapter_result=AdapterResult.FAILED_TERMINAL,
        )

    fatigue = _fatigue_multiplier(row, contact_count)
    effective_recover = response.would_recover and fatigue > 0.15

    if response.adapter_result_override == AdapterResult.TIMEOUT_UNKNOWN.value:
        return OutcomeResult(
            outcome_kind=OutcomeKind.ACTION_FAILED,
            recovered_amount_paise=0,
            recovered_at=None,
            observed_within_horizon=True,
            late_recovery=False,
            attribution_class=AttributionClass.AMBIGUOUS,
            adapter_result=AdapterResult.TIMEOUT_UNKNOWN,
        )

    if not effective_recover:
        return OutcomeResult(
            outcome_kind=OutcomeKind.NOT_RECOVERED,
            recovered_amount_paise=0,
            recovered_at=None,
            observed_within_horizon=True,
            late_recovery=False,
            attribution_class=AttributionClass.ATTRIBUTED,
            adapter_result=AdapterResult.FAILED_TERMINAL,
        )

    recover_at = response.recover_at_micros
    if in_degradation_window and action_code == ActionCode.A01:
        recover_at += 30 * 60 * 1_000_000

    within = recover_at <= action_micros + horizon_micros
    late = recover_at > action_micros + horizon_micros
    amount = min(response.amount_paise, value_at_risk_paise)
    if fatigue < 1.0 and amount > 0:
        amount = int(amount * fatigue)

    kind = OutcomeKind.RECOVERED
    if amount < value_at_risk_paise and amount > 0:
        kind = OutcomeKind.PARTIALLY_RECOVERED

    adapter = AdapterResult.SUCCESS
    if response.adapter_result_override:
        adapter = AdapterResult(response.adapter_result_override)

    natural_overlap = (
        row.recovers_naturally
        and row.natural_recovery_at_micros is not None
        and row.natural_recovery_at_micros <= recover_at
    )
    attribution = (
        AttributionClass.NATURAL if natural_overlap and not within else AttributionClass.ATTRIBUTED
    )

    return OutcomeResult(
        outcome_kind=kind,
        recovered_amount_paise=amount if within else 0,
        recovered_at=VirtualTimestamp(recover_at),
        observed_within_horizon=within,
        late_recovery=late,
        attribution_class=attribution,
        adapter_result=adapter,
    )
