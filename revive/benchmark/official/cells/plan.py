"""Benchmark cell planning — M13.11."""

from __future__ import annotations

from dataclasses import dataclass, replace

from revive.benchmark.official.config import OfficialBenchmarkConfig
from revive.benchmark.official.policies import ALL_BENCHMARK_POLICIES


@dataclass(frozen=True, slots=True)
class BenchmarkCell:
    """One seed × profile × policy evaluation."""

    index: int
    seed: int
    profile: str
    policy_id: str

    @property
    def key(self) -> tuple[int, str, str]:
        return (self.seed, self.profile, self.policy_id)

    def to_dict(self) -> dict[str, int | str]:
        return {
            "index": self.index,
            "seed": self.seed,
            "profile": self.profile,
            "policy_id": self.policy_id,
        }


@dataclass(frozen=True, slots=True)
class BenchmarkGroup:
    """One seed × profile group — shared world, five policy cells."""

    seed: int
    profile: str
    cells: tuple[BenchmarkCell, ...]

    @property
    def key(self) -> tuple[int, str]:
        return (self.seed, self.profile)


def plan_benchmark_groups(
    cells: tuple[BenchmarkCell, ...],
) -> tuple[BenchmarkGroup, ...]:
    """Partition planned cells into seed/profile groups preserving policy order."""
    groups: list[BenchmarkGroup] = []
    index = 0
    while index < len(cells):
        seed = cells[index].seed
        profile = cells[index].profile
        group_cells: list[BenchmarkCell] = []
        while index < len(cells) and cells[index].seed == seed and cells[index].profile == profile:
            group_cells.append(cells[index])
            index += 1
        groups.append(BenchmarkGroup(seed=seed, profile=profile, cells=tuple(group_cells)))
    return tuple(groups)


def plan_benchmark_cells(
    config: OfficialBenchmarkConfig,
    *,
    seeds: tuple[int, ...] | None = None,
    max_cells: int | None = None,
) -> tuple[BenchmarkCell, ...]:
    """Canonical execution order: seed → profile → policy."""
    cells: list[BenchmarkCell] = []
    index = 0
    seed_set = seeds if seeds is not None else config.seed_set
    for seed in seed_set:
        for profile in config.profile_set:
            profile_value = profile.value
            for policy in ALL_BENCHMARK_POLICIES:
                index += 1
                cells.append(
                    BenchmarkCell(
                        index=index,
                        seed=seed,
                        profile=profile_value,
                        policy_id=policy.value,
                    )
                )
                if max_cells is not None and len(cells) >= max_cells:
                    return tuple(cells)
    return tuple(cells)


def plan_feasibility_cells_m13_13(
    config: OfficialBenchmarkConfig,
) -> tuple[BenchmarkCell, ...]:
    """M13.13 revised matrix: seed=1 × 6 profiles × 5 policies + stress REVIVE."""
    seed_one = replace(config, seed_set=(1,))
    cells = list(plan_benchmark_cells(seed_one))
    stress = BenchmarkCell(
        index=len(cells) + 1,
        seed=2,
        profile="BALANCED",
        policy_id="REVIVE",
    )
    cells.append(stress)
    return tuple(cells)


def official_cell_total(config: OfficialBenchmarkConfig) -> int:
    return (
        len(config.seed_set)
        * len(config.profile_set)
        * len(ALL_BENCHMARK_POLICIES)
    )


OFFICIAL_FROZEN_CELL_TOTAL = 20 * 6 * len(ALL_BENCHMARK_POLICIES)
