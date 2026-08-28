"""Product layer — Control Room traces, receipts, integrity."""

from pathlib import Path

import pytest

from revive.config.policy_pack import official_sealed_policy_pack
from revive.policy.models import AuthorizationState
from revive.product.benchmark_lab import DECLARED_FROZEN_EXPERIMENT, benchmark_lab
from revive.product.official_evidence import official_matrix
from revive.product.project import decision_receipt, latest_traces
from revive.product.session import DEMO_SEED, build_demo_session
from revive.product.simulator import run_simulator


def test_demo_session_runs_engine_and_labels_fixture():
    session = build_demo_session(seed=42, cycles=2)
    snap = session.snapshot()
    room = snap["control_room"]
    assert room["product"] == "PAYVANTA"
    assert "synthetic" in room["fixture_label"].lower()
    assert room["internal_policy_id"] == "REVIVE"
    assert room["cycles_run"] == 2
    assert "incremental_net_recovery" in room["hero"]
    assert room["hero"]["execution_integrity"] in {"PASS", "FAIL"}


def test_receipt_has_required_fields():
    session = build_demo_session(seed=42, cycles=2)
    traces = latest_traces(session.state)
    assert traces
    receipt = decision_receipt(traces[0])
    for key in (
        "opportunity_id",
        "observed_failure",
        "selected_action",
        "expected_incremental_value",
        "authorization",
        "audit_reference",
        "pipeline",
        "incremental_net_recovery",
    ):
        assert key in receipt


def test_no_execution_without_authorization():
    session = build_demo_session(seed=42, cycles=2)
    for cycle in session.state.cycles:
        for tr in cycle.opportunities:
            if tr.execution is not None:
                assert tr.authorization is not None
                assert tr.authorization.authorization_state == AuthorizationState.AUTHORIZED


def test_simulator_is_deterministic():
    a = run_simulator(failure_type="PAYMENT_FAILURE", seed=7, opportunity_count=8)
    b = run_simulator(failure_type="PAYMENT_FAILURE", seed=7, opportunity_count=8)
    assert a["control_room"]["hero"]["authorized_interventions"] == b["control_room"]["hero"]["authorized_interventions"]
    assert a["inputs"]["llm_mode"] == "OFF"
    assert a["control_room"]["pipeline"]["DETECTED"] >= 1
    assert a["focus_opportunity_id"] is not None


def test_benchmark_lab_does_not_write_official_dir(tmp_path: Path):
    official = tmp_path / "artefacts" / "benchmark" / "official-cloud-final"
    lab = benchmark_lab(official)
    assert lab["internal_policy_id"] == "REVIVE"
    assert lab["declared_official_run"]["cells"] == 600
    assert lab["declared_official_run"]["frozen_experiment_reference"] == DECLARED_FROZEN_EXPERIMENT
    assert lab["artefact_status"] == "NOT_MOUNTED_IN_THIS_WORKSPACE"
    assert lab["policy_summaries"] is None
    assert not official.exists()


def test_invalidated_official_tree_is_not_product_proof():
    from revive.product.benchmark_lab import INVALIDATED_OFFICIAL, classify_artefact_tree

    assert classify_artefact_tree(INVALIDATED_OFFICIAL) == "INADMISSIBLE"
    lab = benchmark_lab(INVALIDATED_OFFICIAL)
    assert lab["artefact_status"] == "INADMISSIBLE_LOCAL_TREE"
    assert lab["policy_summaries"] is None
    assert lab["integrity"]["never_use_invalidated_official_tree"] is True



def test_money_projection_includes_compact_headline():
    from revive.product.money import format_compact_inr
    from revive.product.project import _money

    assert format_compact_inr(4_742_000_00) == "₹47.42L"
    packed = _money(4_742_000_00)
    assert packed["compact"] == "₹47.42L"
    assert packed["display"].startswith("₹")
    assert packed["paise"] == 4_742_000_00


def test_control_room_v2_projections():
    session = build_demo_session(seed=42, cycles=2)
    snap = session.snapshot()
    room = snap["control_room"]
    assert "system_pulse" in room
    assert "interactive_pipeline" in room
    assert len(room["interactive_pipeline"]) == 8
    assert "opportunity_summary" in room
    assert len(room["all_opportunities"]) >= len(room["top_opportunities"])
    assert "at_risk_revenue" in room["hero"]
    assert "natural_recovery" in room["hero"]
    assert isinstance(snap["audit_ledger"], list)
    card = room["all_opportunities"][0]
    assert "best_action" in card
    assert "expected_recovery" in card


def test_benchmark_profile_policy_matrix():
    lab = benchmark_lab()
    mx = lab["profile_policy_matrix"]
    assert len(mx["profiles"]) == 6
    assert "REVIVE" in mx["policies"]
    if lab.get("evidence_verified"):
        assert mx["verified"] is True
        full = official_matrix()
        assert full["matrix"]["ABUNDANT"]["REVIVE"]["seed_count"] == 20
    else:
        assert mx.get("verified") is False


def test_official_policy_pack_untouched():
    pack = official_sealed_policy_pack()
    assert pack.version == "pol_m13_official_v1"
    assert pack.epsilon_paise == 100
    assert pack.status.value == "SEALED"
    digest = pack.config_hash()
    assert digest == official_sealed_policy_pack().config_hash()


def test_simulator_request_validation_answers_bad_input():
    """A cleared number field used to raise ``int("")`` out of the handler, dropping the
    connection so the browser reported a transport error for a validation problem."""
    from revive.product.server import (
        PROFILES,
        _BadRequest,
        _choice_field,
        _int_field,
    )

    assert _int_field({"seed": ""}, "seed", 7, 1, 9999) == 7
    assert _int_field({}, "seed", 7, 1, 9999) == 7
    assert _int_field({"seed": "14"}, "seed", 7, 1, 9999) == 14
    for bad in ("abc", "1.5", 0, 10_000, "-3"):
        with pytest.raises(_BadRequest):
            _int_field({"seed": bad}, "seed", 7, 1, 9999)

    assert _choice_field({}, "profile", "SCARCE", PROFILES) == "SCARCE"
    assert _choice_field({"profile": "ABUNDANT"}, "profile", "SCARCE", PROFILES) == "ABUNDANT"
    with pytest.raises(_BadRequest):
        _choice_field({"profile": "NOPE"}, "profile", "SCARCE", PROFILES)


def test_demo_seed_has_success_and_blocked_paths():
    """Judge starting world: one authorized→executed→measured path and one block."""
    session = build_demo_session(seed=DEMO_SEED)
    snap = session.snapshot()
    wow_id = snap["wow_opportunity_id"]
    assert wow_id
    wow = snap["opportunities"][wow_id]["card"]
    assert wow["authorization_state"] == "AUTHORIZED"
    assert wow["execution_state"] == "SUCCEEDED"
    assert wow["measured"] is True
    assert wow["incremental_net"]["paise"] > 0
    blocked = [c for c in snap["control_room"]["all_opportunities"] if c["blocked"]]
    assert blocked
    assert blocked[0]["execution_state"] == "NOT_EXECUTED"
    assert snap["control_room"]["seed"] == DEMO_SEED
    assert "sandbox" in snap["control_room"]["fixture_label"].lower()
    pulse = snap["control_room"]["system_pulse"]
    assert pulse["detected"] >= 1
    assert pulse["authorized"] >= 1
    assert pulse["blocked"] >= 1
    assert pulse["executed"] >= 1
    assert pulse["measured"] >= 1
