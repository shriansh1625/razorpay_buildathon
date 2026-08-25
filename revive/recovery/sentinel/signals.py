"""Signal ingestion and quarantine (C-01, RR-FUNC-004/005)."""

from __future__ import annotations

from typing import Any

from revive.domain.enums import SignalType
from revive.recovery.sentinel.models import QuarantineRecord

# Generator emits `{RiskClass}_SIGNAL`; also accept documented types from docs/12 §3.1.
_GENERATOR_TYPES = frozenset(
    {
        "PAYMENT_FAILURE_SIGNAL",
        "CHECKOUT_ABANDONMENT_SIGNAL",
        "SUBSCRIPTION_FAILURE_SIGNAL",
        "RECEIVABLE_OVERDUE_SIGNAL",
        "MANDATE_HEALTH_SIGNAL",
    }
)

KNOWN_SIGNAL_TYPES = frozenset(item.value for item in SignalType) | _GENERATOR_TYPES


def ingest_signals(
    raw_signals: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    now_micros: int,
) -> tuple[list[dict[str, Any]], list[QuarantineRecord], int]:
    """
    Validate, dedupe, and drop future-only events.

    Returns (accepted, quarantined, skipped_future_count).
    """
    accepted: list[dict[str, Any]] = []
    quarantined: list[QuarantineRecord] = []
    seen_hashes: set[str] = set()
    skipped_future = 0

    for raw in raw_signals:
        signal_id = raw.get("signal_id")
        received = int(raw.get("received_at_micros") or 0)
        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}

        missing = [
            field
            for field in ("signal_id", "signal_type", "dedupe_hash", "occurred_at_micros")
            if raw.get(field) in (None, "")
        ]
        if missing:
            quarantined.append(
                QuarantineRecord(
                    signal_id=str(signal_id) if signal_id else None,
                    rejection_reason=f"MISSING_FIELDS:{','.join(missing)}",
                    received_at_micros=received,
                    raw_payload=dict(raw) if isinstance(raw, dict) else {},
                )
            )
            continue

        signal_type = str(raw["signal_type"])
        if signal_type not in KNOWN_SIGNAL_TYPES:
            quarantined.append(
                QuarantineRecord(
                    signal_id=str(signal_id),
                    rejection_reason="UNKNOWN_SIGNAL_TYPE",
                    received_at_micros=received,
                    raw_payload=dict(raw),
                )
            )
            continue

        occurred = int(raw["occurred_at_micros"])
        if occurred > now_micros:
            skipped_future += 1
            continue

        amount = payload.get("amount_paise")
        if amount is not None:
            if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
                quarantined.append(
                    QuarantineRecord(
                        signal_id=str(signal_id),
                        rejection_reason="INVALID_AMOUNT",
                        received_at_micros=received,
                        raw_payload=dict(raw),
                    )
                )
                continue

        dedupe_hash = str(raw["dedupe_hash"])
        if dedupe_hash in seen_hashes:
            continue
        seen_hashes.add(dedupe_hash)
        accepted.append(raw)

    return accepted, quarantined, skipped_future
