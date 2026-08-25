"""Structured logging — JSON-friendly records for audit alignment (M1 stub)."""

from __future__ import annotations

import logging
import sys
from typing import Any


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )


def get_logger(name: str, **context: Any) -> logging.LoggerAdapter:
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, extra=context)
