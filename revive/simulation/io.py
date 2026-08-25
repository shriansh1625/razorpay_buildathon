"""Dataset serialization to artefacts directory."""

from __future__ import annotations

import json
from pathlib import Path

from revive.simulation.distributions import compute_distributions
from revive.simulation.generator import GeneratedDataset
from revive.simulation.manifest import build_manifest
from revive.simulation.observation import _record_dict, get_observable_state


def write_dataset(dataset: GeneratedDataset, output_dir: Path) -> Path:
    """Write manifest, domain, signals, oracle partition, distributions separately."""
    output_dir.mkdir(parents=True, exist_ok=True)
    domain_dir = output_dir / "domain"
    oracle_dir = output_dir / "oracle"
    domain_dir.mkdir(exist_ok=True)
    oracle_dir.mkdir(exist_ok=True)

    manifest = build_manifest(dataset.config, dataset.world, dataset.dataset_hash)
    (output_dir / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")

    observable = get_observable_state(dataset.world)
    (domain_dir / "observable_world.json").write_text(
        json.dumps(observable.as_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    signals = [_record_dict(s) for s in dataset.world.signals]
    with (output_dir / "signals.ndjson").open("w", encoding="utf-8") as fh:
        for sig in signals:
            fh.write(json.dumps(sig) + "\n")

    (oracle_dir / "partition.json").write_text(
        json.dumps(dataset.oracle_partition.to_dict(), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    distributions = compute_distributions(dataset)
    (output_dir / "distributions.json").write_text(distributions.to_json(), encoding="utf-8")

    if dataset.world.privacy_canaries:
        canaries = [_record_dict(c) for c in dataset.world.privacy_canaries]
        (output_dir / "canaries.json").write_text(json.dumps(canaries, indent=2), encoding="utf-8")

    if dataset.world.adversarial_case_ids:
        (output_dir / "injections.json").write_text(
            json.dumps(list(dataset.world.adversarial_case_ids), indent=2),
            encoding="utf-8",
        )

    return output_dir


def load_oracle_partition(path: Path):
    from revive.simulation.oracle._partition import OraclePartition

    data = json.loads((path / "oracle" / "partition.json").read_text(encoding="utf-8"))
    return OraclePartition.from_dict(data)
