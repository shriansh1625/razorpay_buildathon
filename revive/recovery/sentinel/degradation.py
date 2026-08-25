"""Observable cohort degradation (C-03, RR-FUNC-006).

Infers elevated failure rates from payment attempts — never from hidden cohort labels.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from revive.recovery.sentinel.config import SentinelConfig

MINUTE_MICROS = 60 * 1_000_000


def detect_degraded_cohorts(
    transactions: list[dict[str, Any]],
    now_micros: int,
    config: SentinelConfig,
) -> set[str]:
    """Return method_type values showing an observable failure spike in the rolling window."""
    window = config.degradation_window_minutes * MINUTE_MICROS
    window_start = now_micros - window
    by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for txn in transactions:
        attempted = int(txn.get("attempted_at_micros") or 0)
        if attempted > now_micros or attempted < window_start:
            continue
        method = str(txn.get("method_type") or "")
        if method:
            by_method[method].append(txn)

    degraded: set[str] = set()
    for method, attempts in by_method.items():
        if len(attempts) < config.degradation_min_attempts:
            continue
        failures = sum(1 for t in attempts if str(t.get("status") or "").upper() == "FAILED")
        rate = failures / len(attempts)
        if rate >= config.degradation_failure_rate:
            degraded.add(method)
    return degraded
