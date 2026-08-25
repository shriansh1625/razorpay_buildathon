"""Execution result models — observable outcomes separate from M7 predictions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from revive.domain.enums import ActionCode, InterventionState
from revive.decision.models import ResourceReservation
from revive.simulation.types import AdapterResult, OutcomeKind


class ExecutionStage(str, Enum):
    """Execution lifecycle stages — docs/15, M11."""

    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYABLE = "RETRYABLE"
    PERMANENT_FAILURE = "PERMANENT_FAILURE"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    SCHEDULED = "SCHEDULED"


class LedgerSettlement(str, Enum):
    COMMIT = "COMMIT"
    RELEASE = "RELEASE"
    PARTIAL_COMMIT = "PARTIAL_COMMIT"


class RejectionReason(str, Enum):
    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    AUTHORIZATION_EXPIRED = "AUTHORIZATION_EXPIRED"
    RESERVATION_INVALID = "RESERVATION_INVALID"
    DUPLICATE_BLOCKED = "DUPLICATE_BLOCKED"


@dataclass(frozen=True, slots=True)
class RealizedOutcome:
    """M11 observable recovery outcome — never overwrites M7 valuation."""

    outcome_kind: OutcomeKind
    recovered_amount_paise: int
    recovered_at_micros: int | None
    observed_within_horizon: bool
    late_recovery: bool
    attribution_class: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_kind": self.outcome_kind.value,
            "recovered_amount_paise": self.recovered_amount_paise,
            "recovered_at_micros": self.recovered_at_micros,
            "observed_within_horizon": self.observed_within_horizon,
            "late_recovery": self.late_recovery,
            "attribution_class": self.attribution_class,
        }


@dataclass(frozen=True, slots=True)
class AuthorisedAction:
    """
    Type-safe execution token — only constructible via mint_authorised_action().
    """

    authorization_id: str
    decision_id: str
    opportunity_id: str
    candidate_id: str | None
    action_code: ActionCode
    authorized_parameters: dict[str, Any]
    idempotency_key: str
    configuration_hash: str
    authorization_version: str
    policy_pack_version: str
    allocator_version: str
    valuation_version: str
    expires_at_micros: int | None
    enrv_paise: int
    audit_reference: str


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    execution_id: str
    authorization_id: str
    decision_id: str
    opportunity_id: str
    candidate_id: str | None
    action_code: ActionCode
    intervention_id: str
    execution_stage: ExecutionStage
    adapter_result: AdapterResult | None
    predicted_cost_paise: int
    realized_cost_paise: int
    predicted_enrv_paise: int
    idempotency_key: str
    executed_at_micros: int
    duplicate: bool
    failure_reason: str | None
    ledger_settlement: LedgerSettlement | None
    intervention_state: InterventionState
    opportunity_state: str | None
    payment_state: str | None
    customer_response: str | None
    realized_outcome: RealizedOutcome | None
    resource_consumed: tuple[ResourceReservation, ...]
    scheduled_at_micros: int | None
    audit_intent_ref: str | None
    audit_result_ref: str | None
    configuration_hash: str
    authorization_version: str
    execution_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "authorization_id": self.authorization_id,
            "decision_id": self.decision_id,
            "opportunity_id": self.opportunity_id,
            "candidate_id": self.candidate_id,
            "action_code": self.action_code.value,
            "intervention_id": self.intervention_id,
            "execution_stage": self.execution_stage.value,
            "adapter_result": self.adapter_result.value if self.adapter_result else None,
            "predicted_cost_paise": self.predicted_cost_paise,
            "realized_cost_paise": self.realized_cost_paise,
            "predicted_enrv_paise": self.predicted_enrv_paise,
            "idempotency_key": self.idempotency_key,
            "executed_at_micros": self.executed_at_micros,
            "duplicate": self.duplicate,
            "failure_reason": self.failure_reason,
            "ledger_settlement": (
                self.ledger_settlement.value if self.ledger_settlement else None
            ),
            "intervention_state": self.intervention_state.value,
            "opportunity_state": self.opportunity_state,
            "payment_state": self.payment_state,
            "customer_response": self.customer_response,
            "realized_outcome": (
                self.realized_outcome.to_dict() if self.realized_outcome else None
            ),
            "resource_consumed": [r.to_dict() for r in self.resource_consumed],
            "scheduled_at_micros": self.scheduled_at_micros,
            "audit_intent_ref": self.audit_intent_ref,
            "audit_result_ref": self.audit_result_ref,
            "configuration_hash": self.configuration_hash,
            "authorization_version": self.authorization_version,
            "execution_version": self.execution_version,
        }
