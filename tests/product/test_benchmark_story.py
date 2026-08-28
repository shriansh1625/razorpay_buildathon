"""Official benchmark story — available without mounted artefacts."""

from __future__ import annotations

import json
import socket
import threading
from http.client import HTTPConnection
from pathlib import Path

from revive.product.benchmark_lab import DECLARED_FROZEN_EXPERIMENT, benchmark_lab
from revive.product.benchmark_story import benchmark_story
from revive.product.official_evidence import official_contract
from revive.product.server import PayvantaHandler, ThreadingHTTPServer


def test_story_is_self_contained():
    story = benchmark_story()
    assert story["product"] == "PAYVANTA"
    assert story["internal_policy_id"] == "REVIVE"
    assert "not the product" in story["role"].lower()
    assert story["declared_run"]["cells"] == 600
    assert story["declared_run"]["groups"] == 120
    assert story["declared_run"]["seeds"] == 20
    assert story["declared_run"]["profiles"] == 6
    assert story["declared_run"]["policies"] == 5
    assert story["declared_run"]["frozen_experiment_hash"] == DECLARED_FROZEN_EXPERIMENT
    assert story["m10"]["id"] == "M-10"
    assert story["m10"]["user_facing"] == "INCREMENTAL NET RECOVERY"
    assert {p["id"] for p in story["profiles"]} == {
        "BALANCED",
        "HIGH_NATURAL",
        "SCARCE",
        "ABUNDANT",
        "HOSTILE",
        "DEGRADED",
    }
    assert [p["id"] for p in story["policies"]] == ["B0", "B1", "B2", "B3", "REVIVE"]
    ids = [step["id"] for step in story["engineering"]]
    assert ids == ["M13.24", "M13.25", "M13.26", "M13.27", "CLOUD", "OFFICIAL"]
    assert story["access"]["git_tracked"] is False
    assert "artefacts/" in story["access"]["gitignore_rule"]
    assert story["reference_cell"] == {
        "seed": 14,
        "profile": "ABUNDANT",
        "policy": "REVIVE",
        "ui": "#/benchmark/matrix",
        "api": "/api/benchmark/official/cell/14/ABUNDANT/REVIVE",
    }
    banned = [p.lower() for p in story["do_not_claim"]]
    headline = (story["north_star"] + " " + story["differentiator"]).lower()
    for phrase in banned:
        assert phrase not in headline


def test_contract_without_artefacts(tmp_path: Path):
    missing = tmp_path / "artefacts" / "benchmark" / "official-cloud-final"
    contract = official_contract(missing)
    assert contract["verified"] is False
    assert contract["cell_count"] is None
    assert contract["expected_cell_count"] == 600
    assert contract["frozen_experiment_hash"] == DECLARED_FROZEN_EXPERIMENT
    assert contract["evidence_path"] == "artefacts/benchmark/official-cloud-final"
    assert contract["m10"]["id"] == "M-10"
    assert len(contract["engineering"]) == 6
    assert contract["access"]["git_tracked"] is False


def test_benchmark_lab_always_carries_story(tmp_path: Path):
    missing = tmp_path / "artefacts" / "benchmark" / "official-cloud-final"
    lab = benchmark_lab(missing)
    assert lab["story"]["declared_run"]["cells"] == 600
    assert lab["contract"]["verified"] is False
    assert lab["headline"] == "Measured, not claimed."


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_story_and_contract_http_endpoints():
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), PayvantaHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=180)
        conn.request("GET", "/api/benchmark/story")
        resp = conn.getresponse()
        assert resp.status == 200
        story = json.loads(resp.read().decode("utf-8"))
        assert story["m10"]["id"] == "M-10"
        assert story["why"]["cells"]["count"] == 600

        conn.request("GET", "/api/benchmark/official/contract")
        resp = conn.getresponse()
        assert resp.status == 200
        contract = json.loads(resp.read().decode("utf-8"))
        assert "benchmark_version" in contract
        assert "metric_version" in contract
        assert "frozen_experiment_hash" in contract
        assert contract["evidence_path"].endswith("official-cloud-final")
        assert contract["story"]["engineering"][0]["id"] == "M13.24"

        conn.request("POST", "/api/benchmark/official/contract", body=b"{}")
        resp = conn.getresponse()
        assert resp.status == 405
    finally:
        httpd.shutdown()
