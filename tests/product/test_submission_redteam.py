"""Submission red team — official evidence writes, traversal, overview honesty."""

from __future__ import annotations

import json
import socket
import threading
from http.client import HTTPConnection

import pytest

from revive.product.official_evidence import official_cell_detail
from revive.product.server import PayvantaHandler, ThreadingHTTPServer


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def test_official_writes_rejected():
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), PayvantaHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", port, timeout=30)
        for method, path in (
            ("POST", "/api/benchmark/official/summary"),
            ("PUT", "/api/benchmark/official/summary"),
            ("PATCH", "/api/benchmark/official/contract"),
            ("DELETE", "/api/benchmark/official/cell/14/ABUNDANT/REVIVE"),
        ):
            conn.request(method, path, body=b"{}")
            resp = conn.getresponse()
            body = json.loads(resp.read().decode("utf-8"))
            assert resp.status == 405, (method, path, resp.status, body)
            assert "read-only" in body.get("error", "")
    finally:
        httpd.shutdown()


def test_cell_path_traversal_rejected():
    with pytest.raises(ValueError, match="invalid profile"):
        official_cell_detail(14, "../etc", "REVIVE")
    with pytest.raises(ValueError, match="invalid policy"):
        official_cell_detail(14, "ABUNDANT", "EVIL")
    with pytest.raises(ValueError, match="invalid seed"):
        official_cell_detail(0, "ABUNDANT", "REVIVE")


def test_overview_exposes_intelligence_and_track03():
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
        assert ov["intelligence"]["llm_used"] is False
        assert ov["integrity"]["sandbox_is_not_official_evidence"] is True
        assert ov["integrity"]["official_evidence_writable_by_product"] is False
        assert ov["track03"]["audit_trail"] is True
    finally:
        httpd.shutdown()
