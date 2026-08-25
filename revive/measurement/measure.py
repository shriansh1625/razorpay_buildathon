"""Measurement entry — ingest M11 execution, produce authoritative accounting."""

from __future__ import annotations

import hashlib

from revive.decision.models import AllocationDecision
from revive.domain.enums import Observability
from revive.execution.models import ExecutionResult
from revive.measurement.attribution import split_recovery
from revive.measurement.config import (
    DEFAULT_HORIZON_MINUTES,
    DEFAULT_NET_RETENTION,
    MEASUREMENT_VERSION,
)
from revive.measurement.ledger import OpportunityRecoveryLedger
from revive.measurement.models import (
    AttributionMethod,
    MeasurementProvenance,
    RecoveryMeasurement,
)
from revive.measurement.reference import (
    predicted_no_action_reference_paise,
    realized_no_action_reference_paise,
)
from revive.measurement.store import MeasurementStore
from revive.recovery.valuation.money import bankers_round_paise
from revive.recovery.valuation.models import CandidateValuation
from revive.simulation.oracle._partition import OraclePartition


def measurement_id_for(execution_id: str) -> str:
    digest = hashlib.sha256(
        f"{execution_id}:{MEASUREMENT_VERSION}".encode()
    ).hexdigest()
    return f"msr_{digest[:26]}"


def measure_execution(
    execution: ExecutionResult,
    valuation: CandidateValuation,
    decision: AllocationDecision,
    *,
    value_at_risk_paise: int,
    net_retention: float = DEFAULT_NET_RETENTION,
    horizon_minutes: int = DEFAULT_HORIZON_MINUTES,
    partition: OraclePartition | None = None,
    recovery_ledger: OpportunityRecoveryLedger | None = None,
    store: MeasurementStore | None = None,
    measured_at_micros: int | None = None,
    attempt_seq: int = 1,
) -> RecoveryMeasurement:
    """
    Measure a single execution outcome — idempotent per execution_id.

    Prediction fields come from M7 valuation (unchanged). Realization from M11.
    Oracle partition is optional and used only for realized no-action reference.
    """
    meas_store = store or MeasurementStore()
    existing = meas_store.get_by_execution(execution.execution_id)
    if existing is not None:
        return _duplicate_measurement(existing)

    opp_ledger = recovery_ledger or OpportunityRecoveryLedger()
    already_counted = opp_ledger.recovery_already_counted(execution.opportunity_id)
    opp_ledger.record_execution(execution.opportunity_id)

    split = split_recovery(execution, recovery_already_counted=already_counted)

    predicted_no_action = predicted_no_action_reference_paise(
        valuation, value_at_risk_paise, net_retention=net_retention
    )
    realized_no_action: int | None = None
    if partition is not None:
        realized_no_action = realized_no_action_reference_paise(
            partition,
            execution.opportunity_id,
            execution.executed_at_micros,
            value_at_risk_paise,
            horizon_minutes=horizon_minutes,
        )

    no_action_ref = (
        realized_no_action if realized_no_action is not None else predicted_no_action
    )
    incremental_vs_no_action = max(0, split.gross_recovered_paise - no_action_ref)

    net_gross = bankers_round_paise(
        split.attributed_recovered_paise * net_retention
    )
    realized_net = net_gross - execution.realized_cost_paise

    remaining = max(0, value_at_risk_paise - split.gross_recovered_paise)
    partial = (
        split.gross_recovered_paise > 0
        and split.gross_recovered_paise < value_at_risk_paise
    )

    observability = (
        Observability.OBSERVED
        if split.gross_recovered_paise > 0 or execution.realized_outcome is not None
        else Observability.UNOBSERVABLE
    )

    predicted_cost = valuation.cost_paise + valuation.expected_incentive_paise
    recovery_error = split.gross_recovered_paise - valuation.gross_paise
    enrv_error = realized_net - valuation.enrv_paise

    if split.gross_recovered_paise > 0 and not already_counted:
        opp_ledger.record_recovery(
            execution.opportunity_id, split.gross_recovered_paise
        )

    provenance = MeasurementProvenance(
        execution_id=execution.execution_id,
        authorization_id=execution.authorization_id,
        decision_id=execution.decision_id,
        opportunity_id=execution.opportunity_id,
        candidate_id=execution.candidate_id,
        cycle_id=decision.cycle_id,
        configuration_hash=execution.configuration_hash,
        valuation_version=valuation.valuation_version,
        strategy_version=valuation.strategy_version,
        execution_version=execution.execution_version,
        measurement_version=MEASUREMENT_VERSION,
        measured_at_micros=measured_at_micros or execution.executed_at_micros,
        attempt_seq=attempt_seq,
    )

    measurement = RecoveryMeasurement(
        measurement_id=measurement_id_for(execution.execution_id),
        provenance=provenance,
        action_code=execution.action_code,
        value_at_risk_paise=value_at_risk_paise,
        predicted_p_action=valuation.p_action,
        predicted_p_natural=valuation.p_natural,
        predicted_enrv_paise=valuation.enrv_paise,
        predicted_gross_paise=valuation.gross_paise,
        predicted_cost_paise=predicted_cost,
        predicted_no_action_reference_paise=predicted_no_action,
        predicted_fatigue_cost_paise=valuation.fatigue_cost_paise,
        gross_recovered_paise=split.gross_recovered_paise,
        attributed_recovered_paise=split.attributed_recovered_paise,
        natural_recovered_paise=split.natural_recovered_paise,
        ambiguous_recovered_paise=split.ambiguous_recovered_paise,
        incremental_recovered_paise=split.attributed_recovered_paise,
        incremental_vs_no_action_paise=incremental_vs_no_action,
        realized_no_action_reference_paise=realized_no_action,
        realized_cost_paise=execution.realized_cost_paise,
        realized_fatigue_cost_paise=valuation.fatigue_cost_paise,
        realized_net_value_paise=realized_net,
        remaining_exposure_paise=remaining,
        partial_recovery=partial,
        observed_within_horizon=split.observed_within_horizon,
        late_recovery=split.late_recovery,
        observability=observability,
        attribution_class=split.attribution_class,
        attribution_method=split.attribution_method,
        final_opportunity_state=execution.opportunity_state,
        execution_stage=execution.execution_stage.value,
        failure_reason=execution.failure_reason,
        duplicate_measurement=False,
        enrv_prediction_error_paise=enrv_error,
        recovery_prediction_error_paise=recovery_error,
    )
    return meas_store.record(measurement)


