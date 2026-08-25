"""Database schema skeleton tests."""

import sqlite3

from revive.db import SCHEMA_VERSION, apply_schema, schema_ddl


def test_schema_ddl_contains_core_tables():
    ddl = schema_ddl()
    for table in (
        "revenue_opportunity",
        "decision",
        "outcome_oracle_partition",
        "policy_pack",
        "audit_event",
    ):
        assert table in ddl


def test_apply_schema_in_memory():
    conn = sqlite3.connect(":memory:")
    apply_schema(conn)
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key = 'schema_version'"
    ).fetchone()
    assert row[0] == str(SCHEMA_VERSION)
    conn.close()
