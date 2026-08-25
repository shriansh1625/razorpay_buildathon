"""
Synthetic revenue environment — generator and hidden outcome oracle (M2).

Oracle partition is isolated from the decision path (AI-6).
"""

from revive.simulation.config import GENERATOR_VERSION, GeneratorConfig
from revive.simulation.generator import GeneratedDataset, generate_dataset
from revive.simulation.manifest import DatasetManifest, build_manifest
from revive.simulation.observation import ObservableWorldView, get_observable_state
from revive.simulation.replay import replay_dataset
from revive.simulation.types import GenerationProfile
from revive.simulation.validation import assert_dataset_valid, validate_dataset

__all__ = [
    "GENERATOR_VERSION",
    "GeneratorConfig",
    "GenerationProfile",
    "GeneratedDataset",
    "generate_dataset",
    "DatasetManifest",
    "build_manifest",
    "ObservableWorldView",
    "get_observable_state",
    "replay_dataset",
    "assert_dataset_valid",
    "validate_dataset",
]
