"""DDL skeleton mirroring docs/17 layers — no seed data."""

from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- DOMAIN layer (synthetic input — populated by generator in M2)
CREATE TABLE IF NOT EXISTS merchant (
    merchant_id TEXT PRIMARY KEY,
    name_token TEXT NOT NULL,
    timezone TEXT NOT NULL,
    net_retention_factor REAL NOT NULL,
    policy_pack_ref TEXT
);

CREATE TABLE IF NOT EXISTS customer (
    customer_id TEXT PRIMARY KEY,
    customer_ref TEXT NOT NULL,
    segment TEXT,
    tenure_band TEXT,
    value_band TEXT
);

-- SIGNAL layer
CREATE TABLE IF NOT EXISTS signal (
    signal_id TEXT PRIMARY KEY,
    signal_type TEXT NOT NULL,
    source_ref TEXT,
    payload_json TEXT NOT NULL,
    received_at_micros INTEGER NOT NULL,
    occurred_at_micros INTEGER NOT NULL,
    dedupe_hash TEXT NOT NULL UNIQUE,
    processed_at_micros INTEGER,
    opportunity_id TEXT
);

CREATE TABLE IF NOT EXISTS signal_quarantine (
    quarantine_id TEXT PRIMARY KEY,
    raw_payload TEXT NOT NULL,
    rejection_reason TEXT NOT NULL,
    received_at_micros INTEGER NOT NULL,
    schema_version_attempted TEXT
);

