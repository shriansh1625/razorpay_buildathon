"""C-02 Revenue Sentinel — detection only."""

from revive.recovery.sentinel.config import DETECTOR_VERSION, SentinelConfig, default_sentinel_config
from revive.recovery.sentinel.detect import detect
from revive.recovery.sentinel.models import DetectedOpportunity, SentinelResult

__all__ = [
    "DETECTOR_VERSION",
    "SentinelConfig",
    "default_sentinel_config",
    "DetectedOpportunity",
    "SentinelResult",
    "detect",
]
