"""Policy engine — deterministic gates + stopping rules (M10)."""

from revive.policy.authorize import authorize_execution, authorization_id_for
from revive.policy.config import (
    AUTHORIZATION_VERSION,
    PolicyRules,
    default_policy_rules,
)
from revive.policy.context import AuthorizeContext
from revive.policy.models import (
    AuthorizationState,
    ExecutionAuthorization,
    GateResult,
    StoppingRuleResult,
)
from revive.policy.store import AuthorizationStore

__all__ = [
    "AUTHORIZATION_VERSION",
    "AuthorizationState",
    "AuthorizeContext",
    "ExecutionAuthorization",
    "GateResult",
    "StoppingRuleResult",
    "PolicyRules",
    "AuthorizationStore",
    "default_policy_rules",
    "authorize_execution",
    "authorization_id_for",
]
