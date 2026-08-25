"""Ledger settlement after adapter invocation — docs/15 §5."""

from __future__ import annotations

from revive.decision.ledger import ReservationLedger
from revive.decision.models import ResourceReservation, ReservationStatus
from revive.simulation.types import AdapterResult

from revive.execution.models import LedgerSettlement

_INCENTIVE_KEYS = frozenset({"incentive_budget", "incentive_allowance"})


def settle_reservations(
    adapter_result: AdapterResult,
    ledger: ReservationLedger,
    decision_id: str,
) -> tuple[LedgerSettlement, tuple[ResourceReservation, ...]]:
    """
    Commit or release reservations per closed outcome taxonomy.

    Returns settlement kind and consumed reservation rows.
    """
    if adapter_result == AdapterResult.REJECTED_BY_PROVIDER:
        ledger.release(decision_id)
        return LedgerSettlement.RELEASE, ()

    if adapter_result in {
        AdapterResult.FAILED_RETRYABLE,
        AdapterResult.FAILED_TERMINAL,
    }:
        committed = ledger.commit(decision_id)
        if committed is None:
            return LedgerSettlement.PARTIAL_COMMIT, ()
        return LedgerSettlement.PARTIAL_COMMIT, committed

    committed = ledger.commit(decision_id)
    if committed is None:
        return LedgerSettlement.COMMIT, ()
    return LedgerSettlement.COMMIT, committed


def realized_cost_paise(
    adapter_result: AdapterResult,
    predicted_cost_paise: int,
    reservations: tuple[ResourceReservation, ...],
) -> int:
    """Record realized execution cost — incentive released on certain failures."""
    if adapter_result == AdapterResult.REJECTED_BY_PROVIDER:
        return 0
    if adapter_result in {
        AdapterResult.FAILED_RETRYABLE,
        AdapterResult.FAILED_TERMINAL,
    }:
        incentive = sum(
            r.quantity
            for r in reservations
            if r.resource_key in _INCENTIVE_KEYS
        )
        return max(0, predicted_cost_paise - incentive)
    return predicted_cost_paise
