"""M13.7 thesis audit tests."""

from revive.benchmark.calibration.thesis_audit.cycle import official_scale_dataset, build_cycle_snapshot
from revive.benchmark.calibration.thesis_audit.analyze import analyze_cycle
from revive.benchmark.calibration.thesis_audit.runner import run_m13_7_audit
from revive.simulation.types import GenerationProfile


def test_official_scale_audit_runs():
    dataset = official_scale_dataset(1, GenerationProfile.BALANCED)
    snap = build_cycle_snapshot(dataset)
    cell = analyze_cycle(snap)
    assert cell.opportunities_in_cycle > 0
    assert cell.b3_total_enrv == cell.revive_total_enrv


def test_m13_7_full_audit_smoke():
    report = run_m13_7_audit()
    assert report.official_scale_cells
    assert report.config_matrix
    assert report.thesis_classification == "THESIS CONFIGURATION-DEPENDENT"
