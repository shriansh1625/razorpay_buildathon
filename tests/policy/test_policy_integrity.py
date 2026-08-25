"""Oracle isolation for policy engine."""

import inspect

from revive.integrity import assert_decision_path_does_not_import_oracle
from revive.policy.authorize import authorize_execution as authorize_fn


def test_policy_modules_no_oracle():
    assert_decision_path_does_not_import_oracle()


def test_authorize_does_not_allocate_or_execute():
    source = inspect.getsource(authorize_fn)
    assert "allocate_portfolio" not in source
    assert "ExecutionAgent" not in source
    assert "adapter.invoke" not in source
