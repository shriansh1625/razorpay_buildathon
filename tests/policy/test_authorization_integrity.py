"""No substitution, stopping overrides value, idempotency."""

from revive.config.policy_pack import PolicyPack, PolicyPackStatus
from revive.domain.enums import ActionCode, DecisionOutcome
from revive.decision.models import (
    AllocationDecision,
    AllocationSnapshot,
    DecisionLifecycleStatus,
)
from revive.policy import AuthorizationState, AuthorizeContext, authorize_execution, AuthorizationStore
from revive.policy.config import PolicyRules
from tests.policy.test_authorization_demo import (
    _candidate,
    _ctx,
    _decision,
    _valuation,
    NOW,
)


def test_no_action_substitution_when_primary_blocked():
    """Selected A05 blocked — does not authorize feasible A03."""
    decision = _decision(ActionCode.A05)
    blocked = authorize_execution(
        decision,
        _candidate(ActionCode.A05),
        _valuation(),
        _ctx(contacts_today=5),
        rules=PolicyRules(max_contacts_per_customer=2),
    )
    assert blocked.authorization_state == AuthorizationState.BLOCKED
    assert blocked.action_code == ActionCode.A05
    assert blocked.authorization_state != AuthorizationState.AUTHORIZED


def test_stopping_overrides_high_enrv():
    decision = _decision(enrv=50_000_000, value=50_000_000)
    auth = authorize_execution(
        decision,
        _candidate(ActionCode.A05),
        _valuation(50_000_000),
        _ctx(opted_out=True),
    )
    assert auth.authorization_state == AuthorizationState.BLOCKED
    assert any(s.rule_id == "SR-08" and s.fired for s in auth.stopping_results)


def test_idempotency_no_duplicate_authorization():
    store = AuthorizationStore()
    decision = _decision()
    cand = _candidate(ActionCode.A05)
    val = _valuation()
    ctx = _ctx()
    first = authorize_execution(decision, cand, val, ctx, store=store)
    assert first.authorization_state == AuthorizationState.AUTHORIZED
    second = authorize_execution(decision, cand, val, ctx, store=store)
    assert second.authorization_state == AuthorizationState.BLOCKED
    assert second.blocking_reason_code == "DUPLICATE_IDEMPOTENCY"


def test_stale_decision_not_authorized():
    decision = _decision()
    auth = authorize_execution(
        decision,
        _candidate(ActionCode.A05),
        _valuation(),
        _ctx(reconciliation_status="STALE"),
    )
    assert auth.authorization_state == AuthorizationState.STALE
    assert not auth.execution_ready
