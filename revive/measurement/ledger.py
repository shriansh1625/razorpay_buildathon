"""Opportunity-level recovery ledger — prevents double counting (AT-2, LK-4)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OpportunityRecoveryLedger:
    """Track recovery already attributed per opportunity."""

    _gross_counted: dict[str, int] = field(default_factory=dict)
    _execution_count: dict[str, int] = field(default_factory=dict)

    def recovery_already_counted(self, opportunity_id: str) -> bool:
        return self._gross_counted.get(opportunity_id, 0) > 0

    def record_recovery(self, opportunity_id: str, gross_paise: int) -> None:
        if gross_paise <= 0:
            return
        self._gross_counted[opportunity_id] = (
            self._gross_counted.get(opportunity_id, 0) + gross_paise
        )

    def record_execution(self, opportunity_id: str) -> int:
        count = self._execution_count.get(opportunity_id, 0) + 1
        self._execution_count[opportunity_id] = count
        return count

    def execution_count(self, opportunity_id: str) -> int:
        return self._execution_count.get(opportunity_id, 0)

    def gross_counted(self, opportunity_id: str) -> int:
        return self._gross_counted.get(opportunity_id, 0)
