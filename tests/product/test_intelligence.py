"""Product intelligence layer tests — Groq sandbox only."""

from __future__ import annotations

import ast
import json
import socket
import threading
import time
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch

import pytest

from revive.domain.enums import ActionCode
from revive.product.catalog import action_label
from revive.product.intelligence.config import GROQ_MODEL, MAX_RETRIES, REQUEST_TIMEOUT_S
from revive.product.intelligence.diagnosis import (
    diagnose_opportunity,
    economic_decision,
    intelligence_event,
)
from revive.product.intelligence.groq_client import GroqError
from revive.product.intelligence.schemas import parse_proposal
from revive.product.project import find_trace
from revive.product.server import PayvantaHandler, ThreadingHTTPServer, _clear_ai_state
from revive.product.session import DEMO_SEED, build_demo_session

SUCCESS_OID = "opp_CQ6VCH7HPPW9WG284G5EFRMDN0"
BLOCKED_OID = "opp_WST4PPPH81VPNTNC18K0YGRAW9"


def test_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    session = build_demo_session(seed=14, cycles=2)
    trace = session.snapshot()["opportunities"]
    oid = next(iter(trace))
    from revive.product.project import find_trace

    t = find_trace(session.state, oid)
    assert t is not None
    result = diagnose_opportunity(t)
    assert result.source == "deterministic_fallback"
    assert result.status == "DETERMINISTIC_FALLBACK"
    assert result.proposal.opportunity_id == oid


def test_parse_proposal_validates_cause_and_actions():
    payload = {
        "opportunity_id": "opp_TEST123",
        "primary_cause": "INSUFFICIENT_FUNDS",
        "cause_confidence": 0.7,
        "observed_evidence": ["reason_code=insufficient_funds"],
        "inference_notes": ["Customer may retry after payday."],
        "candidate_actions": [
            {
                "action_id": "A01",
                "reason": "Immediate retry may succeed.",
                "expected_context_fit": "Soft decline pattern",
            }
        ],
        "missing_evidence": [],
        "risk_flags": [],
        "uncertainty": "Moderate",
    }
    proposal = parse_proposal(
        payload,
        expected_opportunity_id="opp_TEST123",
        evidence_facts={"reason_code": "insufficient_funds"},
    )
    assert proposal.primary_cause == "INSUFFICIENT_FUNDS"
    assert proposal.candidate_actions[0].action_id == "A01"
    assert proposal.observed_evidence == ("reason_code=insufficient_funds",)


def test_parse_proposal_downgrades_fabricated_observation():
    payload = {
        "opportunity_id": "opp_TEST123",
        "primary_cause": "INSUFFICIENT_FUNDS",
        "cause_confidence": 0.7,
        "observed_evidence": [
            "reason_code=insufficient_funds",
            "customer_promised_to_pay_tomorrow",
        ],
        "inference_notes": ["May retry after payday."],
        "candidate_actions": [
            {
                "action_id": "A01",
                "reason": "Immediate retry may succeed.",
                "expected_context_fit": "Soft decline pattern",
            }
        ],
        "missing_evidence": [],
        "risk_flags": [],
        "uncertainty": "Moderate",
    }
    proposal = parse_proposal(
        payload,
        expected_opportunity_id="opp_TEST123",
        evidence_facts={"reason_code": "insufficient_funds"},
    )
    assert proposal.observed_evidence == ("reason_code=insufficient_funds",)
    assert any("customer_promised_to_pay_tomorrow" in note for note in proposal.inference_notes)
    assert all("customer_promised_to_pay_tomorrow" not in item for item in proposal.observed_evidence)


def test_parse_proposal_rejects_malformed_payload():
    with pytest.raises(ValueError, match="proposal must be an object"):
        parse_proposal(["not", "an", "object"], expected_opportunity_id="opp_TEST123")


def test_parse_proposal_rejects_unknown_cause():
    payload = {
        "opportunity_id": "opp_TEST123",
        "primary_cause": "MADE_UP_CAUSE",
        "cause_confidence": 0.7,
        "observed_evidence": [],
        "inference_notes": [],
        "candidate_actions": [],
        "missing_evidence": [],
        "risk_flags": [],
        "uncertainty": "",
    }
    with pytest.raises(ValueError, match="invalid primary_cause"):
        parse_proposal(payload, expected_opportunity_id="opp_TEST123")


