"""AuthorisedAction minting — only AUTHORIZED executions may proceed."""

from __future__ import annotations

from revive.policy.models import AuthorizationState, ExecutionAuthorization

from revive.execution.models import AuthorisedAction


def mint_authorised_action(authorization: ExecutionAuthorization) -> AuthorisedAction:
    """
  Mint a type-safe execution token from an authorization artifact.

  Raises ValueError if authorization_state is not AUTHORIZED.
  """
    if authorization.authorization_state != AuthorizationState.AUTHORIZED:
        raise ValueError(
            f"cannot mint AuthorisedAction: state={authorization.authorization_state.value}"
        )
    return AuthorisedAction(
        authorization_id=authorization.authorization_id,
        decision_id=authorization.decision_id,
        opportunity_id=authorization.opportunity_id,
        candidate_id=authorization.candidate_id,
        action_code=authorization.action_code,
        authorized_parameters=dict(authorization.authorized_parameters),
        idempotency_key=authorization.idempotency_key,
        configuration_hash=authorization.configuration_hash,
        authorization_version=authorization.authorization_version,
        policy_pack_version=authorization.policy_pack_version,
        allocator_version=authorization.allocator_version,
        valuation_version=authorization.valuation_version,
        expires_at_micros=authorization.expires_at_micros,
        enrv_paise=authorization.enrv_paise,
        audit_reference=authorization.audit_reference,
    )
