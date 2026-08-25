"""Detection-layer metrics (observability only — no recovery claims)."""

from __future__ import annotations

from collections import Counter

from revive.recovery.sentinel.config import DETECTOR_VERSION
from revive.recovery.sentinel.models import DetectedOpportunity, DetectionMetrics, QuarantineRecord


def compute_metrics(
    opportunities: list[DetectedOpportunity],
    quarantined: list[QuarantineRecord],
    *,
    signals_ingested: int,
    dedupe_merges: int,
    detector_version: str = DETECTOR_VERSION,
) -> DetectionMetrics:
    by_class = Counter(o.risk_class.value for o in opportunities)
    return DetectionMetrics(
        opportunities_detected=len(opportunities),
        value_at_risk_total_paise=sum(o.value_at_risk_paise for o in opportunities),
        by_class=dict(by_class),
        quarantine_count=len(quarantined),
        dedupe_merges=dedupe_merges,
        signals_ingested=signals_ingested,
        detector_version=detector_version,
    )
