"""M13.5 calibration smoke tests."""

from pathlib import Path

from revive.benchmark.calibration import run_calibration_diagnostics, write_calibration_reports
from revive.benchmark.calibration.config import calibration_config
from revive.benchmark.calibration.environment import analyze_environment
from revive.simulation.generator import generate_dataset
from revive.simulation.types import GenerationProfile


def test_environment_diagnostics_single_cell():
    dataset = generate_dataset(calibration_config(1, GenerationProfile.BALANCED))
    cell = analyze_environment(dataset)
    assert cell.opportunity_count > 0
    assert cell.gross_value_at_risk_paise > 0


def test_calibration_runner_smoke():
    report = run_calibration_diagnostics(
        seeds=(1,),
        profiles=(GenerationProfile.BALANCED,),
        skip_reproduction=True,
    )
    assert report.baseline_separation is not None
    assert report.freeze_readiness is not None
    assert report.freeze_readiness.decision.startswith("NOT READY")


def test_calibration_reports_written(tmp_path: Path):
    report = run_calibration_diagnostics(
        seeds=(1,),
        profiles=(GenerationProfile.BALANCED,),
        skip_reproduction=True,
    )
    out = write_calibration_reports(report, tmp_path)
    assert (out / "M13.5-decision.md").exists()
    assert (out / "freeze-readiness.md").exists()