def _duplicate_measurement(existing: RecoveryMeasurement) -> RecoveryMeasurement:
    return RecoveryMeasurement(
        measurement_id=existing.measurement_id,
        provenance=existing.provenance,
        action_code=existing.action_code,
        value_at_risk_paise=existing.value_at_risk_paise,
        predicted_p_action=existing.predicted_p_action,
        predicted_p_natural=existing.predicted_p_natural,
        predicted_enrv_paise=existing.predicted_enrv_paise,
        predicted_gross_paise=existing.predicted_gross_paise,
        predicted_cost_paise=existing.predicted_cost_paise,
        predicted_no_action_reference_paise=existing.predicted_no_action_reference_paise,
        predicted_fatigue_cost_paise=existing.predicted_fatigue_cost_paise,
        gross_recovered_paise=existing.gross_recovered_paise,
        attributed_recovered_paise=existing.attributed_recovered_paise,
        natural_recovered_paise=existing.natural_recovered_paise,
        ambiguous_recovered_paise=existing.ambiguous_recovered_paise,
        incremental_recovered_paise=existing.incremental_recovered_paise,
        incremental_vs_no_action_paise=existing.incremental_vs_no_action_paise,
        realized_no_action_reference_paise=existing.realized_no_action_reference_paise,
        realized_cost_paise=existing.realized_cost_paise,
        realized_fatigue_cost_paise=existing.realized_fatigue_cost_paise,
        realized_net_value_paise=existing.realized_net_value_paise,
        remaining_exposure_paise=existing.remaining_exposure_paise,
        partial_recovery=existing.partial_recovery,
        observed_within_horizon=existing.observed_within_horizon,
        late_recovery=existing.late_recovery,
        observability=existing.observability,
        attribution_class=existing.attribution_class,
        attribution_method=existing.attribution_method,
        final_opportunity_state=existing.final_opportunity_state,
        execution_stage=existing.execution_stage,
        failure_reason=existing.failure_reason,
        duplicate_measurement=True,
        enrv_prediction_error_paise=existing.enrv_prediction_error_paise,
        recovery_prediction_error_paise=existing.recovery_prediction_error_paise,
    )
