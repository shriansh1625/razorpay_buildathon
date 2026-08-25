"""SQLite persistence — schema skeleton only (docs/17)."""

from revive.db.connection import connect
from revive.db.schema import SCHEMA_VERSION, apply_schema, schema_ddl

__all__ = ["connect", "apply_schema", "schema_ddl", "SCHEMA_VERSION"]
