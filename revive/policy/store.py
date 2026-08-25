"""Authorization store — idempotency and immutable authorization history."""

from __future__ import annotations

from dataclasses import dataclass, field

from revive.policy.models import ExecutionAuthorization


@dataclass
class AuthorizationStore:
    """Tracks authorizations and idempotency claims — no duplicate execution identities."""

    _authorizations: dict[str, ExecutionAuthorization] = field(default_factory=dict)
    _idempotency_claimed: set[str] = field(default_factory=set)
    _audit_log: list[dict] = field(default_factory=list)

    def record(self, authorization: ExecutionAuthorization) -> ExecutionAuthorization:
        existing = self._authorizations.get(authorization.authorization_id)
        if existing is not None:
            if existing.to_dict() == authorization.to_dict():
                return existing
            if authorization.blocking_reason_code == "DUPLICATE_IDEMPOTENCY":
                return authorization
            raise ValueError(f"authorization id collision: {authorization.authorization_id}")

        if authorization.authorization_state.value == "AUTHORIZED":
            if authorization.idempotency_key in self._idempotency_claimed:
                raise ValueError("duplicate authorized idempotency key")
            self._idempotency_claimed.add(authorization.idempotency_key)

        self._authorizations[authorization.authorization_id] = authorization
        self._audit_log.append(
            {
                "authorization_id": authorization.authorization_id,
                "decision_id": authorization.decision_id,
                "state": authorization.authorization_state.value,
                "blocking_reason": authorization.blocking_reason_code,
            }
        )
        return authorization

    def get(self, authorization_id: str) -> ExecutionAuthorization | None:
        return self._authorizations.get(authorization_id)

    def is_idempotency_claimed(self, idempotency_key: str) -> bool:
        return idempotency_key in self._idempotency_claimed

    def claim_idempotency(self, idempotency_key: str) -> bool:
        if idempotency_key in self._idempotency_claimed:
            return False
        self._idempotency_claimed.add(idempotency_key)
        return True
