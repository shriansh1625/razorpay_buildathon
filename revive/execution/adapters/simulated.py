"""Simulated action adapters — oracle consulted only here (AI-6 boundary)."""

from __future__ import annotations

from revive.domain.enums import ActionCode
from revive.domain.timestamps import VirtualTimestamp
from revive.simulation.oracle.resolve import OutcomeResult, resolve_outcome
from revive.simulation.types import AdapterResult

from revive.execution.environment import ExecutionEnvironment
from revive.execution.models import AuthorisedAction

_PAYMENT_ACTIONS = frozenset({ActionCode.A01, ActionCode.A02})
_MESSAGE_ACTIONS = frozenset(
    {
        ActionCode.A03,
        ActionCode.A04,
        ActionCode.A05,
        ActionCode.A06,
        ActionCode.A07,
        ActionCode.A08,
        ActionCode.A09,
        ActionCode.A10,
        ActionCode.A11,
    }
)
_VOICE_ACTIONS = frozenset({ActionCode.A12})
_HUMAN_ACTIONS = frozenset({ActionCode.A13, ActionCode.A14})


def supports(action_code: ActionCode) -> bool:
    return action_code != ActionCode.A00


def invoke(
    authorised: AuthorisedAction,
    env: ExecutionEnvironment,
    now_micros: int,
) -> OutcomeResult:
    """
    Invoke the simulated adapter for the authorised action.

    Returns oracle-resolved outcome — adapters never mutate REVIVE state.
    """
    action = authorised.action_code
    if action == ActionCode.A00:
        raise ValueError("NO_ACTION is not executable")

    if action in _HUMAN_ACTIONS:
        return _invoke_human(authorised, env, now_micros)

    return resolve_outcome(
        env.oracle_partition,
        authorised.opportunity_id,
        action,
        VirtualTimestamp(now_micros),
        contact_count=env.contact_count_for(env.customer_id),
        horizon_minutes=env.horizon_minutes,
        value_at_risk_paise=env.value_at_risk_paise,
        in_degradation_window=env.in_degradation_window,
    )


def reconcile(
    authorised: AuthorisedAction,
    env: ExecutionEnvironment,
    now_micros: int,
) -> OutcomeResult | None:
    """Reconcile TIMEOUT_UNKNOWN — re-query oracle boundary."""
    result = invoke(authorised, env, now_micros)
    if result.adapter_result == AdapterResult.TIMEOUT_UNKNOWN:
        return None
    return result


def _invoke_human(
    authorised: AuthorisedAction,
    env: ExecutionEnvironment,
    now_micros: int,
) -> OutcomeResult:
    """Human escalation — oracle models simulated handler outcome."""
    return resolve_outcome(
        env.oracle_partition,
        authorised.opportunity_id,
        authorised.action_code,
        VirtualTimestamp(now_micros),
        contact_count=env.contact_count_for(env.customer_id),
        horizon_minutes=env.horizon_minutes,
        value_at_risk_paise=env.value_at_risk_paise,
        in_degradation_window=env.in_degradation_window,
    )


def adapter_family(action_code: ActionCode) -> str:
    if action_code in _PAYMENT_ACTIONS:
        return "payment"
    if action_code in _MESSAGE_ACTIONS:
        return "message"
    if action_code in _VOICE_ACTIONS:
        return "voice"
    if action_code in _HUMAN_ACTIONS:
        return "human"
    return "unknown"
