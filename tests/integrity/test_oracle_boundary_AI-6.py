"""Architectural integrity tests."""

import importlib

from revive.benchmark import ORACLE_MODULE
from revive.integrity import assert_decision_path_does_not_import_oracle


def test_oracle_module_exists_for_m2():
    mod = importlib.import_module(ORACLE_MODULE)
    assert hasattr(mod, "resolve_outcome")


def test_decision_path_oracle_boundary():
    assert_decision_path_does_not_import_oracle()


def test_action_code_count():
    from revive.domain.enums import ActionCode

    assert len(ActionCode) == 15
