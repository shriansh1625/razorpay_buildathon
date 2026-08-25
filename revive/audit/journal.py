"""Append-only audit journal — ACTION_INTENT before effect."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AuditEventType(str, Enum):
    ACTION_INTENT = "ACTION_INTENT"
    ACTION_RESULT = "ACTION_RESULT"


@dataclass(frozen=True, slots=True)
class AuditRecord:
    audit_id: str
    event_type: AuditEventType
    sequence_no: int
    occurred_at_micros: int
    prev_hash: str
    content_hash: str
    correlation: dict[str, Any]
    payload: dict[str, Any]


@dataclass
class AuditJournal:
    """In-memory append-only audit chain for M11."""

    _records: list[AuditRecord] = field(default_factory=list)
    _writable: bool = True

    def append(
        self,
        event_type: AuditEventType,
        occurred_at_micros: int,
        correlation: dict[str, Any],
        payload: dict[str, Any],
    ) -> AuditRecord:
        if not self._writable:
            raise RuntimeError("audit store unwritable — execution halted")
        sequence = len(self._records) + 1
        prev_hash = self._records[-1].content_hash if self._records else "0"
        audit_id = f"aud_{hashlib.sha256(f'{sequence}:{event_type.value}'.encode()).hexdigest()[:26]}"
        canonical = _canonical_payload(event_type, occurred_at_micros, correlation, payload)
        content_hash = hashlib.sha256(canonical.encode()).hexdigest()
        record = AuditRecord(
            audit_id=audit_id,
            event_type=event_type,
            sequence_no=sequence,
            occurred_at_micros=occurred_at_micros,
            prev_hash=prev_hash,
            content_hash=content_hash,
            correlation=dict(correlation),
            payload=dict(payload),
        )
        self._records.append(record)
        return record

    def records(self) -> tuple[AuditRecord, ...]:
        return tuple(self._records)

    def halt(self) -> None:
        self._writable = False


def _canonical_payload(
    event_type: AuditEventType,
    occurred_at_micros: int,
    correlation: dict[str, Any],
    payload: dict[str, Any],
) -> str:
    body = {
        "event_type": event_type.value,
        "occurred_at_micros": occurred_at_micros,
        "correlation": correlation,
        "payload": payload,
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"))
