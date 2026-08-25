"""Recall against generator economic losses — development validation only."""

from revive.recovery.sentinel import detect
from revive.simulation import generate_dataset
from revive.simulation.fixtures import tiny_config
from revive.simulation.observation import get_observable_state


def _refs(linked: dict) -> set[str]:
    return {v for v in linked.values() if v}


def test_sentinel_recalls_generator_economic_losses():
    dataset = generate_dataset(tiny_config(seed=4))
    world = get_observable_state(dataset.world)
    now = max(o.first_detected_at_micros for o in dataset.world.opportunities) + 1
    result = detect(world, now)

    detected_refs = set()
    for opp in result.opportunities:
        detected_refs.update(_refs(opp.evidence.source_refs))

    missing = []
    for gen in dataset.world.opportunities:
        refs = _refs(gen.linked_refs)
        if refs and refs.isdisjoint(detected_refs):
            missing.append((gen.opportunity_id, gen.risk_class, gen.linked_refs))
    assert missing == []
    assert result.metrics.opportunities_detected >= 1
    assert result.metrics.value_at_risk_total_paise > 0
