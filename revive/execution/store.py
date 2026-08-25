"""Idempotent execution store."""

from __future__ import annotations

from dataclasses import dataclass, field

from revive.execution.models import ExecutionResult, ExecutionStage


@dataclass
class ExecutionStore:
    """Claim idempotency keys and persist execution results."""

    _by_idempotency: dict[str, ExecutionResult] = field(default_factory=dict)
    _by_execution_id: dict[str, ExecutionResult] = field(default_factory=dict)
    _claimed: set[str] = field(default_factory=set)

    def is_claimed(self, idempotency_key: str) -> bool:
        return idempotency_key in self._claimed or idempotency_key in self._by_idempotency

    def claim(self, idempotency_key: str) -> bool:
        """Atomic claim — returns False if already claimed."""
        if self.is_claimed(idempotency_key):
            return False
        self._claimed.add(idempotency_key)
        return True

    def get_by_idempotency(self, idempotency_key: str) -> ExecutionResult | None:
        return self._by_idempotency.get(idempotency_key)

    def record(self, result: ExecutionResult) -> ExecutionResult:
        existing = self._by_idempotency.get(result.idempotency_key)
        if existing is not None:
            if existing.execution_stage == ExecutionStage.SCHEDULED:
                if result.execution_stage != ExecutionStage.SCHEDULED:
                    self._by_idempotency[result.idempotency_key] = result
                    self._by_execution_id[result.execution_id] = result
                    return result
                return existing
            return existing
        self._by_idempotency[result.idempotency_key] = result
        self._by_execution_id[result.execution_id] = result
        self._claimed.add(result.idempotency_key)
        return result

    def get(self, execution_id: str) -> ExecutionResult | None:
        return self._by_execution_id.get(execution_id)
