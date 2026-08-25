"""Oracle isolation and leakage tests (AI-6)."""

import pytest

from revive.integrity import assert_decision_path_does_not_import_oracle
from revive.simulation import generate_dataset, get_observable_state
from revive.simulation.config import GeneratorConfig
from revive.simulation.fixtures import tiny_config
from revive.simulation.oracle import resolve_outcome
from revive.simulation.oracle._partition import OraclePartition


def test_decision_path_does_not_import_oracle():
    assert_decision_path_does_not_import_oracle()


def test_observable_state_has_no_hidden_keys():
    dataset = generate_dataset(tiny_config())
    view = get_observable_state(dataset.world)
    assert view.contains_hidden_keys() == []


def test_oracle_partition_not_in_observable_manifest():
    dataset = generate_dataset(tiny_config())
    observable = get_observable_state(dataset.world).as_dict()
    assert "latent_traits" not in observable
    assert "per_action_response" not in str(observable)


def test_resolve_outcome_requires_partition():
    partition = OraclePartition()
    with pytest.raises(KeyError):
        resolve_outcome(
            partition,
            "missing",
            __import__("revive.domain.enums", fromlist=["ActionCode"]).ActionCode.A01,
            __import__("revive.domain.timestamps", fromlist=["VirtualTimestamp"]).VirtualTimestamp(0),
            horizon_minutes=60,
            value_at_risk_paise=1000,
        )
