"""Authorization and gate models — docs/13, docs/17 §4.5."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from revive.domain.enums import ActionCode, ApprovalRequestState, GateVerdictKind


class AuthorizationState(str, Enum):
    AUTHORIZED = "AUTHORIZED"
    BLOCKED = "BLOCKED"
    REQUIRES_HUMAN_APPROVAL = "REQUIRES_HUMAN_APPROVAL"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    REPLAN_REQUIRED = "REPLAN_REQUIRED"


@dataclass(frozen=True, slots=True)
class GateResult:
    gate_id: str
    sequence: int
    verdict: GateVerdictKind
    reason_code: str
    blocking: bool
    observed_value: Any = None
    limit_value: Any = None
    detail: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "sequence": self.sequence,
            "verdict": self.verdict.value,
            "reason_code": self.reason_code,
            "blocking": self.blocking,
            "observed_value": self.observed_value,
            "limit_value": self.limit_value,
            "detail": dict(self.detail or {}),
        }


@dataclass(frozen=True, slots=True)
class StoppingRuleResult:
    rule_id: str
    fired: bool
    blocking: bool
    reason_code: str
    observed_value: Any = None
    threshold: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "fired": self.fired,
            "blocking": self.blocking,
            "reason_code": self.reason_code,
            "observed_value": self.observed_value,
            "threshold": self.threshold,
        }


@dataclass(frozen=True, slots=True)
class ExecutionAuthorization:
    authorization_id: str
    decision_id: str
    opportunity_id: str
    candidate_id: str | None
    action_code: ActionCode
    authorized_parameters: dict[str, Any]
    authorization_state: AuthorizationState
    gate_trace: tuple[GateResult, ...]
    stopping_results: tuple[StoppingRuleResult, ...]
    approval_requirement: bool
    approval_state: ApprovalRequestState | None
    policy_pack_version: str
    configuration_hash: str
    allocator_version: str
    valuation_version: str
    authorization_version: str
    authorized_at_micros: int | None
    expires_at_micros: int | None
    idempotency_key: str
    enrv_paise: int
    blocking_gate_id: str | None
    blocking_reason_code: str | None
    audit_reference: str
    explanation: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "authorization_id": self.authorization_id,
            "decision_id": self.decision_id,
            "opportunity_id": self.opportunity_id,
            "candidate_id": self.candidate_id,
            "action_code": self.action_code.value,
            "authorized_parameters": dict(self.authorized_parameters),
            "authorization_state": self.authorization_state.value,
            "gate_trace": [g.to_dict() for g in self.gate_trace],
            "stopping_results": [s.to_dict() for s in self.stopping_results],
            "approval_requirement": self.approval_requirement,
            "approval_state": self.approval_state.value if self.approval_state else None,
            "policy_pack_version": self.policy_pack_version,
            "configuration_hash": self.configuration_hash,
            "allocator_version": self.allocator_version,
            "valuation_version": self.valuation_version,
            "authorization_version": self.authorization_version,
            "authorized_at_micros": self.authorized_at_micros,
            "expires_at_micros": self.expires_at_micros,
            "idempotency_key": self.idempotency_key,
            "enrv_paise": self.enrv_paise,
            "blocking_gate_id": self.blocking_gate_id,
            "blocking_reason_code": self.blocking_reason_code,
            "audit_reference": self.audit_reference,
            "explanation": list(self.explanation),
        }

    @property
    def execution_ready(self) -> bool:
        return self.authorization_state == AuthorizationState.AUTHORIZED
