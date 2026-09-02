from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from sovereign_operator import needs_you
from sovereign_operator.node_runtime import node_runtime
from sovereign_operator.port_client import port_state


PORT_STATE = {
    "ok": True,
    "ts": "2026-09-01T14:12:09-0600",
    "kpi": {"open_node": {"state": "BLOCKED", "click": False, "fp": "a682845eb6d5"}},
    "rows": [
        {"owns": "KM", "obligation_id": "hold:km", "current_obligation": "Do not click",
         "state": "BLOCKED", "blocks_open_node": True},
        {"owns": "Port", "obligation_id": "hold:port", "current_obligation": "Healthy work",
         "state": "WORKING"},
        {"owns": "AA", "obligation_id": "hold:aa", "current_obligation": "Score tray",
         "state": "QUIET"},
    ],
}


def test_needs_you_is_exception_only_and_preserves_blocker():
    result = needs_you.build([], PORT_STATE)
    assert result["cards"] == []
    assert [card["id"] for card in result["parked"]] == ["port:hold:aa"]
    assert result["kpi"]["open_node"]["click"] is False


def test_open_node_transition_requires_complete_truthful_port_signal():
    ready = {**PORT_STATE, "kpi": {**PORT_STATE["kpi"], "open_node": {
        "state": "READY", "click": True, "fp": "a682845eb6d5ac5b",
    }}}
    result = needs_you.build([], ready)
    assert result["count"] == 1
    assert result["cards"] == [{
        "id": "open-node",
        "source": "Port :8490",
        "kind": "DECISION",
        "state": "READY",
        "what": "OPEN MY NODE",
        "why": "Port verified this IRON and fingerprint a682845eb6d5ac5b.",
        "evidence": {"fingerprint": "a682845eb6d5ac5b"},
        "exact_effect": "Open the local node ceremony in this browser.",
        "disposition": "HUMAN_ACTION",
        "action_url": "http://127.0.0.1:8477/",
    }]
    assert result["kpi"]["open_node"] == {
        "state": "READY", "click": True, "fp": "a682845eb6d5ac5b",
    }


@pytest.mark.parametrize("open_node", [
    {"state": "READY", "click": True, "fp": "wrong-iron"},
    {"state": "READY", "click": False, "fp": "a682845eb6d5ac5b"},
    {"state": "BLOCKED", "click": True, "fp": "a682845eb6d5ac5b"},
])
def test_open_node_transition_fails_closed_on_partial_or_conflicting_signal(open_node):
    port = {**PORT_STATE, "kpi": {**PORT_STATE["kpi"], "open_node": open_node}}
    result = needs_you.build([], port)
    assert result["count"] == 0
    assert result["cards"] == []
    assert result["kpi"]["open_node"]["state"] == "BLOCKED"
    assert result["kpi"]["open_node"]["click"] is False


def test_authoritative_runtime_open_suppresses_stale_ready_card():
    stale_ready = {**PORT_STATE, "kpi": {**PORT_STATE["kpi"], "open_node": {
        "state": "READY", "click": True, "fp": "a682845eb6d5ac5b",
    }}}
    runtime = {"open": True, "fingerprint": "a682845eb6d5ac5b"}
    result = needs_you.build([], stale_ready, runtime=runtime)
    assert result["count"] == 0
    assert result["cards"] == []
    assert result["kpi"]["open_node"] == {
        "state": "OPEN", "click": False, "fp": "a682845eb6d5ac5b",
        "display_fp": "a682845eb6d5",
        "detail": "The local ERP reports this node is already open.",
    }
    assert result["feeds"]["runtime"]["open"] is True


def test_runtime_open_with_wrong_identity_does_not_override_port():
    runtime = {"open": True, "fingerprint": "wrong-iron"}
    result = needs_you.build([], PORT_STATE, runtime=runtime)
    assert result["kpi"]["open_node"]["state"] == "BLOCKED"
    assert result["feeds"]["runtime"]["open"] is False


def test_pending_gate_rises_before_port_obligations():
    gate = {"gate": {"req_id": "g1", "request": {"action_class": "port_crossing"},
                     "provenance": {"boundary": "external", "source": "agent"}},
            "dispose": {"PROPOSE": "sanction crossing c1", "RUN_approve": "curl approve",
                        "RUN_deny": "curl deny"}}
    result = needs_you.build([gate], PORT_STATE)
    assert result["cards"][0]["id"] == "gate:g1"
    assert result["cards"][0]["disposition"] == "DRAFT_ONLY"


class _PortHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        assert self.path == "/api/state"
        body = json.dumps(PORT_STATE).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


class _RuntimeHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/api/vocab":
            body = {"open": True, "expected_fp_configured": True}
        elif self.path == "/api/status":
            body = {"identity": {"present": True, "fingerprint": "a682845eb6d5ac5b",
                                 "public_hex": "must-not-leak"}}
        else:
            self.send_response(404)
            self.end_headers()
            return
        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)


def test_port_client_is_get_only_and_loopback(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), _PortHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    from sovereign_operator import config
    monkeypatch.setattr(config, "PORT_BASE", f"http://127.0.0.1:{server.server_address[1]}")
    try:
        assert port_state()["kpi"]["open_node"]["state"] == "BLOCKED"
    finally:
        server.shutdown()


def test_port_client_refuses_non_loopback(monkeypatch):
    from sovereign_operator import config
    monkeypatch.setattr(config, "PORT_BASE", "http://10.0.0.5:8490")
    with pytest.raises(ValueError):
        port_state()


def test_node_runtime_combines_get_only_facts_without_key_material(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), _RuntimeHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    from sovereign_operator import config
    monkeypatch.setattr(config, "ERP_BASE", f"http://127.0.0.1:{server.server_address[1]}")
    try:
        assert node_runtime() == {
            "ok": True, "open": True, "expected_fp_configured": True,
            "fingerprint": "a682845eb6d5ac5b",
        }
    finally:
        server.shutdown()
