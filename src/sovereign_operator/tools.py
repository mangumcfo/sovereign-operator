"""tools.py — the whole tool layer, one greppable file. Every tool is a READ or a DRAFT. Nothing here
POSTs a USN route (Q1 lock). No tool holds state; memory is the notebook's job (memory/store.py).

Uniform contract: each tool returns {"ok": bool, "data": ...} on success, or
{"ok": false, "out_reason": "..."} when the live API has no such route (deny-by-default — the tool
layer may NOT invent a route). A node that is down raises UsnUnreachable up to the caller, which then
degrades to memory-only and labels the facts stale (never fabricates).

Draft tools return a `run` field: the EXACT command KM pastes on their own keyboard (or the console
Gate Inbox). The operator never runs it. The strings 'approve'/'deny'/'sanction'/POST appear ONLY
inside these RUN drafts — never as a call this process makes (verify rows U2/U3).
"""
from __future__ import annotations

import json
import shlex

from . import config
from .http_client import UsnUnreachable, usn_get

OUT = "route not in live API — OUT"


def _ok(data):
    return {"ok": True, "data": data}


def _out(reason: str = OUT):
    return {"ok": False, "out_reason": reason}


def _get(path: str):
    """GET a route; map 404/absent → OUT (deny-by-default). Propagates UsnUnreachable (node down)."""
    status, body = usn_get(path)
    if status == 404:
        return None, _out()
    if status >= 400:
        return None, _out(f"node returned {status} — {OUT}")
    return body, None


def _curl(method: str, path: str, body: dict | None = None) -> str:
    """Build the EXACT curl RUN text KM would paste. This is text, not an action."""
    url = f"{config.USN_BASE}{path}"
    parts = ["curl", "-s", "-X", method, shlex.quote(url), "-H", "'Content-Type: application/json'"]
    if body is not None:
        parts += ["-d", shlex.quote(json.dumps(body))]
    return " ".join(parts)


# ── READ tools ────────────────────────────────────────────────────────────────────────────────────

def usn_status() -> dict:
    """The ONE fact source (GET /status). The agent must never cache-and-assert stale facts as live."""
    data, err = _get("/status")
    return err or _ok(data)


def usn_list_pending_gates() -> dict:
    """Pending human-approval requests (GET /breath_gate/pending) — id · verb · boundary · provenance."""
    data, err = _get("/breath_gate/pending")
    if err:
        return err
    items = data.get("pending", data) if isinstance(data, dict) else data
    return _ok({"count": len(items or []), "pending": items or []})


def usn_receipts(kind: str = "inference", n: int = 20) -> dict:
    """Read what ACTUALLY happened from receipts (not memory). kind: 'inference' | 'audit'."""
    path = "/inference/receipts" if kind == "inference" else "/audit/cylinders"
    data, err = _get(f"{path}?limit={int(n)}")
    return err or _ok(data)


def usn_peers() -> dict:
    """Peer facts, read from the one status doc."""
    data, err = _get("/status")
    if err:
        return err
    return _ok((data or {}).get("peers", {"count": 0, "labels": []}))


def usn_storage_read(datum_id: str) -> dict:
    """Owner-scoped datum read (GET /storage/datum/<id>)."""
    data, err = _get(f"/storage/datum/{datum_id}")
    return err or _ok(data)


# ── DRAFT tools (RUN text only; never executed here) ────────────────────────────────────────────────

def usn_capacity_propose() -> dict:
    """Return the node's OWN exact renew_run / revoke_run strings, VERBATIM (CH7-fixed, copy-paste).

    The operator never re-authors these — byte-for-byte what /status carries (verify row U7).
    """
    data, err = _get("/status")
    if err:
        return err
    grants = (data or {}).get("grants", [])
    proposals = []
    for g in grants:
        proposals.append({
            "peer": g.get("peer"),
            "expires": g.get("expires"),
            "renew_run": g.get("renew_run"),      # verbatim from the node
            "revoke_run": g.get("revoke_run"),    # verbatim from the node
            "note": "PROPOSAL — copy to your keyboard. The operator does not run this; issuing is a human act.",
        })
    return _ok({"count": len(proposals), "proposals": proposals,
                "gate": "issue/renew/revoke is a human act (KM keyboard / Gate Inbox). NOT executed."})


