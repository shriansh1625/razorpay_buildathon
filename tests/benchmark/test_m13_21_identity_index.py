"""M13.21 cycle-local world identity index tests."""

from revive.benchmark.official.config import generator_config_for_cell, official_benchmark_config
from revive.config.policy_pack import official_sealed_policy_pack
from revive.recovery.sentinel.identity_bridge import (
    index_world_opportunities_by_natural_key,
    resolve_world_opportunity_id_by_natural_key,
)
from revive.simulation.observation import get_observable_state
from revive.simulation.types import GenerationProfile
from revive.benchmark.official.world import generate_shared_world


def test_world_index_matches_linear_resolve():
    pack = official_sealed_policy_pack()
    config = official_benchmark_config(policy_pack=pack)
    gen = generator_config_for_cell(config, 2, GenerationProfile.BALANCED)
    bundle = generate_shared_world(gen)
    view = get_observable_state(bundle.world)
    index = index_world_opportunities_by_natural_key(view)

    for nk, wid in index.items():
        assert resolve_world_opportunity_id_by_natural_key(nk, view) == wid
        assert resolve_world_opportunity_id_by_natural_key(nk, view, world_index=index) == wid
