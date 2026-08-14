"""Fence tests — the operator's locks, hermetic (fake USN on loopback). These pre-stage the AA bar
rows U2/U3/U4/U5/U7 and the deny-by-default + loopback fences; AA runs the live U1–U10.
"""
from __future__ import annotations

import pathlib

import pytest

from sovereign_operator import tools
from sovereign_operator.http_client import UsnUnreachable, usn_get
from sovereign_operator.memory.store import Notebook


# ── U2/U3 · read-and-draft only: a full tool sweep POSTs nothing to the USN ────────────────────────
def test_full_tool_sweep_is_get_only(usn):
    tools.usn_status()
    tools.usn_list_pending_gates()
    tools.usn_receipts("inference", 5)
    tools.usn_receipts("audit", 5)
    tools.usn_peers()
    tools.usn_storage_read("known")
    tools.usn_capacity_propose()
    tools.usn_gate_prepare("approval_1")
    # draft tools must make NO request at all — pure text
    tools.usn_propose_port_crossing("relay", {"send": "ref://x"}, "why")
    tools.usn_storage_propose("ref://note", "why")
    tools.usn_refuse_peer_prepare("peerX", "why")
    tools.usn_clean_exit_prepare("why")

    methods = {m for m, _ in usn["requests"]}
    assert methods == {"GET"}, f"operator hit the node with non-GET: {usn['requests']}"
    assert not any(m == "POST" for m, _ in usn["requests"])


# ── U3 · draft tools carry RUN text, never execute; the POST strings live only inside drafts ────────
def test_draft_tools_return_run_text_not_actions(usn):
    for fn, args in [
        (tools.usn_propose_port_crossing, ("relay", {"send": "ref://x"}, "why")),
        (tools.usn_storage_propose, ("ref://note", "why")),
        (tools.usn_refuse_peer_prepare, ("peerX", "why")),
        (tools.usn_clean_exit_prepare, ("why",)),
    ]:
        r = fn(*args)
        assert r["ok"] and r["data"]["RUN"].startswith("curl")
        assert "NOT executed" in r["data"]["GATE"]
    # gate_prepare surfaces the exact owner act as text, never calls it
    g = tools.usn_gate_prepare("approval_1")
    assert g["ok"] and g["data"]["RUN_deny"].startswith("curl")
    assert "sanction" in g["data"]["RUN_approve"]  # port-crossing gate → sanction route (text only)


# ── deny-by-default · a 404/absent route → OUT, never invented ─────────────────────────────────────
def test_deny_on_404(usn):
    r = tools.usn_storage_read("does-not-exist")
    assert r["ok"] is False and r["out_reason"] == "route not in live API — OUT"
    g = tools.usn_gate_prepare("no-such-gate")
    assert g["ok"] is False and "OUT" in g["out_reason"]


# ── U7 · capacity drafts are byte-equal to the node's own strings ──────────────────────────────────
def test_capacity_verbatim(usn):
    r = tools.usn_capacity_propose()
    assert r["ok"]
    p = r["data"]["proposals"][0]
    assert p["renew_run"] == usn["renew"]          # byte-for-byte
    assert p["revoke_run"] == usn["revoke"]


# ── loopback fence · a non-loopback USN url is refused, not tried ──────────────────────────────────
def test_loopback_only(monkeypatch):
    from sovereign_operator import config
    monkeypatch.setattr(config, "USN_BASE", "http://10.0.0.5:8421/api/v1")
    with pytest.raises(ValueError):
        usn_get("/status")


# ── failure law · node down → UsnUnreachable (caller degrades to memory, never fabricates) ─────────
def test_node_down_raises_unreachable(monkeypatch):
    from sovereign_operator import config
    # nothing is listening on this loopback port
    monkeypatch.setattr(config, "USN_BASE", "http://127.0.0.1:9/api/v1")
    with pytest.raises(UsnUnreachable):
        usn_get("/status")


# ── U4 · memory is repo-side only: the notebook file lives under OPERATOR_HOME, nowhere near USN ────
def test_memory_repo_side(usn):
    nb = Notebook()
    nb.append("t", "km", "hello")
    nb.record_proposal("capacity", "renew Beard", "curl ...")
    assert nb.open_proposals()[0]["summary"] == "renew Beard"
    db = pathlib.Path(nb.path)
    assert usn["home"] in db.parents, f"notebook escaped OPERATOR_HOME: {db}"
    nb.close()
    # a memory session made ZERO requests to the node
    assert usn["requests"] == []
