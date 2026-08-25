"""Attribution split — docs/21 §3, AT-1 through AT-3."""

from __future__ import annotations

from dataclasses import dataclass

from revive.domain.enums import AttributionClass
from revive.execution.models import ExecutionResult, ExecutionStage, RealizedOutcome
from revive.measurement.models import AttributionMethod


@dataclass(frozen=True, slots=True)
class AttributionSplit:
    gross_recovered_paise: int
    attributed_recovered_paise: int
    natural_recovered_paise: int
    ambiguous_recovered_paise: int
    attribution_class: AttributionClass | None
    attribution_method: AttributionMethod
    observed_within_horizon: bool
    late_recovery: bool


def split_recovery(
    execution: ExecutionResult,
    *,
    recovery_already_counted: bool,
) -> AttributionSplit:
    """
    Split gross recovery into attributed / natural / ambiguous buckets.

    Uses M11 observable outcome attribution_class. Multi-action dedup zeroes
    monetary buckets when recovery was already counted on the opportunity.
    """
    realized = execution.realized_outcome
    if execution.execution_stage in {
        ExecutionStage.CANCELLED,
        ExecutionStage.SCHEDULED,
    }:
        return _empty_split(AttributionMethod.NO_RECOVERY)

    if realized is None or realized.recovered_amount_paise <= 0:
        return _empty_split(AttributionMethod.NO_RECOVERY)

    gross = realized.recovered_amount_paise
    if not realized.observed_within_horizon or realized.late_recovery:
        return AttributionSplit(
            gross_recovered_paise=0,
            attributed_recovered_paise=0,
            natural_recovered_paise=0,
            ambiguous_recovered_paise=0,
            attribution_class=AttributionClass.NATURAL,
            attribution_method=AttributionMethod.NO_RECOVERY,
            observed_within_horizon=realized.observed_within_horizon,
            late_recovery=realized.late_recovery,
        )

    if recovery_already_counted:
        return AttributionSplit(
            gross_recovered_paise=0,
            attributed_recovered_paise=0,
            natural_recovered_paise=0,
            ambiguous_recovered_paise=0,
            attribution_class=AttributionClass.AMBIGUOUS,
            attribution_method=AttributionMethod.MULTI_ACTION_DEDUP,
            observed_within_horizon=True,
            late_recovery=False,
        )

    attr_class = AttributionClass(realized.attribution_class)
    attributed = natural = ambiguous = 0
    if attr_class == AttributionClass.ATTRIBUTED:
        attributed = gross
    elif attr_class == AttributionClass.NATURAL:
        natural = gross
    else:
        ambiguous = gross

    return AttributionSplit(
        gross_recovered_paise=gross,
        attributed_recovered_paise=attributed,
        natural_recovered_paise=natural,
        ambiguous_recovered_paise=ambiguous,
        attribution_class=attr_class,
        attribution_method=AttributionMethod.EXECUTION_OUTCOME,
        observed_within_horizon=True,
        late_recovery=False,
    )


def _empty_split(method: AttributionMethod) -> AttributionSplit:
    return AttributionSplit(
        gross_recovered_paise=0,
        attributed_recovered_paise=0,
        natural_recovered_paise=0,
        ambiguous_recovered_paise=0,
        attribution_class=None,
        attribution_method=method,
        observed_within_horizon=False,
        late_recovery=False,
    )