def usn_gate_prepare(gate_id: str) -> dict:
    """Surface a pending gate + the EXACT act KM would take. Never calls approve/deny (those are
    @require_owner human acts and stay so)."""
    data, err = _get("/breath_gate/pending")
    if err:
        return err
    items = data.get("pending", []) if isinstance(data, dict) else (data or [])
    match = next((i for i in items if (i.get("req_id") or i.get("id")) == gate_id), None)
    if not match:
        return _out(f"no pending gate '{gate_id}' — {OUT}")
    prov = match.get("provenance", {}) or {}
    is_port = prov.get("source") == "http:port.crossing" and prov.get("crossing_id")
    approve = (_curl("POST", f"/port/crossing/{prov['crossing_id']}/sanction", {"named_human": config.PRINCIPAL})
               if is_port else _curl("POST", f"/breath_gate/{gate_id}/approve", {}))
    return _ok({
        "gate": match,
        "PROPOSE": f"dispose gate {gate_id} ({match.get('request', {}).get('action_class', '?')})",
        "RUN_approve": approve,
        "RUN_deny": _curl("POST", f"/breath_gate/{gate_id}/deny", {"reason": "<why>"}),
        "GATE": "owner-only (@require_owner) — the operator surfaces this; KM disposes. NOT executed.",
    })


def usn_propose_port_crossing(target: str, instruction: dict, why: str) -> dict:
    """Draft the RUN text for POST /port/crossing (v1: text only — Q1 lock). Frontier-model access is
    exactly this tool with the provider as `target`: gated, receipted, never silent."""
    if not target or not isinstance(instruction, dict) or not instruction:
        return _out("a crossing needs a non-empty target and instruction — refusing to draft an empty crossing")
    return _ok({
        "PROPOSE": f"Port crossing to {target!r} — {why}",
        "RUN": _curl("POST", "/port/crossing", {"target": target, "instruction": instruction}),
        "GATE": "raises a PENDING sanction in the Gate Inbox; sanction is owner-only. The operator drafts; "
                "KM sanctions. NOT executed. (Frontier model = this crossing, never a silent fallback.)",
    })


def usn_storage_propose(content_ref: str, why: str) -> dict:
    """Draft RUN text for POST /storage/datum — for KM's OWN datums only. The operator never stores its
    own notes here (Q2 lock: agent memory is wholly repo-side)."""
    return _ok({
        "PROPOSE": f"store a datum — {why}",
        "RUN": _curl("POST", "/storage/datum", {"content": content_ref, "visibility": "owner"}),
        "GATE": "KM's keyboard. The operator drafts this for KM's datums; it does not store its own notes "
                "in the USN (memory stays in ~/.sovereign_operator/). NOT executed.",
    })


def usn_refuse_peer_prepare(peer_id: str, why: str) -> dict:
    """Draft RUN text for POST /peers/refuse — surfacing the exit, never performing it (Q1 lock)."""
    return _ok({
        "PROPOSE": f"refuse peer {peer_id} — {why}",
        "RUN": _curl("POST", "/peers/refuse", {"other": peer_id}),
        "EXPECT": "honest outcome: residual_claim: null — hostage-free.",
        "GATE": "KM's keyboard. Surfaced, NOT executed.",
    })


def usn_clean_exit_prepare(why: str) -> dict:
    """Draft RUN text for POST /peers/clean_exit — exit is ≤2 clicks and ALWAYS available."""
    return _ok({
        "PROPOSE": f"clean exit — {why}",
        "RUN": _curl("POST", "/peers/clean_exit", {}),
        "EXPECT": "no_residual: true — exit is always available; the operator reminds, never performs.",
        "GATE": "KM's keyboard. Surfaced, NOT executed.",
    })


# The complete v1 tool set (read | draft). Used by CLI + tests to enumerate the surface.
READ_TOOLS = ("usn_status", "usn_list_pending_gates", "usn_receipts", "usn_peers", "usn_storage_read")
DRAFT_TOOLS = ("usn_capacity_propose", "usn_gate_prepare", "usn_propose_port_crossing",
               "usn_storage_propose", "usn_refuse_peer_prepare", "usn_clean_exit_prepare")


def health() -> dict:
    """Convenience: fold status into a compact health view; UsnUnreachable bubbles to the caller."""
    try:
        s = usn_status()
    except UsnUnreachable:
        raise
    return s
