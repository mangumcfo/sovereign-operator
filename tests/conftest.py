"""Hermetic test rig: a fake USN node (stdlib http.server) on loopback. Records every (method, path)
so tests can prove the operator only ever GETs. No network beyond 127.0.0.1."""
from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

RENEW_VERBATIM = ("NODE_KEYSTORE_DIR=/x python3 scripts/compute_share_offer.py --node N --units 100 "
                  "--renew-days 7 --approver KM --approval-ref r --requester-name Beard "
                  "--requester-public-hex ff --models m --registry /r --emit-grant /g.json --min-gpu-free-mib 20000")
REVOKE_VERBATIM = "rm /home/x/.sovereign_share/grant_Beard.json"

REQUESTS: list[tuple[str, str]] = []


def _status_doc():
    exp = (datetime.now(timezone.utc) + timedelta(days=8)).isoformat()
    return {
        "node_fp": "f864f89e4362f599",
        "gpu": {"state": "ok", "free_mib": 31778, "total_mib": 32607, "util_pct": 0},
        "peers": {"count": 1, "labels": ["Beard"]},
        "grants": [{"file": "grant_Beard.json", "peer": "Beard", "expires": exp,
                    "models": ["llama3.2:1b"], "renew_run": RENEW_VERBATIM, "revoke_run": REVOKE_VERBATIM}],
        "units_offered": 100, "puller_running": True, "model_up": True,
        "source": "sovereign_agent.agent.local_mind.facts",
    }


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        REQUESTS.append(("GET", self.path))
        p = self.path.split("?")[0]
        if p == "/api/v1/status":
            return self._send(200, _status_doc())
        if p == "/api/v1/breath_gate/pending":
            return self._send(200, {"count": 1, "pending": [
                {"req_id": "approval_1", "request": {"action_class": "boundary_crossing"},
                 "provenance": {"source": "http:port.crossing", "boundary": "external:x", "crossing_id": "c1"}}]})
        if p == "/api/v1/inference/receipts":
            return self._send(200, {"receipts": [{"seq": 0}]})
        if p == "/api/v1/audit/cylinders":
            return self._send(200, {"cylinders": [], "count": 0})
        if p == "/api/v1/storage/datum/known":
            return self._send(200, {"id": "known", "content": "x", "visibility": "owner"})
        return self._send(404, {"error": {"code": "ROUTE_NOT_FOUND"}})

    def do_POST(self):  # must NEVER be hit by a tool — recorded so tests fail loudly if it is
        REQUESTS.append(("POST", self.path))
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self._send(405, {"error": "operator must not POST"})


@pytest.fixture()
def usn(monkeypatch, tmp_path):
    REQUESTS.clear()
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    from sovereign_operator import config
    monkeypatch.setattr(config, "USN_BASE", f"http://127.0.0.1:{port}/api/v1")
    monkeypatch.setattr(config, "MIND_URL", "http://127.0.0.1:11434/v1/chat/completions")
    monkeypatch.setattr(config, "HOME", tmp_path / "sovop")
    monkeypatch.setattr(config, "NOTEBOOK_DB", tmp_path / "sovop" / "notebook.sqlite3")
    monkeypatch.setattr(config, "EXPORT_DIR", tmp_path / "sovop" / "exports")

    yield {"port": port, "requests": REQUESTS, "home": tmp_path / "sovop",
           "renew": RENEW_VERBATIM, "revoke": REVOKE_VERBATIM}
    httpd.shutdown()
