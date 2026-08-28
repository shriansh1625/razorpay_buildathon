"""Product-facing catalogues — labels only. Engine enums stay unchanged."""

from __future__ import annotations

from revive.domain.enums import ActionCode, RiskClass

ACTION_LABELS: dict[str, str] = {
    ActionCode.A00.value: "Do nothing",
    ActionCode.A01.value: "Retry payment now",
    ActionCode.A02.value: "Retry payment (scheduled)",
    ActionCode.A03.value: "Retry different instrument",
    ActionCode.A04.value: "Send payment link",
    ActionCode.A05.value: "Send reminder",
    ActionCode.A06.value: "Offer incentive",
    ActionCode.A07.value: "Escalate to agent",
    ActionCode.A08.value: "Update mandate",
    ActionCode.A09.value: "Resume checkout",
    ActionCode.A10.value: "Partial write-off",
    ActionCode.A11.value: "Request consent",
    ActionCode.A12.value: "Defer to next cycle",
    ActionCode.A13.value: "Cancel and reissue",
    ActionCode.A14.value: "Manual review only",
}

RISK_LABELS: dict[str, str] = {
    RiskClass.PAYMENT_FAILURE.value: "Payment failure",
    RiskClass.CHECKOUT_ABANDONMENT.value: "Checkout abandonment",
    RiskClass.SUBSCRIPTION_FAILURE.value: "Subscription failure",
    RiskClass.RECEIVABLE_OVERDUE.value: "Receivable overdue",
    RiskClass.MANDATE_HEALTH.value: "Mandate health",
}

PIPELINE_STAGES: tuple[str, ...] = (
    "DETECTED",
    "DIAGNOSED",
    "OPTIMIZED",
    "GUARDED",
    "AUTHORIZED",
    "EXECUTED",
    "MEASURED",
)

BLOCK_REASON_LABELS: dict[str, str] = {
    "DUPLICATE_IDEMPOTENCY": "Duplicate action",
    "STALE_DECISION": "Stale decision",
    "EXPIRED_DECISION": "Expired decision",
    "DECISION_INVALID": "Decision no longer valid",
    "CONFIGURATION_MISMATCH": "Configuration mismatch",
    "POLICY_PACK_MISMATCH": "Policy pack mismatch",
    "CANDIDATE_MISSING": "Candidate missing",
    "BUDGET_EXCEEDED": "Budget exceeded",
    "RESOURCE_UNAVAILABLE": "Resource unavailable",
    "APPROVAL_REQUIRED": "Approval required",
    "COOLDOWN_ACTIVE": "Cooldown active",
    "CONTACT_CAP_EXCEEDED": "Contact cap exceeded",
    "WINDOW_EXPIRED": "Recovery window expired",
    "RISK_HOLD": "Risk / legal hold",
    "CONSENT_MISSING": "Consent missing",
    "UNSAFE_ACTION": "Unsafe action",
}


def action_label(code: str) -> str:
    return ACTION_LABELS.get(code, code)


def risk_label(code: str) -> str:
    return RISK_LABELS.get(code, code)


def block_label(reason: str | None) -> str | None:
    if not reason:
        return None
    return BLOCK_REASON_LABELS.get(reason, reason.replace("_", " ").title())
