"""Policy run metrics — docs/21, docs/37."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.domain.enums import ActionCode
from revive.execution.models import ExecutionResult, ExecutionStage
from revive.measurement.aggregate import aggregate_batch
from revive.measurement.models import RecoveryMeasurement
from revive.policy.models import AuthorizationState, ExecutionAuthorization

CONTACT_ACTIONS = frozenset(
    {
        ActionCode.A04,
        ActionCode.A05,
        ActionCode.A06,
        ActionCode.A07,
        ActionCode.A08,
        ActionCode.A09,
        ActionCode.A11,
    }
)


@dataclass
class PolicyRunMetrics:
    policy_id: str
    seed: int
    profile: str
    net_recovered_paise: int = 0
    gross_recovered_paise: int = 0
    natural_recovered_paise: int = 0
    incremental_recovered_paise: int = 0
    realized_cost_paise: int = 0
    intervention_count: int = 0
    contact_count: int = 0
    unauthorized_executions: int = 0
    policy_violations: int = 0
    stopping_rule_violations: int = 0
    execution_failures: int = 0
    idempotency_conflicts: int = 0
    duplicate_effects: int = 0
    resource_oversubscriptions: int = 0
    budget_violations: int = 0
    predicted_enrv_paise: int = 0
    realized_incremental_paise: int = 0
    enrv_prediction_error_paise: int = 0
    recovery_prediction_error_paise: int = 0
    recovery_rate: float = 0.0
    budget_utilization: float = 0.0
    resource_utilization: dict[str, float] = field(default_factory=dict)
    run_valid: bool = True
    invalid_reasons: list[str] = field(default_factory=list)
    m10_incremental_net_paise: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PolicyRunMetrics:
        return cls(
            policy_id=str(data["policy_id"]),
            seed=int(data["seed"]),
            profile=str(data["profile"]),
            net_recovered_paise=int(data.get("net_recovered_paise", 0)),
            gross_recovered_paise=int(data.get("gross_recovered_paise", 0)),
            natural_recovered_paise=int(data.get("natural_recovered_paise", 0)),
            incremental_recovered_paise=int(data.get("incremental_recovered_paise", 0)),
            realized_cost_paise=int(data.get("realized_cost_paise", 0)),
            intervention_count=int(data.get("intervention_count", 0)),
            contact_count=int(data.get("contact_count", 0)),
            unauthorized_executions=int(data.get("unauthorized_executions", 0)),
            policy_violations=int(data.get("policy_violations", 0)),
            stopping_rule_violations=int(data.get("stopping_rule_violations", 0)),
            execution_failures=int(data.get("execution_failures", 0)),
            idempotency_conflicts=int(data.get("idempotency_conflicts", 0)),
            duplicate_effects=int(data.get("duplicate_effects", 0)),
            resource_oversubscriptions=int(data.get("resource_oversubscriptions", 0)),
            budget_violations=int(data.get("budget_violations", 0)),
            predicted_enrv_paise=int(data.get("predicted_enrv_paise", 0)),
            realized_incremental_paise=int(data.get("realized_incremental_paise", 0)),
            enrv_prediction_error_paise=int(data.get("enrv_prediction_error_paise", 0)),
            recovery_prediction_error_paise=int(
                data.get("recovery_prediction_error_paise", 0)
            ),
            recovery_rate=float(data.get("recovery_rate", 0.0)),
            budget_utilization=float(data.get("budget_utilization", 0.0)),
            resource_utilization=dict(data.get("resource_utilization", {})),
            run_valid=bool(data.get("run_valid", True)),
            invalid_reasons=list(data.get("invalid_reasons", [])),
            m10_incremental_net_paise=data.get("M-10_incremental_net_paise"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "seed": self.seed,
            "profile": self.profile,
            "net_recovered_paise": self.net_recovered_paise,
            "gross_recovered_paise": self.gross_recovered_paise,
            "natural_recovered_paise": self.natural_recovered_paise,
            "incremental_recovered_paise": self.incremental_recovered_paise,
            "realized_cost_paise": self.realized_cost_paise,
            "intervention_count": self.intervention_count,
            "contact_count": self.contact_count,
            "unauthorized_executions": self.unauthorized_executions,
            "policy_violations": self.policy_violations,
            "stopping_rule_violations": self.stopping_rule_violations,
            "execution_failures": self.execution_failures,
            "idempotency_conflicts": self.idempotency_conflicts,
            "duplicate_effects": self.duplicate_effects,
            "resource_oversubscriptions": self.resource_oversubscriptions,
            "budget_violations": self.budget_violations,
            "predicted_enrv_paise": self.predicted_enrv_paise,
            "realized_incremental_paise": self.realized_incremental_paise,
            "enrv_prediction_error_paise": self.enrv_prediction_error_paise,
            "recovery_prediction_error_paise": self.recovery_prediction_error_paise,
            "recovery_rate": self.recovery_rate,
            "budget_utilization": self.budget_utilization,
            "resource_utilization": self.resource_utilization,
            "run_valid": self.run_valid,
            "invalid_reasons": self.invalid_reasons,
            "M-10_incremental_net_paise": self.m10_incremental_net_paise,
        }


def compute_policy_metrics(
    policy_id: str,
    seed: int,
    profile: str,
    measurements: tuple[RecoveryMeasurement, ...],
    executions: tuple[ExecutionResult, ...],
    authorizations: tuple[ExecutionAuthorization, ...],
    *,
    incentive_budget_capacity_paise: int,
    retry_capacity: int,
    message_capacity: int,
) -> PolicyRunMetrics:
    batch = aggregate_batch(measurements)

    predicted_enrv_paise = 0
    realized_incremental_paise = 0
    enrv_prediction_error_paise = 0
    recovery_prediction_error_paise = 0
    duplicate_effects = 0
    for measurement in measurements:
        predicted_enrv_paise += measurement.predicted_enrv_paise
        realized_incremental_paise += measurement.incremental_recovered_paise
        enrv_prediction_error_paise += measurement.enrv_prediction_error_paise
        recovery_prediction_error_paise += measurement.recovery_prediction_error_paise
        if measurement.duplicate_measurement:
            duplicate_effects += 1

    contact_count = 0
    execution_failures = 0
    idempotency_conflicts = 0
    succeeded_auth_ids: set[str] = set()
    failed_stages = frozenset(
        {
            ExecutionStage.FAILED,
            ExecutionStage.PERMANENT_FAILURE,
            ExecutionStage.RETRYABLE,
        }
    )
    for execution in executions:
        stage = execution.execution_stage
        if execution.action_code in CONTACT_ACTIONS and stage == ExecutionStage.SUCCEEDED:
            contact_count += 1
        if stage == ExecutionStage.SUCCEEDED:
            succeeded_auth_ids.add(execution.authorization_id)
        elif stage in failed_stages:
            execution_failures += 1
        if execution.duplicate:
            idempotency_conflicts += 1

    unauthorized_executions = sum(
        1
        for authorization in authorizations
        if authorization.authorization_state != AuthorizationState.AUTHORIZED
        and authorization.authorization_id in succeeded_auth_ids
    )

    metrics = PolicyRunMetrics(
        policy_id=policy_id,
        seed=seed,
        profile=profile,
        net_recovered_paise=batch.total_net_recovery_paise,
        gross_recovered_paise=batch.total_gross_recovered_paise,
        natural_recovered_paise=batch.total_natural_recovery_paise,
        incremental_recovered_paise=batch.total_incremental_recovery_paise,
        realized_cost_paise=batch.total_realized_cost_paise,
        intervention_count=len(executions),
        contact_count=contact_count,
        predicted_enrv_paise=predicted_enrv_paise,
        realized_incremental_paise=realized_incremental_paise,
        enrv_prediction_error_paise=enrv_prediction_error_paise,
        recovery_prediction_error_paise=recovery_prediction_error_paise,
        unauthorized_executions=unauthorized_executions,
        execution_failures=execution_failures,
        idempotency_conflicts=idempotency_conflicts,
        duplicate_effects=duplicate_effects,
    )

    if batch.total_at_risk_paise > 0:
        metrics.recovery_rate = batch.total_gross_recovered_paise / batch.total_at_risk_paise

    total_cost = batch.total_realized_cost_paise
    if incentive_budget_capacity_paise > 0:
        metrics.budget_utilization = total_cost / incentive_budget_capacity_paise

    metrics.resource_utilization = {
        "retry_slots": min(1.0, metrics.intervention_count / max(1, retry_capacity)),
        "message_capacity": min(1.0, metrics.contact_count / max(1, message_capacity)),
    }

    # Tier-0 guardrails — M-16 style
    if metrics.unauthorized_executions > 0:
        metrics.run_valid = False
        metrics.invalid_reasons.append("M-16: unauthorized_executions > 0")

    return metrics


def apply_m10_paired(
    policy_metrics: PolicyRunMetrics,
    b0_net_recovered_paise: int,
) -> PolicyRunMetrics:
    """M-10 = NetRecovered(policy) - NetRecovered(B0) per docs/21 §2.1."""
    policy_metrics.m10_incremental_net_paise = (
        policy_metrics.net_recovered_paise - b0_net_recovered_paise
    )
    return policy_metrics
