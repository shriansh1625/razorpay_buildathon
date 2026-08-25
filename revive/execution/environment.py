"""Execution environment — oracle partition at adapter boundary only."""

from __future__ import annotations

from dataclasses import dataclass, field

from revive.domain.enums import OpportunityState
from revive.simulation.oracle._partition import OraclePartition
from revive.simulation.world import SyntheticWorld

from revive.execution.config import DEFAULT_HORIZON_MINUTES


@dataclass
class ExecutionEnvironment:
    """
    Simulator context for M11 adapters.

    The oracle partition is only reachable through execution adapters — not
    through decision-path modules.
    """

    oracle_partition: OraclePartition
    world: SyntheticWorld | None = None
    contact_counts: dict[str, int] = field(default_factory=dict)
    horizon_minutes: int = DEFAULT_HORIZON_MINUTES
    value_at_risk_paise: int = 0
    customer_id: str | None = None
    opportunity_state: OpportunityState = OpportunityState.AUTHORISED
    in_degradation_window: bool = False

    def contact_count_for(self, customer_id: str | None) -> int:
        if not customer_id:
            return 0
        return self.contact_counts.get(customer_id, 0)

    def increment_contact(self, customer_id: str | None) -> None:
        if customer_id:
            self.contact_counts[customer_id] = self.contact_count_for(customer_id) + 1
