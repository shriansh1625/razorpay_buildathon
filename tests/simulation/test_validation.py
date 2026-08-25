"""Dataset validation and replay tests."""

from revive.simulation import assert_dataset_valid, generate_dataset, replay_dataset
from revive.simulation.fixtures import tiny_config
from revive.simulation.io import write_dataset
from revive.simulation.replay import replay_dataset as replay_fn


def test_dataset_passes_invariants():
    dataset = generate_dataset(tiny_config())
    assert_dataset_valid(dataset)


def test_replay_matches_original():
    config = tiny_config(seed=33)
    original = generate_dataset(config)
    replayed = replay_fn(config)
    assert original.dataset_hash == replayed.dataset_hash


def test_write_dataset_creates_manifest(tmp_path):
    dataset = generate_dataset(tiny_config())
    out = write_dataset(dataset, tmp_path / "ds")
    assert (out / "manifest.json").exists()
    assert (out / "oracle" / "partition.json").exists()
    assert (out / "distributions.json").exists()
