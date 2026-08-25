"""Valuation output models — docs/17 §4.3 ActionCandidate pricing fields."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from revive.domain.enums import ActionCode
from revive.simulation.observation import HIDDEN_KEYS


@dataclass(frozen=True, slots=True)
class CandidateValuation:
    """Prediction-layer valuation — distinct from realized outcomes."""

    valuation_id: str
    candidate_id: str
    opportunity_id: str
    cycle_id: str
    action_code: ActionCode
    p_action: float
    p_natural: float
    uplift: float
    sigma: float
    predictor_cell_ref: str
    shrinkage_level: int
    gross_paise: int
    cost_paise: int
    expected_incentive_paise: int
    fatigue_cost_paise: int
    enrv_paise: int
    enrv_lo_paise: int
    enrv_hi_paise: int
    valuation_version: str
    strategy_version: str
    provenance: tuple[str, ...]
    value_drivers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valuation_id": self.valuation_id,
            "candidate_id": self.candidate_id,
            "opportunity_id": self.opportunity_id,
            "cycle_id": self.cycle_id,
            "action_code": self.action_code.value,
            "p_action": self.p_action,
            "p_natural": self.p_natural,
            "uplift": self.uplift,
            "sigma": self.sigma,
            "predictor_cell_ref": self.predictor_cell_ref,
            "shrinkage_level": self.shrinkage_level,
            "gross_paise": self.gross_paise,
            "cost_paise": self.cost_paise,
            "expected_incentive_paise": self.expected_incentive_paise,
            "fatigue_cost_paise": self.fatigue_cost_paise,
            "enrv_paise": self.enrv_paise,
            "enrv_lo_paise": self.enrv_lo_paise,
            "enrv_hi_paise": self.enrv_hi_paise,
            "valuation_version": self.valuation_version,
            "strategy_version": self.strategy_version,
            "provenance": list(self.provenance),
            "value_drivers": list(self.value_drivers),
        }

    def hidden_keys(self) -> list[str]:
        found: list[str] = []
        stack: list[Any] = [self.to_dict()]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                for key, value in item.items():
                    if key in HIDDEN_KEYS:
                        found.append(key)
                    stack.append(value)
            elif isinstance(item, list):
                stack.extend(item)
        return found

    def component_sum_paise(self) -> int:
        return (
            self.gross_paise
            - self.cost_paise
            - self.expected_incentive_paise
            - self.fatigue_cost_paise
        )


@dataclass(frozen=True, slots=True)
class ValuationResult:
    opportunity_id: str
    cycle_id: str
    produced_at_micros: int
    valuations: tuple[CandidateValuation, ...]
    valuation_version: str
    strategy_version: str
    p_natural: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "cycle_id": self.cycle_id,
            "produced_at_micros": self.produced_at_micros,
            "valuations": [v.to_dict() for v in self.valuations],
            "valuation_version": self.valuation_version,
            "strategy_version": self.strategy_version,
            "p_natural": self.p_natural,
        }
