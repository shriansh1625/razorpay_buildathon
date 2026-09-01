"""Stdlib product server — no extra web framework dependency."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from revive.product.benchmark_lab import benchmark_lab
from revive.product.benchmark_story import benchmark_story
from revive.product.intelligence.diagnosis import (
    diagnose_opportunity,
    economic_decision,
    intelligence_event,
)
from revive.product.intelligence.status import intelligence_status
from revive.product.official_evidence import (
    official_cell_detail,
    official_contract,
    official_matrix,
    official_summary,
    search_official_cells_page,
)
from revive.product.project import find_trace
from revive.product.overview import product_overview
from revive.product.session import (
    DEMO_SEED,
    ProductSession,
    build_demo_session,
)
from revive.product.simulator import run_simulator

UI_DIR = Path(__file__).resolve().parent / "ui"

_SESSION: ProductSession | None = None
_SNAPSHOT: dict | None = None
_RUN_COUNT = 0
_AI_CACHE: dict[str, dict] = {}
_AI_EVENTS: list[dict] = []
_LAST_AI_STATUS: str | None = None


def _clear_ai_state() -> None:
    global _LAST_AI_STATUS
    _AI_CACHE.clear()
    _AI_EVENTS.clear()
    _LAST_AI_STATUS = None


def _ai_audit_rows() -> list[dict]:
    """Product-layer overlay rows. Not appended to the engine AuditJournal."""
    rows: list[dict] = []
    for ev in _AI_EVENTS[-20:]:
        rows.append(
            {
                "timestamp": ev.get("timestamp") or "ai",
                "category": "intelligence",
                "event": ev.get("event") or "AI_DIAGNOSIS_COMPLETED",
                "stage": "AI_DIAGNOSIS",
                "label": "Sandbox AI diagnosis overlay",
                "object": ev.get("opportunity_id"),
                "decision": ev.get("primary_cause"),
                "result": ev.get("status"),
                "blocked": False,
                "audit_reference": None,
                "layer": ev.get("layer") or "product_sandbox_overlay",
                "source": ev.get("source"),
                "model": ev.get("model"),
                "schema_version": ev.get("schema_version"),
                "money_path": False,
                "note": ev.get("note")
                or "Not a money-path event. Engine hash journal is unchanged.",
            }
        )
    return rows


def _enrich_snapshot(base: dict) -> dict:
    enriched = dict(base)
    enriched["intelligence_status"] = intelligence_status(last_status=_LAST_AI_STATUS)
    enriched["intelligence_events"] = list(_AI_EVENTS[-20:])
    enriched["audit_ledger"] = list(base.get("audit_ledger") or []) + _ai_audit_rows()
    return enriched


def _session() -> ProductSession:
    global _SESSION, _SNAPSHOT
    if _SESSION is None:
        _SESSION = build_demo_session()
        _SNAPSHOT = _SESSION.snapshot()
    return _SESSION


def _snapshot() -> dict:
    _session()
    assert _SNAPSHOT is not None
    return _enrich_snapshot(_SNAPSHOT)


def _intelligence_receipt_block(cached: dict) -> dict:
    proposal = cached.get("proposal") or {}
    return {
        "source": cached.get("source"),
        "status": cached.get("status"),
        "model": cached.get("model"),
        "provider": cached.get("provider"),
        "ai_proposal_primary_cause": proposal.get("primary_cause"),
        "ai_proposal_candidates": [
            c.get("action_id") for c in (proposal.get("candidate_actions") or [])
        ],
        "final_decision_authority": "deterministic_engine",
        "execution_authority": "none",
    }


def _ai_diagnosis_for(opportunity_id: str) -> dict:
    if opportunity_id in _AI_CACHE:
        return _AI_CACHE[opportunity_id]
    trace = find_trace(_session().state, opportunity_id)
    if trace is None:
        raise KeyError(opportunity_id)
    result = diagnose_opportunity(trace)
    payload = {
        **result.to_dict(),
        "economic_decision": economic_decision(trace),
        "trust_boundary": {
            "ai": "understand · propose",
            "control": "validate · authorize",
            "engine": "execute · measure",
        },
    }
    _AI_CACHE[opportunity_id] = payload
    global _LAST_AI_STATUS
    _LAST_AI_STATUS = result.status
    _AI_EVENTS.append(intelligence_event(result))
    if len(_AI_EVENTS) > 50:
        del _AI_EVENTS[:-50]
    return payload


def _recovery_run(body: dict) -> dict:
    """Bounded sandbox batch run: regenerate the session world on a new seed.

    The run is real — it rebuilds the deterministic world, runs the full traced
    engine across four cycles, settles scheduled executions, and re-projects the
    snapshot. `seed` is caller-supplied within a bounded range; when absent the
    server advances its own run counter so each press produces a new bounded run
    without ever touching the official evidence tree.
    """
    global _SESSION, _SNAPSHOT, _RUN_COUNT
    _RUN_COUNT += 1
    _clear_ai_state()
    seed = body.get("seed")
    try:
        seed = int(seed) if seed is not None else DEMO_SEED + _RUN_COUNT * 7
    except (TypeError, ValueError):
        raise _BadRequest("seed must be an integer") from None
    if not 1 <= seed <= 9999:
        raise _BadRequest("seed must be between 1 and 9999")
    _SESSION = build_demo_session(seed=seed)
    _SNAPSHOT = _SESSION.snapshot()
    return {
        "run_index": _RUN_COUNT,
        "seed": seed,
        "environment": "PAYVANTA Sandbox",
        "execution": "Bounded local execution",
        **_SNAPSHOT,
    }


class _BadRequest(ValueError):
    """A client-supplied value the simulator cannot accept."""


# The seed and count fields are user-editable, and a cleared number input posts "".
# ``int("")`` raised straight out of the handler, which killed the connection and
# surfaced in the browser as "TypeError: Failed to fetch" — a transport error standing
# in for a validation error. Bad input is answered, not crashed on.
def _int_field(body: dict, key: str, default: int, low: int, high: int) -> int:
    raw = body.get(key, default)
    if raw is None or raw == "":
        raw = default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise _BadRequest(f"{key} must be a whole number.") from None
    if not low <= value <= high:
        raise _BadRequest(f"{key} must be between {low} and {high}.")
    return value


def _choice_field(body: dict, key: str, default: str, allowed: tuple[str, ...]) -> str:
    value = str(body.get(key) or default)
    if value not in allowed:
        raise _BadRequest(f"{key} must be one of: {', '.join(allowed)}.")
    return value


FAILURE_TYPES = (
    "PAYMENT_FAILURE",
    "SUBSCRIPTION_FAILURE",
    "CHECKOUT_ABANDONMENT",
    "RECEIVABLE_OVERDUE",
)
PROFILES = ("BALANCED", "HIGH_NATURAL", "SCARCE", "ABUNDANT", "HOSTILE", "DEGRADED")
URGENCIES = ("normal", "high")


class PayvantaHandler(BaseHTTPRequestHandler):
    server_version = "PAYVANTA/0.1"

    def log_message(self, fmt: str, *args: object) -> None:
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("PAYVANTA " + (fmt % args) + "\n")

    def _json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _reject_official_write(self) -> bool:
        if urlparse(self.path).path.startswith("/api/benchmark/official"):
            self._json({"error": "official benchmark evidence is read-only"}, 405)
            return True
        return False

    def _handle_official_get(self, path: str, query: dict[str, list[str]]) -> bool:
        if not path.startswith("/api/benchmark/official"):
            return False

        if path in ("/api/benchmark/official", "/api/benchmark/official/summary"):
            self._json(official_summary())
            return True
        if path == "/api/benchmark/official/contract":
            self._json(official_contract())
            return True
        if path in ("/api/benchmark/official/story",):
            self._json(benchmark_story())
            return True
        if path == "/api/benchmark/official/matrix":
            self._json(official_matrix())
            return True
        if path == "/api/benchmark/official/search":
            q = (query.get("q") or [""])[0]
            self._json({"query": q, **search_official_cells_page(q)})
            return True

        parts = path.split("/")
        if len(parts) == 8 and parts[3] == "official" and parts[4] == "cell":
            try:
                seed = int(parts[5])
            except ValueError:
                self._json({"error": "invalid seed"}, 400)
                return True
            profile = parts[6]
            policy = parts[7]
            try:
                self._json(official_cell_detail(seed, profile, policy))
            except ValueError as exc:
                self._json({"error": str(exc)}, 400)
            except FileNotFoundError:
                self._json({"error": "cell not found"}, 404)
            return True

        if path.startswith("/api/benchmark/official/"):
            self._json({"error": "not found"}, 404)
            return True

        return False

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)
        if self._handle_official_get(path, query):
            return
        if path in ("/", "/index.html"):
            self._file(UI_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path == "/app.css":
            self._file(UI_DIR / "app.css", "text/css; charset=utf-8")
            return
        if path == "/app.js":
            self._file(UI_DIR / "app.js", "text/javascript; charset=utf-8")
            return
        if path in ("/api/product/overview", "/api/product"):
            self._json(product_overview(_snapshot(), benchmark_lab(), run_index=_RUN_COUNT))
            return
        if path == "/api/control-room":
            self._json(_snapshot()["control_room"])
            return
        if path == "/api/snapshot":
            self._json(_snapshot())
            return
        if path == "/api/audit":
            snap = _snapshot()
            events = list(snap["audit_ledger"])
            obj = (query.get("object") or [None])[0]
            if obj:
                events = [e for e in events if e.get("object") == obj]
            self._json(
                {
                    "environment": "SANDBOX",
                    "seed": snap["control_room"]["seed"],
                    "count": len(events),
                    "events": events,
                }
            )
            return
        if path == "/api/runs":
            snap = _snapshot()
            cr = snap["control_room"]
            self._json(
                {
                    "environment": "SANDBOX",
                    "server_run_index": _RUN_COUNT,
                    "current_seed": cr["seed"],
                    "cycles_run": cr["cycles_run"],
                    "note": (
                        "POST /api/recovery-run rebuilds the sandbox world. "
                        "Browser recent-run history is local to the client session."
                    ),
                }
            )
            return
        if path == "/api/intelligence/status":
            self._json(intelligence_status(last_status=_LAST_AI_STATUS))
            return
        if path.startswith("/api/receipt/"):
            oid = path.rsplit("/", 1)[-1]
            detail = _snapshot()["opportunities"].get(oid)
            if detail is None:
                self._json({"error": "unknown opportunity"}, 404)
                return
            receipt = dict(detail["receipt"])
            if oid in _AI_CACHE:
                receipt["intelligence"] = _intelligence_receipt_block(_AI_CACHE[oid])
            self._json(receipt)
            return
        if path.startswith("/api/opportunity/"):
            parts = [p for p in path.split("/") if p]
            if len(parts) < 3:
                self._json({"error": "unknown opportunity"}, 404)
                return
            oid = parts[2]
            detail = _snapshot()["opportunities"].get(oid)
            if detail is None:
                self._json({"error": "unknown opportunity"}, 404)
                return
            if len(parts) == 4 and parts[3] == "receipt":
                receipt = dict(detail["receipt"])
                if oid in _AI_CACHE:
                    receipt["intelligence"] = _intelligence_receipt_block(_AI_CACHE[oid])
                self._json(receipt)
                return
            if len(parts) == 3:
                out = dict(detail)
                if oid in _AI_CACHE:
                    out["ai_diagnosis"] = _AI_CACHE[oid]
                self._json(out)
                return
            self._json({"error": "not found"}, 404)
            return
        if path == "/api/benchmark":
            self._json(benchmark_lab())
            return
        if path == "/api/benchmark/story":
            self._json(benchmark_story())
            return
        self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        if self._reject_official_write():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/recovery-run":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json({"error": "invalid json"}, 400)
                return
            try:
                self._json(_recovery_run(body))
            except _BadRequest as exc:
                self._json({"error": str(exc)}, 400)
            return
        if parsed.path.startswith("/api/opportunity/") and parsed.path.endswith("/ai-diagnosis"):
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) != 4 or parts[3] != "ai-diagnosis":
                self._json({"error": "not found"}, 404)
                return
            oid = parts[2]
            if oid not in _snapshot()["opportunities"]:
                self._json({"error": "unknown opportunity"}, 404)
                return
            try:
                self._json(_ai_diagnosis_for(oid))
            except KeyError:
                self._json({"error": "unknown opportunity"}, 404)
            return
        if parsed.path != "/api/simulator":
            self._json({"error": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._json({"error": "invalid json"}, 400)
            return
        try:
            result = run_simulator(
                failure_type=_choice_field(body, "failure_type", "PAYMENT_FAILURE", FAILURE_TYPES),
                seed=_int_field(body, "seed", 7, 1, 9999),
                opportunity_count=_int_field(body, "opportunity_count", 12, 1, 200),
                profile=_choice_field(body, "profile", "SCARCE", PROFILES),
                urgency=_choice_field(body, "urgency", "normal", URGENCIES),
            )
        except _BadRequest as exc:
            self._json({"error": str(exc)}, 400)
            return
        except ValueError as exc:
            # The engine rejected an otherwise well-formed configuration.
            self._json({"error": f"The engine rejected this configuration: {exc}"}, 400)
            return
        self._json(result)

    def do_PATCH(self) -> None:  # noqa: N802
        if self._reject_official_write():
            return
        self._json({"error": "not found"}, 404)

    def do_PUT(self) -> None:  # noqa: N802
        if self._reject_official_write():
            return
        self._json({"error": "not found"}, 404)

    def do_DELETE(self) -> None:  # noqa: N802
        if self._reject_official_write():
            return
        self._json({"error": "not found"}, 404)


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = ThreadingHTTPServer((host, port), PayvantaHandler)
    print(f"PAYVANTA Control Room  http://{host}:{port}")
    print("Demonstration fixture — synthetic engine session.")
    print("Official benchmark evidence: read-only at artefacts/benchmark/official-cloud-final/")
    httpd.serve_forever()


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="revive control-room")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
