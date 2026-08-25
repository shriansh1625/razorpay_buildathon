"""Resource reservation ledger — single authority for M9 intent records."""

from __future__ import annotations

from dataclasses import dataclass, field

from revive.decision.models import ResourceReservation, ReservationStatus


@dataclass
class ReservationLedger:
    """In-memory reservation ledger — idempotent per decision_id."""

    _active: dict[str, tuple[ResourceReservation, ...]] = field(default_factory=dict)
    _released: set[str] = field(default_factory=set)
    _committed: dict[str, tuple[ResourceReservation, ...]] = field(default_factory=dict)

    def has_active(self, decision_id: str) -> bool:
        return decision_id in self._active and decision_id not in self._released

    def is_committed(self, decision_id: str) -> bool:
        return decision_id in self._committed

    def commit(self, decision_id: str) -> tuple[ResourceReservation, ...] | None:
        """Mark reservations consumed — idempotent per decision_id."""
        if decision_id in self._committed:
            return self._committed[decision_id]
        if not self.has_active(decision_id):
            return None
        committed = tuple(
            ResourceReservation(
                reservation_id=r.reservation_id,
                decision_id=r.decision_id,
                cycle_id=r.cycle_id,
                resource_key=r.resource_key,
                quantity=r.quantity,
                customer_id=r.customer_id,
                reserved_at_micros=r.reserved_at_micros,
                expires_at_micros=r.expires_at_micros,
                status=ReservationStatus.COMMITTED,
            )
            for r in self._active[decision_id]
        )
        self._committed[decision_id] = committed
        del self._active[decision_id]
        return committed

    def reserve(
        self,
        reservations: tuple[ResourceReservation, ...],
    ) -> tuple[ResourceReservation, ...]:
        decision_id = reservations[0].decision_id if reservations else ""
        if not decision_id:
            return ()
        if decision_id in self._active:
            return self._active[decision_id]
        for other_id, existing in self._active.items():
            if other_id == decision_id or other_id in self._released:
                continue
            for new_res in reservations:
                for old_res in existing:
                    if new_res.resource_key != old_res.resource_key:
                        continue
                    if new_res.resource_key == "contact_allowance":
                        if (
                            new_res.customer_id
                            and old_res.customer_id == new_res.customer_id
                        ):
                            raise ValueError(
                                f"contact allowance conflict: {decision_id} vs {other_id}"
                            )
                    elif new_res.quantity > 0 and old_res.quantity > 0:
                        raise ValueError(
                            f"resource conflict on {new_res.resource_key}: "
                            f"{decision_id} vs {other_id}"
                        )
        self._active[decision_id] = reservations
        return reservations

    def release(self, decision_id: str) -> bool:
        if decision_id not in self._active:
            return False
        if decision_id in self._released:
            return False
        released = tuple(
            ResourceReservation(
                reservation_id=r.reservation_id,
                decision_id=r.decision_id,
                cycle_id=r.cycle_id,
                resource_key=r.resource_key,
                quantity=r.quantity,
                customer_id=r.customer_id,
                reserved_at_micros=r.reserved_at_micros,
                expires_at_micros=r.expires_at_micros,
                status=ReservationStatus.RELEASED,
            )
            for r in self._active[decision_id]
        )
        self._active[decision_id] = released
        self._released.add(decision_id)
        return True

    def active_reservations(self) -> tuple[ResourceReservation, ...]:
        rows: list[ResourceReservation] = []
        for decision_id, res in self._active.items():
            if decision_id in self._released:
                continue
            rows.extend(res)
        return tuple(rows)
