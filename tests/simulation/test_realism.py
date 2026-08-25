"""Distribution realism smoke tests."""

from revive.domain.enums import RiskClass
from revive.simulation import generate_dataset
from revive.simulation.fixtures import tiny_config


def test_multiple_risk_classes_present():
    dataset = generate_dataset(tiny_config(seed=8))
    classes = {o.risk_class for o in dataset.world.opportunities}
    assert len(classes) >= 3


def test_payment_failure_class_present():
    dataset = generate_dataset(tiny_config())
    assert any(o.risk_class == RiskClass.PAYMENT_FAILURE for o in dataset.world.opportunities)


def test_customer_heterogeneity():
    dataset = generate_dataset(tiny_config(seed=12))
    segments = {c.segment for c in dataset.world.customers}
    assert len(segments) >= 2
