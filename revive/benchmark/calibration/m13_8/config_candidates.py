"""M13.8 benchmark configuration candidates."""

from __future__ import annotations

from dataclasses import dataclass

from revive.simulation.config import GeneratorConfig
from revive.simulation.types import GenerationProfile

# Representative multi-seed sample for M13.8 calibration (official set is 1–20).
M13_8_CALIBRATION_SEEDS: tuple[int, ...] = (1, 2, 3, 4, 5)
M13_8_VERSION = "0.13.8-m13.8"


@dataclass(frozen=True, slots=True)
class HorizonCandidate:
    id: str
    label: str
    simulation_window_days: int
    opportunity_count: int
    customer_count: int
    cycle_interval_minutes: int = 15

    def generator_config(self, seed: int, profile: GenerationProfile) -> GeneratorConfig:
        return GeneratorConfig(
            seed=seed,
            profile=profile,
            merchant_count=1,
            customer_count=self.customer_count,
            opportunity_count=self.opportunity_count,
            simulation_window_days=self.simulation_window_days,
            cycle_interval_minutes=self.cycle_interval_minutes,
            inject_signal_faults=True,
            inject_adversarial_cases=False,
            privacy_canary_count=3,
        )


CONFIG_A = HorizonCandidate(
    id="A",
    label="500 opps / 100 customers / 30-day window",
    simulation_window_days=30,
    opportunity_count=500,
    customer_count=100,
)

CONFIG_B = HorizonCandidate(
    id="B",
    label="500 opps / 100 customers / 21-day window (calibration scale)",
    simulation_window_days=21,
    opportunity_count=500,
    customer_count=100,
)

HORIZON_CANDIDATES: tuple[HorizonCandidate, ...] = (CONFIG_A, CONFIG_B)
