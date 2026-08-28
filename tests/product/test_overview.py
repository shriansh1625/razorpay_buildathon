"""Machine-readable product overview — same truth as the UI."""

from __future__ import annotations

import json
import socket
import threading
from http.client import HTTPConnection
from pathlib import Path

from revive.product.benchmark_lab import benchmark_lab
from revive.product.overview import product_overview
from revive.product.server import PayvantaHandler, ThreadingHTTPServer
from revive.product.session import DEMO_SEED, build_demo_session


def test_overview_matches_sandbox_snapshot():
    session = build_demo_session()
    snap = session.snapshot()
    bench = benchmark_lab()
    ov = product_overview(snap, bench)

    room = snap["control_room"]
    assert ov["product"] == "PAYVANTA"
    assert ov["environment"]["kind"] == "SANDBOX"
    assert ov["environment"]["seed"] == room["seed"] == DEMO_SEED
    assert ov["engine"]["status"] == "READY"
    assert ov["engine"]["internal_policy_id"] == "REVIVE"
    assert ov["intelligence"]["llm_used"] is False
    assert ov["intelligence"]["official_llm_mode"] == "LLM_OFF"
    assert ov["audit"]["ledger_count"] >= 1
    assert ov["track03"]["detect"] is True
    assert (
        ov["financial"]["incremental_net_recovery"]
        == room["hero"]["incremental_net_recovery"]
    )
    assert ov["financial"]["source"] == "sandbox_engine_measurement"
    assert ov["current_run"]["opportunity_id"] == snap["wow_opportunity_id"]
    assert ov["current_opportunity"]["opportunity_id"] == snap["wow_opportunity_id"]
    assert ov["workflow"]["pulse"] == room["system_pulse"]
    assert ov["integrity"]["sandbox_is_not_official_evidence"] is True
    assert ov["integrity"]["official_evidence_writable_by_product"] is False

    claims = {c["id"]: c for c in ov["claims"]}
    assert claims["incremental_net_recovery"]["environment"] == "SANDBOX"
    assert claims["official_cells"]["environment"] == "OFFICIAL_EVIDENCE"
    assert claims["benchmark_valid"]["environment"] == "OFFICIAL_EVIDENCE"
    assert claims["m10"]["value"] == "INCREMENTAL NET RECOVERY"

    if bench.get("evidence_verified"):
        assert ov["official_benchmark"]["verified"] is True
        assert ov["official_benchmark"]["cells"] == 600
        assert ov["official_benchmark"]["cell_count"] == 600
        assert ov["official_benchmark"]["groups"] == 120
        assert ov["official_benchmark"]["group_count"] == 120
        assert ov["official_benchmark"]["seeds"] == 20
        assert ov["official_benchmark"]["profiles"] == 6
        assert ov["official_benchmark"]["policies"] == 5
        assert ov["official_benchmark"]["validation"] == "BENCHMARK_VALID"
        assert ov["official_benchmark"]["blocked"] is False
        assert ov["official_benchmark"]["m10"]["id"] == "M-10"
        assert ov["official_benchmark"]["evidence_path"].endswith("official-cloud-final")
        assert claims["official_cells"]["value"] == 600
    else:
        assert ov["official_benchmark"]["cells"] is None
        assert claims["official_cells"]["value"] is None


def test_overview_does_not_claim_cells_without_verification(tmp_path: Path):
    session = build_demo_session(seed=42, cycles=2)
    missing = tmp_path / "artefacts" / "benchmark" / "official-cloud-final"
    bench = benchmark_lab(missing)
    ov = product_overview(session.snapshot(), bench)
    assert ov["official_benchmark"]["verified"] is False
    assert ov["official_benchmark"]["cells"] is None
    assert ov["financial"]["incremental_net_recovery"] is not None


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_overview_audit_receipt_http_endpoints():
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), PayvantaHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=180)
        conn.request("GET", "/api/product/overview")
        resp = conn.getresponse()
        assert resp.status == 200
        ov = json.loads(resp.read().decode("utf-8"))
        assert ov["product"] == "PAYVANTA"
        assert ov["environment"]["kind"] == "SANDBOX"
        wow = ov["current_run"]["opportunity_id"]
        assert wow

        conn.request("GET", "/api/audit")
        resp = conn.getresponse()
        assert resp.status == 200
        audit = json.loads(resp.read().decode("utf-8"))
        assert audit["environment"] == "SANDBOX"
        assert audit["count"] == len(audit["events"])
        assert audit["count"] >= 1

        conn.request("GET", "/api/runs")
        resp = conn.getresponse()
        assert resp.status == 200
        runs = json.loads(resp.read().decode("utf-8"))
        assert runs["environment"] == "SANDBOX"
        assert runs["current_seed"] == ov["environment"]["seed"]

        conn.request("GET", "/api/receipt/" + wow)
        resp = conn.getresponse()
        assert resp.status == 200
        receipt = json.loads(resp.read().decode("utf-8"))
        assert receipt["opportunity_id"] == wow
        assert "audit_reference" in receipt

        conn.request("GET", "/api/opportunity/" + wow + "/receipt")
        resp = conn.getresponse()
        assert resp.status == 200
        alias = json.loads(resp.read().decode("utf-8"))
        assert alias["opportunity_id"] == wow

        conn.request("POST", "/api/benchmark/official/summary", body=b"{}")
        resp = conn.getresponse()
        assert resp.status == 405
    finally:
        httpd.shutdown()
