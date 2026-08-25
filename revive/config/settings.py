"""Centralised runtime settings (M1 skeleton — no env-specific secrets)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ReviveSettings:
    db_path: Path
    master_seed: int
    log_level: str
    timezone: str = "Asia/Kolkata"

    def __post_init__(self) -> None:
        if self.master_seed < 0:
            raise ValueError("master_seed must be non-negative")


def load_settings() -> ReviveSettings:
    """Load settings from environment with documented defaults."""
    db_path = Path(os.environ.get("REVIVE_DB_PATH", "revive.db"))
    master_seed = int(os.environ.get("REVIVE_MASTER_SEED", "42"))
    log_level = os.environ.get("REVIVE_LOG_LEVEL", "INFO")
    return ReviveSettings(
        db_path=db_path,
        master_seed=master_seed,
        log_level=log_level,
    )
