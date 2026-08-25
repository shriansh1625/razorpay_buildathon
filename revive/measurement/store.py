"""Idempotent measurement store."""

from __future__ import annotations

from dataclasses import dataclass, field

from revive.measurement.models import RecoveryMeasurement


@dataclass
class MeasurementStore:
    """One execution → one measurement — idempotent by measurement_id."""

    _by_id: dict[str, RecoveryMeasurement] = field(default_factory=dict)
    _by_execution: dict[str, RecoveryMeasurement] = field(default_factory=dict)

    def get(self, measurement_id: str) -> RecoveryMeasurement | None:
        return self._by_id.get(measurement_id)

    def get_by_execution(self, execution_id: str) -> RecoveryMeasurement | None:
        return self._by_execution.get(execution_id)

    def record(self, measurement: RecoveryMeasurement) -> RecoveryMeasurement:
        existing = self._by_execution.get(measurement.provenance.execution_id)
        if existing is not None:
            return existing
        self._by_id[measurement.measurement_id] = measurement
        self._by_execution[measurement.provenance.execution_id] = measurement
        return measurement

    def all_measurements(self) -> tuple[RecoveryMeasurement, ...]:
        return tuple(self._by_id.values())
