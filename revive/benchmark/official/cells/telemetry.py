"""Optional memory telemetry — M13.11 (does not affect benchmark outcomes)."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MemorySample:
    rss_bytes: int | None
    timestamp: float


@dataclass(frozen=True, slots=True)
class CellTelemetry:
    rss_before_bytes: int | None
    rss_after_bytes: int | None
    peak_rss_bytes: int | None
    duration_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "rss_before_bytes": self.rss_before_bytes,
            "rss_after_bytes": self.rss_after_bytes,
            "peak_rss_bytes": self.peak_rss_bytes,
            "duration_seconds": self.duration_seconds,
        }


def current_rss_bytes() -> int | None:
    """Best-effort resident set size for the current process."""
    try:
        import psutil

        return int(psutil.Process().memory_info().rss)
    except Exception:
        pass

    if sys.platform == "win32":
        try:
            import ctypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_ulong),
                    ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            if ctypes.windll.psapi.GetProcessMemoryInfo(
                handle,
                ctypes.byref(counters),
                counters.cb,
            ):
                return int(counters.WorkingSetSize)
        except Exception:
            return None
        return None

    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss = usage.ru_maxrss
        if sys.platform == "darwin":
            return int(rss)
        return int(rss) * 1024
    except Exception:
        return None


class PeakRssTracker:
    """Track peak RSS during a cell when sampling is available."""

    def __init__(self) -> None:
        self._start = current_rss_bytes()
        self._peak = self._start

    def sample(self) -> None:
        rss = current_rss_bytes()
        if rss is None:
            return
        if self._peak is None or rss > self._peak:
            self._peak = rss

    @property
    def peak(self) -> int | None:
        return self._peak


def monotonic_seconds() -> float:
    return time.perf_counter()