-- CORE layer
CREATE TABLE IF NOT EXISTS revenue_opportunity (
    opportunity_id TEXT PRIMARY KEY,
    merchant_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    risk_class TEXT NOT NULL,
    natural_key TEXT NOT NULL,
    value_at_risk_paise INTEGER NOT NULL,
    original_value_paise INTEGER NOT NULL,
    continuation_value_paise INTEGER NOT NULL DEFAULT 0,
    addressable INTEGER NOT NULL,
    state TEXT NOT NULL,
    first_detected_at_micros INTEGER NOT NULL,
    recovery_window_expires_at_micros INTEGER NOT NULL,
    attempt_seq INTEGER NOT NULL DEFAULT 0,
    contacts_made INTEGER NOT NULL DEFAULT 0,
    consecutive_no_action_cycles INTEGER NOT NULL DEFAULT 0,
    next_eligible_at_micros INTEGER,
    reopen_count INTEGER NOT NULL DEFAULT 0,
    linked_refs_json TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_opportunity_natural_key_open
    ON revenue_opportunity (natural_key)
    WHERE state NOT IN ('RECOVERED', 'STOPPED', 'CLOSED_UNRECOVERED', 'RECONCILIATION_FAILED');

CREATE INDEX IF NOT EXISTS idx_opportunity_state_eligible
    ON revenue_opportunity (state, next_eligible_at_micros);

CREATE TABLE IF NOT EXISTS diagnosis (
    diagnosis_id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    cycle_id TEXT NOT NULL,
    ranked_causes_json TEXT NOT NULL,
    unclassified INTEGER NOT NULL DEFAULT 0,
    produced_at_micros INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS action_candidate (
    candidate_id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    cycle_id TEXT NOT NULL,
    action_code TEXT NOT NULL,
    params_json TEXT,
    enrv_paise INTEGER NOT NULL,
    enrv_lo_paise INTEGER NOT NULL,
    enrv_hi_paise INTEGER NOT NULL,
    gross_paise INTEGER NOT NULL,
    cost_paise INTEGER NOT NULL,
    expected_incentive_paise INTEGER NOT NULL DEFAULT 0,
    fatigue_cost_paise INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS decision (
    decision_id TEXT PRIMARY KEY,
    cycle_id TEXT NOT NULL,
    opportunity_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    chosen_action_code TEXT,
    enrv_chosen_paise INTEGER,
    UNIQUE (cycle_id, opportunity_id)
);

CREATE TABLE IF NOT EXISTS gate_verdict (
    verdict_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    cycle_id TEXT NOT NULL,
    gate_id TEXT NOT NULL,
    sequence_no INTEGER NOT NULL,
    verdict TEXT NOT NULL,
    reason_code TEXT,
    policy_pack_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approval_request (
    approval_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    opportunity_id TEXT NOT NULL,
    state TEXT NOT NULL,
    queued_at_micros INTEGER NOT NULL,
    expires_at_micros INTEGER,
    actor_kind TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS intervention (
    intervention_id TEXT PRIMARY KEY,
    decision_id TEXT NOT NULL,
    opportunity_id TEXT NOT NULL,
    cycle_id TEXT NOT NULL,
    action_code TEXT NOT NULL,
    params_json TEXT,
    idempotency_key TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL,
    invoked_at_micros INTEGER,
    returned_at_micros INTEGER
);

CREATE TABLE IF NOT EXISTS outcome (
    outcome_id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    intervention_id TEXT,
    recovered_amount_paise INTEGER NOT NULL DEFAULT 0,
    recovered_at_micros INTEGER,
    horizon_used_minutes INTEGER NOT NULL,
    observability TEXT NOT NULL,
    attribution_class TEXT NOT NULL
);

-- Oracle counterfactual isolated table (AI-6) — decision path must not map this
CREATE TABLE IF NOT EXISTS outcome_oracle_partition (
    outcome_id TEXT PRIMARY KEY,
    oracle_counterfactual_paise INTEGER NOT NULL,
    FOREIGN KEY (outcome_id) REFERENCES outcome(outcome_id)
);

-- CONTROL layer
CREATE TABLE IF NOT EXISTS policy_pack (
    policy_pack_id TEXT PRIMARY KEY,
    version TEXT NOT NULL,
    status TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    sealed_at_micros INTEGER,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resource_ledger_entry (
    ledger_entry_id TEXT PRIMARY KEY,
    resource_key TEXT NOT NULL,
    scope_key TEXT NOT NULL,
    delta REAL NOT NULL,
    kind TEXT NOT NULL,
    handle_id TEXT,
    cycle_id TEXT NOT NULL,
    balance_after REAL NOT NULL,
    created_at_micros INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS reservation_handle (
    handle_id TEXT PRIMARY KEY,
    cycle_id TEXT NOT NULL,
    decision_id TEXT NOT NULL,
    state TEXT NOT NULL,
    items_json TEXT NOT NULL,
    created_at_micros INTEGER NOT NULL,
    settled_at_micros INTEGER
);

CREATE TABLE IF NOT EXISTS idempotency_key (
    key TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    opportunity_id TEXT NOT NULL,
    action_code TEXT NOT NULL,
    attempt_seq INTEGER NOT NULL,
    cycle_id TEXT NOT NULL,
    claimed_at_micros INTEGER NOT NULL
);

-- RECORD layer
CREATE TABLE IF NOT EXISTS cycle_record (
    cycle_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    state TEXT NOT NULL,
    opened_at_micros INTEGER NOT NULL,
    closed_at_micros INTEGER
);

CREATE TABLE IF NOT EXISTS run_record (
    run_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    master_seed INTEGER NOT NULL,
    config_hash TEXT NOT NULL,
    genesis_hash TEXT,
    started_at_micros INTEGER NOT NULL,
    completed_at_micros INTEGER
);

CREATE TABLE IF NOT EXISTS audit_event (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    cycle_id TEXT,
    sequence_no INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    recorded_at_micros INTEGER NOT NULL
);
"""


def schema_ddl() -> str:
    return _DDL.strip()


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(schema_ddl())
    conn.execute(
        "INSERT OR REPLACE INTO schema_meta (key, value) VALUES (?, ?)",
        ("schema_version", str(SCHEMA_VERSION)),
    )
    conn.commit()