def test_parse_proposal_rejects_invalid_action():
    payload = {
        "opportunity_id": "opp_TEST123",
        "primary_cause": "INSUFFICIENT_FUNDS",
        "cause_confidence": 0.7,
        "observed_evidence": [],
        "inference_notes": [],
        "candidate_actions": [{"action_id": "FAKE", "reason": "x", "expected_context_fit": "y"}],
        "missing_evidence": [],
        "risk_flags": [],
        "uncertainty": "",
    }
    with pytest.raises(ValueError, match="invalid action_id"):
        parse_proposal(payload, expected_opportunity_id="opp_TEST123")


def test_groq_failure_falls_back(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    session = build_demo_session(seed=14, cycles=2)
    from revive.product.project import find_trace

    oid = session.snapshot()["wow_opportunity_id"]
    t = find_trace(session.state, oid)
    assert t is not None

    def _boom(*_a, **_k):
        raise RuntimeError("provider down")

    with patch("revive.product.intelligence.diagnosis.complete_structured", side_effect=_boom):
        result = diagnose_opportunity(t)
    assert result.status == "AI_UNAVAILABLE"
    assert result.source == "deterministic_fallback"
    assert result.proposal.primary_cause


def test_ai_diagnosis_endpoint_never_leaks_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    _clear_ai_state()
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), PayvantaHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=30)
        conn.request("GET", "/api/snapshot")
        snap = json.loads(conn.getresponse().read().decode())
        oid = snap["wow_opportunity_id"]
        conn.request("POST", f"/api/opportunity/{oid}/ai-diagnosis", body=b"{}")
        resp = conn.getresponse()
        body = resp.read().decode()
        assert resp.status == 200
        assert "GROQ_API_KEY" not in body
        assert "gsk_" not in body
        payload = json.loads(body)
        assert payload["source"] == "deterministic_fallback"
        assert "economic_decision" in payload
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_overview_exposes_ai_block(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    from revive.product.benchmark_lab import benchmark_lab
    from revive.product.overview import product_overview

    session = build_demo_session(seed=14, cycles=2)
    snap = session.snapshot()
    snap["intelligence_status"] = {
        "enabled": False,
        "status": "DETERMINISTIC_FALLBACK",
        "execution_authority": "none",
    }
    ov = product_overview(snap, benchmark_lab())
    assert ov["ai"]["status"] == "DETERMINISTIC_FALLBACK"
    assert ov["intelligence"]["engine_llm_used"] is False
    assert ov["ai"]["execution_authority"] == "none"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _mock_ai_payload(opportunity_id: str, *, action_id: str = "A01", cause: str = "INSUFFICIENT_FUNDS") -> dict:
    return {
        "opportunity_id": opportunity_id,
        "primary_cause": cause,
        "cause_confidence": 0.82,
        "observed_evidence": ["reason_code=insufficient_funds"],
        "inference_notes": ["Payday timing may explain soft decline."],
        "candidate_actions": [
            {
                "action_id": action_id,
                "reason": "AI proposes immediate retry.",
                "expected_context_fit": "Synthetic sandbox context",
            }
        ],
        "missing_evidence": [],
        "risk_flags": [],
        "uncertainty": "Moderate diagnosis confidence.",
    }


def test_ai_contract_timeout_and_retry_constants():
    assert REQUEST_TIMEOUT_S == 12.0
    assert MAX_RETRIES == 2
    assert GROQ_MODEL == "openai/gpt-oss-120b"


def test_parse_proposal_rejects_opportunity_id_mismatch():
    payload = _mock_ai_payload("opp_OTHER")
    with pytest.raises(ValueError, match="opportunity_id mismatch"):
        parse_proposal(payload, expected_opportunity_id="opp_TEST123")


def test_malformed_ai_response_falls_back(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    session = build_demo_session(seed=DEMO_SEED)
    trace = find_trace(session.state, SUCCESS_OID)
    assert trace is not None

    with patch(
        "revive.product.intelligence.diagnosis.complete_structured",
        return_value=_mock_ai_payload(SUCCESS_OID, cause="MADE_UP_CAUSE"),
    ):
        result = diagnose_opportunity(trace)

    assert result.status == "AI_UNAVAILABLE"
    assert result.source == "deterministic_fallback"
    assert result.error


def test_groq_error_never_contains_api_key(monkeypatch):
    secret = "gsk_test_secret_value_xyz"
    monkeypatch.setenv("GROQ_API_KEY", secret)
    session = build_demo_session(seed=DEMO_SEED)
    trace = find_trace(session.state, SUCCESS_OID)
    assert trace is not None

    with patch(
        "revive.product.intelligence.diagnosis.complete_structured",
        side_effect=GroqError("HTTP 401 unauthorized"),
    ):
        result = diagnose_opportunity(trace)

    assert secret not in (result.error or "")
    assert "gsk_" not in (result.error or "")


def test_economic_boundary_ai_proposal_does_not_override_engine(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    session = build_demo_session(seed=DEMO_SEED)
    trace = find_trace(session.state, SUCCESS_OID)
    assert trace is not None
    assert trace.assignment is not None
    engine_action = trace.assignment.action_code.value
    ai_action = ActionCode.A01.value
    assert ai_action != engine_action

    with patch(
        "revive.product.intelligence.diagnosis.complete_structured",
        return_value=_mock_ai_payload(SUCCESS_OID, action_id=ai_action),
    ):
        result = diagnose_opportunity(trace)

    assert result.status == "AI_COMPLETED"
    assert result.proposal.candidate_actions[0].action_id == ai_action
    econ = economic_decision(trace)
    assert econ["authority"] == "deterministic_engine"
    assert econ["selected_action"] == action_label(engine_action)
    assert econ["selected_action"] != action_label(ai_action)
    joined_observed = " ".join(result.proposal.observed_evidence)
    assert "customer_promised_to_pay" not in joined_observed


def test_diagnose_downgrades_ungrounded_observed_claims(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    session = build_demo_session(seed=DEMO_SEED)
    trace = find_trace(session.state, SUCCESS_OID)
    assert trace is not None
    payload = _mock_ai_payload(SUCCESS_OID)
    payload["observed_evidence"] = ["this_claim_is_not_in_the_fixture_evidence"]
    with patch(
        "revive.product.intelligence.diagnosis.complete_structured",
        return_value=payload,
    ):
        result = diagnose_opportunity(trace)
    assert result.status == "AI_COMPLETED"
    assert result.proposal.observed_evidence == ()
    assert any("this_claim_is_not_in_the_fixture_evidence" in n for n in result.proposal.inference_notes)


def test_safety_boundary_ai_cannot_override_blocked_opportunity(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    session = build_demo_session(seed=DEMO_SEED)
    card = session.snapshot()["opportunities"][BLOCKED_OID]["card"]
    assert card["blocked"] is True
    assert card["authorization_state"] == "BLOCKED"
    assert card["execution_state"] == "NOT_EXECUTED"
    trace = find_trace(session.state, BLOCKED_OID)
    assert trace is not None

    with patch(
        "revive.product.intelligence.diagnosis.complete_structured",
        return_value=_mock_ai_payload(BLOCKED_OID, action_id=ActionCode.A09.value),
    ):
        result = diagnose_opportunity(trace)

    assert result.status == "AI_COMPLETED"
    after = session.snapshot()["opportunities"][BLOCKED_OID]["card"]
    assert after["blocked"] is True
    assert after["authorization_state"] == "BLOCKED"
    assert after["execution_state"] == "NOT_EXECUTED"


def test_authorization_boundary_no_execution_when_blocked(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    session = build_demo_session(seed=DEMO_SEED)
    trace = find_trace(session.state, BLOCKED_OID)
    assert trace is not None
    assert trace.authorization is not None
    assert trace.authorization.authorization_state.value == "BLOCKED"
    assert trace.execution is None

    with patch(
        "revive.product.intelligence.diagnosis.complete_structured",
        return_value=_mock_ai_payload(BLOCKED_OID, action_id=ActionCode.A09.value),
    ):
        diagnose_opportunity(trace)

    assert trace.execution is None


def test_intelligence_module_has_no_execution_imports():
    root = Path(__file__).resolve().parents[2] / "revive" / "product" / "intelligence"
    forbidden = (
        "revive.execution",
        "run_simulator",
        "run_traced_cycle",
        "execute_",
        "ExecutionAdapter",
    )
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        imports = {
            node.names[0].name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
        }
        imports.update(
            f"{node.module}.{node.names[0].name}" if node.module else node.names[0].name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        joined = text + " " + " ".join(imports)
        for token in forbidden:
            assert token not in joined, f"{path.name} must not reference {token}"


def test_ai_diagnosis_endpoint_does_not_execute(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    _clear_ai_state()
    from revive.product import server as srv

    srv._SESSION = None
    srv._SNAPSHOT = None
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), PayvantaHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=30)
        conn.request("GET", "/api/snapshot")
        snap = json.loads(conn.getresponse().read().decode())
        blocked = snap["opportunities"][BLOCKED_OID]["card"]
        assert blocked["execution_state"] == "NOT_EXECUTED"
        conn.request("POST", f"/api/opportunity/{BLOCKED_OID}/ai-diagnosis", body=b"{}")
        payload = json.loads(conn.getresponse().read().decode())
        assert payload["economic_decision"]["authority"] == "deterministic_engine"
        conn.request("GET", "/api/snapshot")
        snap2 = json.loads(conn.getresponse().read().decode())
        assert snap2["opportunities"][BLOCKED_OID]["card"]["execution_state"] == "NOT_EXECUTED"
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_ai_diagnosis_cache_prevents_repeat_calls(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    _clear_ai_state()
    from revive.product import server as srv

    srv._SESSION = None
    srv._SNAPSHOT = None
    calls: list[str] = []

    def _counting(trace):
        calls.append(trace.opportunity.opportunity_id)
        from revive.product.intelligence.diagnosis import diagnose_opportunity as real

        return real(trace)

    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), PayvantaHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with patch("revive.product.server.diagnose_opportunity", side_effect=_counting):
            conn = HTTPConnection("127.0.0.1", port, timeout=30)
            conn.request("GET", "/api/snapshot")
            oid = json.loads(conn.getresponse().read().decode())["wow_opportunity_id"]
            for _ in range(3):
                conn.request("POST", f"/api/opportunity/{oid}/ai-diagnosis", body=b"{}")
                conn.getresponse().read()
        assert len(calls) == 1
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def _http_json(method: str, path: str, port: int, *, body: bytes | None = None) -> dict:
    conn = HTTPConnection("127.0.0.1", port, timeout=120)
    try:
        conn.request(method, path, body=body or b"")
        resp = conn.getresponse()
        data = resp.read()
        assert resp.status == 200, (path, resp.status, data[:200])
        return json.loads(data.decode())
    finally:
        conn.close()


def test_ai_diagnosis_records_audit_event(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    _clear_ai_state()
    from revive.product import server as srv

    srv._SESSION = None
    srv._SNAPSHOT = None
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), PayvantaHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        snap = _http_json("GET", "/api/snapshot", port)
        oid = snap["wow_opportunity_id"]
        _http_json("POST", f"/api/opportunity/{oid}/ai-diagnosis", port, body=b"{}")
        snap2 = _http_json("GET", "/api/snapshot", port)
        events = snap2.get("intelligence_events") or []
        assert any(e.get("event") == "AI_DIAGNOSIS_COMPLETED" for e in events)
        audit = _http_json("GET", "/api/audit", port)
        overlay = [e for e in audit["events"] if e.get("category") == "intelligence"]
        assert overlay
        assert overlay[0].get("money_path") is False
        assert overlay[0].get("event") == "AI_DIAGNOSIS_COMPLETED"
        event = intelligence_event(
            diagnose_opportunity(find_trace(srv._session().state, oid))
        )
        assert event["schema_version"] == "ai_diagnosis_v1"
        assert "GROQ_API_KEY" not in json.dumps(event)
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_intelligence_status_endpoint_safe(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    _clear_ai_state()
    from revive.product import server as srv

    srv._SESSION = None
    srv._SNAPSHOT = None
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), PayvantaHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=30)
        conn.request("GET", "/api/intelligence/status")
        body = conn.getresponse().read().decode()
        payload = json.loads(body)
        assert payload["execution_authority"] == "none"
        assert payload["enabled"] is False
        assert "GROQ_API_KEY" not in body
        assert "gsk_" not in body
    finally:
        httpd.shutdown()
        thread.join(timeout=2)


def test_fallback_latency_bounded(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    session = build_demo_session(seed=DEMO_SEED)
    trace = find_trace(session.state, SUCCESS_OID)
    assert trace is not None
    start = time.perf_counter()
    for _ in range(20):
        diagnose_opportunity(trace)
    assert time.perf_counter() - start < 2.0


def test_demo_seed_success_and_blocked_paths_with_ai_overlay(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    session = build_demo_session(seed=DEMO_SEED)
    snap = session.snapshot()
    success = snap["opportunities"][SUCCESS_OID]["card"]
    blocked = snap["opportunities"][BLOCKED_OID]["card"]
    assert success["authorization_state"] == "AUTHORIZED"
    assert success["execution_state"] == "SUCCEEDED"
    assert blocked["blocked"] is True
    assert blocked["execution_state"] == "NOT_EXECUTED"

    with patch(
        "revive.product.intelligence.diagnosis.complete_structured",
        return_value=_mock_ai_payload(BLOCKED_OID, action_id=ActionCode.A09.value),
    ):
        blocked_ai = diagnose_opportunity(find_trace(session.state, BLOCKED_OID))
    assert blocked_ai.status == "AI_COMPLETED"
    assert session.snapshot()["opportunities"][BLOCKED_OID]["card"]["blocked"] is True
