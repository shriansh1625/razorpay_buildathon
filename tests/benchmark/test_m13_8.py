"""M13.8 freeze decision smoke test."""

from revive.benchmark.calibration.m13_8.config_candidates import CONFIG_B
from revive.benchmark.calibration.m13_8.runner import (
    _aggregate_by_candidate,
    _benchmark_computational_sample,
    _run_calibration_matrix,
)
from revive.simulation.generator import generate_dataset
from revive.simulation.types import GenerationProfile


def test_config_b_generates():
    cfg = CONFIG_B.generator_config(1, GenerationProfile.BALANCED)
    dataset = generate_dataset(cfg)
    assert dataset.config.simulation_window_days == 21
    assert dataset.config.opportunity_count == 500


def test_computational_sample():
    sample = _benchmark_computational_sample("B")
    assert sample.dataset_generation_sec > 0
