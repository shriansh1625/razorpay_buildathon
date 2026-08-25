"""Cycle and batch aggregation primitives — M13 inputs only."""

from __future__ import annotations

from revive.decision.models import AllocationDecision
from revive.domain.enums import OpportunityState
from revive.execution.models import ExecutionResult, ExecutionStage
from revive.measurement.config import MEASUREMENT_VERSION
from revive.measurement.models import BatchTotals, CycleMeasurement, RecoveryMeasurement


def aggregate_cycle(
    measurements: tuple[RecoveryMeasurement, ...],
    cycle_id: str,
    *,
    measured_at_micros: int,
    stopped_opportunity_ids: frozenset[str] | None = None,
) -> CycleMeasurement:
    stopped = stopped_opportunity_ids or frozenset()
    opp_ids = {m.provenance.opportunity_id for m in measurements}
    return CycleMeasurement(
        cycle_id=cycle_id,
        measured_at_micros=measured_at_micros,
        gross_recovered_paise=sum(m.gross_recovered_paise for m in measurements),
        attributed_recovered_paise=sum(m.attributed_recovered_paise for m in measurements),
        natural_recovered_paise=sum(m.natural_recovered_paise for m in measurements),
        ambiguous_recovered_paise=sum(m.ambiguous_recovered_paise for m in measurements),
        incremental_recovered_paise=sum(m.incremental_recovered_paise for m in measurements),
        realized_cost_paise=sum(m.realized_cost_paise for m in measurements),
        realized_net_value_paise=sum(m.realized_net_value_paise for m in measurements),
        opportunities_measured=len(opp_ids),
        executions_measured=len(measurements),
        stopped_opportunities=len(opp_ids & stopped),
        measurement_version=MEASUREMENT_VERSION,
    )


def aggregate_batch(
    measurements: tuple[RecoveryMeasurement, ...],
    *,
    total_at_risk_paise: int | None = None,
) -> BatchTotals:
    at_risk = total_at_risk_paise
    if at_risk is None:
        at_risk = sum(m.value_at_risk_paise for m in measurements)
    return BatchTotals(
        total_at_risk_paise=at_risk,
        total_gross_recovered_paise=sum(m.gross_recovered_paise for m in measurements),
        total_natural_recovery_paise=sum(m.natural_recovered_paise for m in measurements),
        total_incremental_recovery_paise=sum(m.incremental_recovered_paise for m in measurements),
        total_realized_cost_paise=sum(m.realized_cost_paise for m in measurements),
        total_net_recovery_paise=sum(m.realized_net_value_paise for m in measurements),
        opportunities_count=len({m.provenance.opportunity_id for m in measurements}),
        execution_count=len(measurements),
        measurement_version=MEASUREMENT_VERSION,
    )


def safety_event_counts(
    executions: tuple[ExecutionResult, ...],
    decisions: tuple[AllocationDecision, ...],
) -> dict[str, int]:
    """Raw safety accounting for later M13 guardrail metrics."""
    blocked = sum(
        1 for e in executions if e.execution_stage == ExecutionStage.CANCELLED
    )
    failed = sum(
        1
        for e in executions
        if e.execution_stage
        in {
            ExecutionStage.FAILED,
            ExecutionStage.PERMANENT_FAILURE,
            ExecutionStage.RETRYABLE,
        }
    )
    duplicates = sum(1 for e in executions if e.duplicate)
    return {
        "execution_blocked_or_cancelled": blocked,
        "execution_failed": failed,
        "idempotency_duplicates": duplicates,
        "decisions_sealed": len(decisions),
    }
