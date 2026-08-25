"""Measurement boundary integrity — oracle isolation."""

import pkgutil

from revive.integrity import assert_decision_path_does_not_import_oracle


def test_decision_path_still_no_oracle():
    assert_decision_path_does_not_import_oracle()


def test_measurement_reference_not_in_decision_path():
    forbidden: list[str] = []
    import revive

    for mod in pkgutil.walk_packages(revive.__path__, prefix="revive."):
        if mod.name.startswith("revive.measurement"):
            continue
        if mod.name.startswith("revive.execution"):
            continue
        if mod.name.startswith("revive.simulation"):
            continue
        if mod.name.startswith("revive.benchmark"):
            continue
        try:
            imported = __import__(mod.name, fromlist=["_dummy"])
        except ImportError:
            continue
        path = getattr(imported, "__file__", "") or ""
        if not path.endswith(".py"):
            continue
        text = open(path, encoding="utf-8").read()
        if "revive.measurement.reference" in text:
            forbidden.append(mod.name)
    assert forbidden == []


def test_measurement_result_no_oracle_internals():
    from tests.measurement.helpers import execute_and_measure

    _, m, _, _ = execute_and_measure()
    payload = m.to_dict()
    for key in (
        "per_action_response",
        "fatigue_curve",
        "latent_traits",
        "oracle_row",
    ):
        assert key not in str(payload)
