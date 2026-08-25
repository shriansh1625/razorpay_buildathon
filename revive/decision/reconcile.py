"""Reconcile allocation decisions against current observable state."""

from __future__ import annotations

from revive.domain.enums import ActionCode, DecisionOutcome
from revive.decision.models import (
    AllocationDecision,
    DecisionLifecycleStatus,
    ObservableReconcileContext,
    ReconciliationResult,
    StatusTransition,
)


def reconcile_decision(
    decision: AllocationDecision,
    context: ObservableReconcileContext,
    prior_result: ReconciliationResult | None = None,
) -> ReconciliationResult:
    """Check validity — does NOT re-allocate or execute."""
    if prior_result is not None and prior_result.decision_id == decision.decision_id:
        return prior_result

    if decision.lifecycle_status == DecisionLifecycleStatus.SUPERSEDED:
        return ReconciliationResult(
            decision_id=decision.decision_id,
            status=DecisionLifecycleStatus.SUPERSEDED,
            execution_ready=False,
            reason_code="SUPERSEDED",
            reconciled_at_micros=context.now_micros,
        )

    if decision.lifecycle_status == DecisionLifecycleStatus.CANCELLED:
        return ReconciliationResult(
            decision_id=decision.decision_id,
            status=DecisionLifecycleStatus.CANCELLED,
            execution_ready=False,
            reason_code="CANCELLED",
            reconciled_at_micros=context.now_micros,
        )

    stale_factors: list[str] = []

    if context.now_micros > decision.expires_at_micros:
        return ReconciliationResult(
            decision_id=decision.decision_id,
            status=DecisionLifecycleStatus.EXPIRED,
            execution_ready=False,
            reason_code="EXPIRED",
            reconciled_at_micros=context.now_micros,
            stale_factors=("time_expired",),
        )

    if context.configuration_hash and context.configuration_hash != decision.configuration_hash:
        stale_factors.append("configuration_changed")

    if context.policy_config_hash:
        expected_policy = decision.configuration_hash
        if context.policy_config_hash != decision.policy_pack_version:
            # Policy hash change detected via configuration bundle.
            if context.configuration_hash and context.configuration_hash != decision.configuration_hash:
                stale_factors.append("policy_changed")

    if context.payment_succeeded and _is_retry_action(decision.action_code):
        stale_factors.append("payment_already_recovered")

    if context.opportunity_state in ("RECOVERED", "CLOSED", "STOPPED"):
        stale_factors.append("opportunity_closed")

    if decision.outcome == DecisionOutcome.SELECTED and decision.customer_id:
        if _uses_contact(decision.action_code):
            if context.contacts_used_for_customer >= context.contact_allowance_per_customer:
                stale_factors.append("contact_capacity_consumed")

    if stale_factors:
        return ReconciliationResult(
            decision_id=decision.decision_id,
            status=DecisionLifecycleStatus.STALE,
            execution_ready=False,
            reason_code="STALE_STATE",
            reconciled_at_micros=context.now_micros,
            stale_factors=tuple(stale_factors),
        )

    if decision.outcome != DecisionOutcome.SELECTED:
        return ReconciliationResult(
            decision_id=decision.decision_id,
            status=decision.lifecycle_status,
            execution_ready=False,
            reason_code=decision.reason_code,
            reconciled_at_micros=context.now_micros,
        )

    status = DecisionLifecycleStatus.VALID
    return ReconciliationResult(
        decision_id=decision.decision_id,
        status=status,
        execution_ready=True,
        reason_code="VALID",
        reconciled_at_micros=context.now_micros,
    )


def transition_for_reconciliation(
    decision: AllocationDecision,
    result: ReconciliationResult,
) -> StatusTransition | None:
    if result.status == decision.lifecycle_status:
        return None
    return StatusTransition(
        decision_id=decision.decision_id,
        from_status=decision.lifecycle_status,
        to_status=result.status,
        reason_code=result.reason_code,
        occurred_at_micros=result.reconciled_at_micros,
    )


def _is_retry_action(action: ActionCode) -> bool:
    return action in {
        ActionCode.A01,
        ActionCode.A02,
        ActionCode.A03,
    }


def _uses_contact(action: ActionCode) -> bool:
    return action not in {ActionCode.A00, ActionCode.A01, ActionCode.A02}
