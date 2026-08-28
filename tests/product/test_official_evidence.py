"""Official benchmark evidence — read-only integration tests."""

from __future__ import annotations

import json
import socket
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

from revive.product.benchmark_lab import (
    DECLARED_FROZEN_EXPERIMENT,
    OFFICIAL_DIR,
    benchmark_lab,
    classify_artefact_tree,
)
from revive.product.official_evidence import (
    invalidate_cache,
    official_cell_detail,
    official_contract,
    official_matrix,
    official_summary,
    search_official_cells,
    verify_evidence,
)
from revive.product.server import PayvantaHandler, ThreadingHTTPServer

EVIDENCE = Path("artefacts/benchmark/official-cloud-final")


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(autouse=True)
def _reset_evidence_cache():
    invalidate_cache()
    yield
    invalidate_cache()


@pytest.mark.skipif(not EVIDENCE.is_dir(), reason="official-cloud-final not extracted locally")
class TestOfficialCloudFinal:
    def test_verify_evidence_passes(self):
        report = verify_evidence(EVIDENCE)
        assert report.cell_count == 600
        assert report.expected_cells == 600
        assert report.checks["cell_count_600"] is True
        assert report.checks["matrix_complete"] is True
        assert report.checks["frozen_experiment_hash"] is True
        assert report.checks["config_hash"] is True
        assert report.checks["validation"] is True
        assert report.checks["policy_pack"] is True
        assert report.status == "OFFICIAL_EVIDENCE_VERIFIED"
        assert report.verified is True

    def test_benchmark_lab_wires_verified_evidence(self):
        lab = benchmark_lab(EVIDENCE)
        assert lab["evidence_verified"] is True
        assert lab["evidence_status"] == "OFFICIAL_EVIDENCE_VERIFIED"
        assert lab["artefact_status"] == "VERIFIED"
        assert lab["policy_summaries"]["REVIVE"]["M-10_median_paise"] > 0
        mx = lab["profile_policy_matrix"]
        assert mx["verified"] is True
        assert mx.get("lazy_load") is True
        full = official_matrix(EVIDENCE)
        assert full["matrix"]["ABUNDANT"]["REVIVE"]["m10_median_paise"] is not None

    def test_official_matrix_complete(self):
        mx = official_matrix(EVIDENCE)
        assert mx["verified"] is True
        assert mx["status"] == "ready"
        assert mx["cell_groups"] == 30
        assert len(mx["profiles"]) == 6
        assert len(mx["policies"]) == 5
        for profile in mx["profiles"]:
            assert set(mx["matrix"][profile]) == set(mx["policies"])

    def test_matrix_endpoint_http(self):
        port = _free_port()
        httpd = ThreadingHTTPServer(("127.0.0.1", port), PayvantaHandler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            conn = HTTPConnection("127.0.0.1", port, timeout=120)
            conn.request("GET", "/api/benchmark/official/matrix")
            resp = conn.getresponse()
            assert resp.status == 200
            body = json.loads(resp.read().decode("utf-8"))
            assert body["status"] == "ready"
            assert body["cell_groups"] == 30
            assert body["matrix"]["ABUNDANT"]["REVIVE"]["m10_median_paise"] is not None
        finally:
            httpd.shutdown()

    def test_cell_lookup_abundant_revive_seed_14(self):
        detail = official_cell_detail(14, "ABUNDANT", "REVIVE", EVIDENCE)
        assert detail["seed"] == 14
        assert detail["profile"] == "ABUNDANT"
        assert detail["policy"] == "REVIVE"
        assert detail["run_valid"] is True
        assert detail["m10_incremental_net"]["paise"] is not None
        assert detail["metrics_checksum"]
        assert detail["metrics"]["run_valid"] is True
        assert detail["validation"]["run_valid"] is True
        assert detail["validation"]["metrics_checksum"] == detail["metrics_checksum"]
        assert detail["artifact"] == detail["artefact_path"]
        assert detail["raw"]["cell_index"] == 410

    def test_search_finds_cell(self):
        hits = search_official_cells("14 ABUNDANT REVIVE", EVIDENCE)
        assert hits
        assert hits[0]["seed"] == 14
        assert hits[0]["profile"] == "ABUNDANT"
        assert hits[0]["policy"] == "REVIVE"

    def test_summary_provenance_fields(self):
        summary = official_summary(EVIDENCE)
        prov = summary["provenance"]
        assert prov["source"] == "OFFICIAL CLOUD RUN"
        assert prov["frozen_experiment_reference"] == DECLARED_FROZEN_EXPERIMENT
        assert prov["policy_pack_version"] == "pol_m13_official_v1"
        assert prov["cells"] == 600
        assert prov["blocked"] is False
        contract = summary["contract"]
        assert contract["verified"] is True
        assert contract["cell_count"] == 600
        assert contract["group_count"] == 120
        assert contract["seed_count"] == 20
        assert contract["profile_count"] == 6
        assert contract["policy_count"] == 5
        assert contract["validation"] == "BENCHMARK_VALID"
        assert contract["blocked"] is False
        assert contract["frozen_experiment_hash"] == DECLARED_FROZEN_EXPERIMENT
        assert contract["config_hash"]
        assert contract["benchmark_version"]
        assert contract["metric_version"]
        assert contract["policy_pack"]["version"]
        assert contract["evidence_path"].endswith("official-cloud-final")


def test_invalidated_official_tree_still_inadmissible():
    from revive.product.benchmark_lab import INVALIDATED_OFFICIAL

    assert classify_artefact_tree(INVALIDATED_OFFICIAL) == "INADMISSIBLE"


def test_cell_detail_rejects_invalid_params():
    if not EVIDENCE.is_dir():
        pytest.skip("official-cloud-final not extracted locally")
    with pytest.raises(ValueError, match="invalid seed"):
        official_cell_detail(999, "ABUNDANT", "REVIVE", EVIDENCE)
    with pytest.raises(ValueError, match="invalid profile"):
        official_cell_detail(14, "../etc", "REVIVE", EVIDENCE)
    with pytest.raises(ValueError, match="invalid policy"):
        official_cell_detail(14, "ABUNDANT", "EVIL", EVIDENCE)


def test_missing_cell_not_found():
    if not EVIDENCE.is_dir():
        pytest.skip("official-cloud-final not extracted locally")
    missing = EVIDENCE / "cells" / "seed-001" / "ABUNDANT" / "MISSING.json"
    if missing.is_file():
        pytest.skip("unexpected test fixture")
    # valid params but file removed would 404 — use invalid combo via wrong seed path
    with pytest.raises(FileNotFoundError):
        official_cell_detail(14, "ABUNDANT", "REVIVE", Path("artefacts/benchmark/does-not-exist"))


@pytest.mark.skipif(not EVIDENCE.is_dir(), reason="official-cloud-final not extracted locally")
def test_official_http_endpoints_read_only():
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), PayvantaHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=30)
        conn.request("GET", "/api/benchmark/official/cell/14/ABUNDANT/REVIVE")
        resp = conn.getresponse()
        assert resp.status == 200
        body = json.loads(resp.read().decode("utf-8"))
        assert body["policy"] == "REVIVE"

        conn.request("POST", "/api/benchmark/official/summary", body=b"{}")
        resp = conn.getresponse()
        assert resp.status == 405

        conn.request("GET", "/api/benchmark/official/cell/not-a-seed/ABUNDANT/REVIVE")
        resp = conn.getresponse()
        assert resp.status == 400

        conn.request("GET", "/api/benchmark/official/search?q=14+ABUNDANT+REVIVE")
        resp = conn.getresponse()
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["results"]

        conn.request("GET", "/api/benchmark/official/matrix")
        resp = conn.getresponse()
        assert resp.status == 200
        matrix = json.loads(resp.read().decode("utf-8"))
        assert matrix["status"] == "ready"
        assert matrix["cell_groups"] == 30
    finally:
        httpd.shutdown()


def test_evidence_tree_not_modified_by_product_layer(tmp_path: Path):
    if not EVIDENCE.is_dir():
        pytest.skip("official-cloud-final not extracted locally")
    before = {
        p.relative_to(EVIDENCE): p.read_bytes()
        for p in [
            EVIDENCE / "manifest.json",
            EVIDENCE / "aggregate.json",
            EVIDENCE / "validation.json",
        ]
    }
    benchmark_lab(EVIDENCE)
    verify_evidence(EVIDENCE)
    official_summary(EVIDENCE)
    official_cell_detail(14, "ABUNDANT", "REVIVE", EVIDENCE)
    official_contract(EVIDENCE)
    for rel, content in before.items():
        assert (EVIDENCE / rel).read_bytes() == content
