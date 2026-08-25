"""SQLite connection helper."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: Path | str, *, readonly: bool = False) -> sqlite3.Connection:
    uri = f"file:{Path(db_path).as_posix()}"
    if readonly:
        uri += "?mode=ro"
    conn = sqlite3.connect(uri, uri=readonly)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
