"""M13.13 feasibility gate tests (revised 31-cell matrix)."""

import pytest

from revive.benchmark.official.cells.plan import (
    OFFICIAL_FROZEN_CELL_TOTAL,
    plan_feasibility_cells_m13_13,
)
from revive.benchmark.official.feasibility.gate import (
    FEASIBILITY_LABEL,
    FEASIBILITY_MATRIX_CELLS,
    _project_official_600,
    _revive_runtime_stats,
    feasibility_benchmark_config,
)
from revive.config.policy_pack import official_sealed_policy_pack


def test_feasibility_matrix_is_31_cells():
    pack = official_sealed_policy_pack()
    config = feasibility_benchmark_config(policy_pack=pack)
    cells = plan_feasibility_cells_m13_13(config)
    assert len(cells) == FEASIBILITY_MATRIX_CELLS == 31
    assert cells[0].seed == 1
    assert cells[-1].seed == 2
    assert cells[-1].profile == "BALANCED"
    assert cells[-1].policy_id == "REVIVE"
    assert OFFICIAL_FROZEN_CELL_TOTAL == 600


def test_feasibility_label():
    assert FEASIBILITY_LABEL == "DEVELOPMENT_FEASIBILITY_ONLY"


def test_revive_projection_math():
    records = [
        {"policy": "REVIVE", "completion_status": "completed", "elapsed_seconds": 600.0},
        {"policy": "REVIVE", "completion_status": "completed", "elapsed_seconds": 700.0},
        {"policy": "B0", "completion_status": "completed", "elapsed_seconds": 25.0},
    ]
    rs = _revive_runtime_stats(records)
    assert rs["median_seconds"] == 650.0
    assert rs["projected_120_revive_median_seconds"] == 650.0 * 120


def test_project_official_600():
    records = [
        {"policy": "REVIVE", "completion_status": "completed", "elapsed_seconds": 600.0},
        {"policy": "REVIVE", "completion_status": "completed", "elapsed_seconds": 800.0},
        {"policy": "B0", "completion_status": "completed", "elapsed_seconds": 30.0},
        {"policy": "B1", "completion_status": "completed", "elapsed_seconds": 30.0},
    ]
    p = _project_official_600(records)
    assert p["official_cell_total"] == 600
    assert p["projected_600_median_hours"] > 0
