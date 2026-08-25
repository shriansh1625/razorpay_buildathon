"""Recovery measurement models — docs/17 §4.8, docs/21, docs/37."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from revive.domain.enums import ActionCode, AttributionClass, Observability


class AttributionMethod(str, Enum):
    """How attribution was determined — docs/21 §3."""

    EXECUTION_OUTCOME = "EXECUTION_OUTCOME"
    MULTI_ACTION_DEDUP = "MULTI_ACTION_DEDUP"
    NO_RECOVERY = "NO_RECOVERY"
    UNOBSERVABLE = "UNOBSERVABLE"


@dataclass(frozen=True, slots=True)
class MeasurementProvenance:
    execution_id: str
    authorization_id: str
    decision_id: str
    opportunity_id: str
    candidate_id: str | None
    cycle_id: str
    configuration_hash: str
    valuation_version: str
    strategy_version: str
    execution_version: str
    measurement_version: str
    measured_at_micros: int
    attempt_seq: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "authorization_id": self.authorization_id,
            "decision_id": self.decision_id,
            "opportunity_id": self.opportunity_id,
            "candidate_id": self.candidate_id,
            "cycle_id": self.cycle_id,
            "configuration_hash": self.configuration_hash,
            "valuation_version": self.valuation_version,
            "strategy_version": self.strategy_version,
            "execution_version": self.execution_version,
            "measurement_version": self.measurement_version,
            "measured_at_micros": self.measured_at_micros,
            "attempt_seq": self.attempt_seq,
        }


@dataclass(frozen=True, slots=True)
class RecoveryMeasurement:
    """Per-execution authoritative measurement — prediction and realization separate."""

    measurement_id: str
    provenance: MeasurementProvenance
    action_code: ActionCode
    value_at_risk_paise: int
    # Predicted world (M7) — never overwritten
    predicted_p_action: float
    predicted_p_natural: float
    predicted_enrv_paise: int
    predicted_gross_paise: int
    predicted_cost_paise: int
    predicted_no_action_reference_paise: int
    predicted_fatigue_cost_paise: int
    # Realized world (M11)
    gross_recovered_paise: int
    attributed_recovered_paise: int
    natural_recovered_paise: int
    ambiguous_recovered_paise: int
    incremental_recovered_paise: int
    incremental_vs_no_action_paise: int
    realized_no_action_reference_paise: int | None
    realized_cost_paise: int
    realized_fatigue_cost_paise: int
    realized_net_value_paise: int
    remaining_exposure_paise: int
    partial_recovery: bool
    observed_within_horizon: bool
    late_recovery: bool
    observability: Observability
    attribution_class: AttributionClass | None
    attribution_method: AttributionMethod
    final_opportunity_state: str | None
    execution_stage: str
    failure_reason: str | None
    duplicate_measurement: bool
    # Calibration deltas
    enrv_prediction_error_paise: int
    recovery_prediction_error_paise: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "measurement_id": self.measurement_id,
            "provenance": self.provenance.to_dict(),
            "action_code": self.action_code.value,
            "value_at_risk_paise": self.value_at_risk_paise,
            "predicted_p_action": self.predicted_p_action,
            "predicted_p_natural": self.predicted_p_natural,
            "predicted_enrv_paise": self.predicted_enrv_paise,
            "predicted_gross_paise": self.predicted_gross_paise,
            "predicted_cost_paise": self.predicted_cost_paise,
            "predicted_no_action_reference_paise": self.predicted_no_action_reference_paise,
            "predicted_fatigue_cost_paise": self.predicted_fatigue_cost_paise,
            "gross_recovered_paise": self.gross_recovered_paise,
            "attributed_recovered_paise": self.attributed_recovered_paise,
            "natural_recovered_paise": self.natural_recovered_paise,
            "ambiguous_recovered_paise": self.ambiguous_recovered_paise,
            "incremental_recovered_paise": self.incremental_recovered_paise,
            "incremental_vs_no_action_paise": self.incremental_vs_no_action_paise,
            "realized_no_action_reference_paise": self.realized_no_action_reference_paise,
            "realized_cost_paise": self.realized_cost_paise,
            "realized_fatigue_cost_paise": self.realized_fatigue_cost_paise,
            "realized_net_value_paise": self.realized_net_value_paise,
            "remaining_exposure_paise": self.remaining_exposure_paise,
            "partial_recovery": self.partial_recovery,
            "observed_within_horizon": self.observed_within_horizon,
            "late_recovery": self.late_recovery,
            "observability": self.observability.value,
            "attribution_class": (
                self.attribution_class.value if self.attribution_class else None
            ),
            "attribution_method": self.attribution_method.value,
            "final_opportunity_state": self.final_opportunity_state,
            "execution_stage": self.execution_stage,
            "failure_reason": self.failure_reason,
            "duplicate_measurement": self.duplicate_measurement,
            "enrv_prediction_error_paise": self.enrv_prediction_error_paise,
            "recovery_prediction_error_paise": self.recovery_prediction_error_paise,
        }

    def identity_holds(self) -> bool:
        """AT-3: gross = attributed + natural + ambiguous."""
        return (
            self.gross_recovered_paise
            == self.attributed_recovered_paise
            + self.natural_recovered_paise
            + self.ambiguous_recovered_paise
        )


@dataclass(frozen=True, slots=True)
class CycleMeasurement:
    """Cycle-level aggregation primitives — no benchmark comparison."""

    cycle_id: str
    measured_at_micros: int
    gross_recovered_paise: int
    attributed_recovered_paise: int
    natural_recovered_paise: int
    ambiguous_recovered_paise: int
    incremental_recovered_paise: int
    realized_cost_paise: int
    realized_net_value_paise: int
    opportunities_measured: int
    executions_measured: int
    stopped_opportunities: int
    measurement_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "measured_at_micros": self.measured_at_micros,
            "gross_recovered_paise": self.gross_recovered_paise,
            "attributed_recovered_paise": self.attributed_recovered_paise,
            "natural_recovered_paise": self.natural_recovered_paise,
            "ambiguous_recovered_paise": self.ambiguous_recovered_paise,
            "incremental_recovered_paise": self.incremental_recovered_paise,
            "realized_cost_paise": self.realized_cost_paise,
            "realized_net_value_paise": self.realized_net_value_paise,
            "opportunities_measured": self.opportunities_measured,
            "executions_measured": self.executions_measured,
            "stopped_opportunities": self.stopped_opportunities,
            "measurement_version": self.measurement_version,
        }


@dataclass(frozen=True, slots=True)
class BatchTotals:
    """Batch aggregation primitives for M13 — no rankings."""

    total_at_risk_paise: int
    total_gross_recovered_paise: int
    total_natural_recovery_paise: int
    total_incremental_recovery_paise: int
    total_realized_cost_paise: int
    total_net_recovery_paise: int
    opportunities_count: int
    execution_count: int
    measurement_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_at_risk_paise": self.total_at_risk_paise,
            "total_gross_recovered_paise": self.total_gross_recovered_paise,
            "total_natural_recovery_paise": self.total_natural_recovery_paise,
            "total_incremental_recovery_paise": self.total_incremental_recovery_paise,
            "total_realized_cost_paise": self.total_realized_cost_paise,
            "total_net_recovery_paise": self.total_net_recovery_paise,
            "opportunities_count": self.opportunities_count,
            "execution_count": self.execution_count,
            "measurement_version": self.measurement_version,
        }
