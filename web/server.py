#!/usr/bin/env python3
"""server.py — the Operator Web Surface: a loopback browser UI over the EXISTING operator + corpus
read/draft surfaces. The zero-terminal daily path — NOT a new product, NOT a node capability.

LAW (same fences as the operator CLI, now behind a browser):
- **Read/draft only toward the node.** This server talks to the USN ONLY through the operator's
  GET-only client (`sovereign_operator.tools`), so the node's access log shows GETs and nothing else
  from the web surface. It has NO path that POSTs a USN route. Consequential acts (renew/revoke, gate
  disposition, Port crossing, storage) are returned as RUN/PROPOSE/GATE **text** for KM's keyboard /
  the console — never executed here.
- **Loopback only.** Binds 127.0.0.1; refuses to serve off loopback. The mind is the local model
  (loopback); frontier is only ever a *drafted, labeled Port crossing* KM sanctions — never a fallback.
- **Compose, don't re-implement.** Corpus search rides `corpus.retrieval` (cite-or-refuse); the shelf
  is not re-implemented. Stdlib only; zero third-party deps.

The browser POSTs to THIS server (chat prose, draft requests) — those are browser→web-server, never
web-server→USN. The USN stays GET-only from the operator's perspective.
"""
from __future__ import annotations

import http.server
import json
import os
import socketserver
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # sovereign-operator repo root
sys.path.insert(0, str(ROOT / "src"))                  # sovereign_operator package
sys.path.insert(0, str(ROOT))                          # corpus package

from sovereign_operator import config, lens, tools, apps  # noqa: E402
from sovereign_operator.cli import SYSTEM, _claim_guard  # noqa: E402
from sovereign_operator.http_client import UsnUnreachable, mind_complete, mind_up, pick_model  # noqa: E402

PUBLIC = Path(__file__).resolve().parent / "public"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}

_CORPUS = None


def corpus():
    global _CORPUS
    if _CORPUS is None:
        from corpus.retrieval import Corpus
        _CORPUS = Corpus()
    return _CORPUS


def _facts_or_stale():
    try:
        s = tools.usn_status()
    except UsnUnreachable as e:
        return None, f"node unreachable at {config.USN_BASE} ({type(e).__name__}) — facts unknown"
    if not s.get("ok"):
        return None, f"status route unavailable ({s.get('out_reason')})"
    return s["data"], None


# ── endpoint handlers (all return a JSON-able dict) ────────────────────────────────────────────────
def ep_morning(_q):
    facts, stale = _facts_or_stale()
    if facts is None:
        return {"ok": False, "node": "unreachable", "stale": stale,
                "lens": lens.render(None, _Nb(), stale_note=stale)}
    pend = None
    try:
        pg = tools.usn_list_pending_gates()
        pend = pg["data"]["count"] if pg.get("ok") else None
    except UsnUnreachable:
        pend = None
    facts["_pending_gate_count"] = pend
    cap = _safe(tools.usn_capacity_propose)
    return {"ok": True, "facts": facts, "pending_gates": pend,
            "lens": lens.render(facts, _Nb()), "capacity": cap.get("data", {}),
            "model_up": mind_up()}


def ep_status(_q):
    return _safe(tools.usn_status)


def ep_gates(_q):
    r = _safe(tools.usn_list_pending_gates)
    if not r.get("ok"):
        return r
    items = r["data"].get("pending", [])
    out = []
    for it in items:
        gid = it.get("req_id") or it.get("id")
        prep = _safe(lambda gid=gid: tools.usn_gate_prepare(gid))
        out.append({"gate": it, "dispose": prep.get("data", {})})  # RUN_approve / RUN_deny — text only
    return {"ok": True, "count": len(out), "gates": out,
            "note": "Disposition is a human act (owner-only). Copy the RUN line to your keyboard or use "
                    "the console Gate Inbox. This surface never approves/denies."}


def ep_capacity(_q):
    return _safe(tools.usn_capacity_propose)


def ep_receipts(_q):
    inf = _safe(lambda: tools.usn_receipts("inference", 25))
    aud = _safe(lambda: tools.usn_receipts("audit", 25))
    return {"ok": True, "inference": inf.get("data"), "audit": aud.get("data")}


def ep_storage_read(q):
    """Read an owner-scoped datum by id (GET /storage/datum/<id>) — drill 3 verification."""
    did = (q.get("id") or [""])[0].strip()
    if not did:
        return {"ok": False, "out_reason": "datum id required"}
    return _safe(lambda: tools.usn_storage_read(did))


def ep_corpus(q):
    query = (q.get("q") or [""])[0].strip()
    if not query:
        return {"ok": False, "refuse": "empty query"}
    try:
        return corpus().corpus_search(query, k=6)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "out_reason": f"corpus index not available ({type(e).__name__})"}


def ep_chat(body):
    prompt = str(body.get("prompt", "")).strip()
    if not prompt:
        return {"ok": False, "error": "prompt required"}
    facts, stale = _facts_or_stale()
    fdigest = ("node unreachable — " + (stale or "")) if facts is None else (
        f"puller={facts.get('puller_running')} model_up={facts.get('model_up')} "
        f"grants={len(facts.get('grants', []) or [])} units={facts.get('units_offered')}")
    cap = _safe(tools.usn_capacity_propose).get("data", {}) if facts is not None else {}
    model = config.MIND_MODEL or (pick_model() or "")
    if not model or not mind_up():
        return {"ok": True, "answer": "(no loopback model up — facts + proposals only, no prose)",
                "facts_digest": fdigest, "proposals": cap, "model": None}
    try:
        ans = _claim_guard(mind_complete(f"NODE FACTS: {fdigest}\n\nKM: {prompt}", system=SYSTEM, model=model))
    except UsnUnreachable:
        ans = "(node unreachable — memory-only)"
    except Exception as e:  # noqa: BLE001
        ans = f"(mind error: {type(e).__name__})"
    return {"ok": True, "answer": ans, "facts_digest": fdigest, "proposals": cap, "model": model}


def ep_draft_crossing(body):
    return _safe(lambda: tools.usn_propose_port_crossing(
        str(body.get("target", "")), body.get("instruction") or {}, str(body.get("why", ""))))


def ep_draft_storage(body):
    return _safe(lambda: tools.usn_storage_propose(str(body.get("content_ref", "")), str(body.get("why", ""))))


def ep_draft_verify(body):
    """Draft the RUN text for POST /storage/datum/<id>/verify (drill 3 integrity check) — text only,
    no node call. KM runs it on the keyboard; it confirms the stored hash matches the source."""
    did = str(body.get("datum_id", "")).strip()
    content = str(body.get("content", ""))
    if not did or not content:
        return {"ok": False, "out_reason": "datum_id and content required"}
    return {"ok": True, "data": {
        "PROPOSE": f"verify datum {did} against its source content",
        "RUN": tools._curl("POST", f"/storage/datum/{did}/verify", {"content": content}),
        "GATE": "read-check — run on your keyboard. Confirms the stored datum's hash matches the source. "
                "The web surface never posts this; it drafts it."}}


def ep_apps(_q):
    """List installed operator apps (metadata only) from the PRIVATE operator home. No node call. Apps are
    never in this repo — install/uninstall is local operator config, not a node disposition."""
    try:
        return {"ok": True, "apps": apps.list_apps(),
                "note": "Apps are PRIVATE instances under the operator home (~/.sovereign_operator/apps), never "
                        "in this repo. Install/uninstall is local config; it disposes nothing on the node."}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def ep_records(q):
    """Records index for an app — THREE-STATE, live-verified against the node at render (X4):
    `live` (node holds the datum) · `unverified` (node unreachable — could not check, never fabricated) ·
    `MISSING` (node answered, datum absent). App-side only: the tracked ids live in the PRIVATE app home;
    this adds NO node route — it only GETs `/storage/datum/<id>`."""
    name = (q.get("app") or [""])[0].strip()
    app = apps.get_app(name) if name else None
    if not app:
        return {"ok": False, "out_reason": f"no installed app {name!r}"}
    facts, _stale = _facts_or_stale()
    node_up = facts is not None
    rows = []
    for rec in app.get("records", []):
        rid = rec.get("id")
        if not node_up:
            rows.append({"id": rid, "note": rec.get("note", ""), "state": "unverified",
                         "detail": "node unreachable — cannot verify (not fabricated)"})
            continue
        r = _safe(lambda rid=rid: tools.usn_storage_read(rid))
        if r.get("ok"):
            d = r.get("data", {})
            rows.append({"id": rid, "note": rec.get("note", ""), "state": "live",
                         "root": d.get("root"), "mandate": d.get("mandate")})
        else:
            rows.append({"id": rid, "note": rec.get("note", ""), "state": "MISSING",
                         "detail": r.get("out_reason", "the node has no such datum")})
    return {"ok": True, "app": app.get("name"), "mandate": app.get("mandate"), "node_up": node_up, "records": rows,
            "counts": {"live": sum(x["state"] == "live" for x in rows),
                       "MISSING": sum(x["state"] == "MISSING" for x in rows),
                       "unverified": sum(x["state"] == "unverified" for x in rows)}}


def ep_app_install(body):
    """Install a PRIVATE app instance (local operator config; NO node call, NOT a disposition)."""
    name, mandate = str(body.get("name", "")).strip(), str(body.get("mandate", "")).strip()
    if not name or not mandate:
        return {"ok": False, "out_reason": "name and mandate required"}
    try:
        m = apps.install_app(name, mandate=mandate, label=str(body.get("label", "")), at=str(body.get("at", "")))
        return {"ok": True, "installed": m,
                "note": "PRIVATE local app instance under the operator home — not the repo. No node act."}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "out_reason": f"{type(e).__name__}: {e}"}


def ep_app_uninstall(body):
    """Uninstall a PRIVATE app instance — removes its manifest + private record list. NO node call: nothing on
    the node changes; only the operator's local console forgets the app."""
    name = str(body.get("name", "")).strip()
    try:
        existed = apps.uninstall_app(name)
        return {"ok": True, "uninstalled": existed, "name": name,
                "note": "Removed the PRIVATE app instance. No node act; the node's records are untouched."}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "out_reason": f"{type(e).__name__}: {e}"}


def ep_app_track(body):
    """Track a record id under an app (append to its PRIVATE record list; NO node call)."""
    name, rid = str(body.get("name", "")).strip(), str(body.get("id", "")).strip()
    if not name or not rid:
        return {"ok": False, "out_reason": "app name and record id required"}
    try:
        apps.track_record(name, rid, str(body.get("note", "")))
        return {"ok": True, "tracked": rid, "app": name, "note": "Added to the app's PRIVATE record list. No node act."}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "out_reason": f"{type(e).__name__}: {e}"}


def _safe(fn):
    try:
        return fn()
    except UsnUnreachable as e:
        return {"ok": False, "node": "unreachable", "out_reason": f"{type(e).__name__} — facts stale, not fabricated"}


class _Nb:
    """Minimal notebook stand-in for the lens (web surface keeps no cross-session memory of its own;
    the operator CLI notebook is the memory plane). Provides the two methods lens.render calls."""
    def last_snapshot(self):
        return None

    def open_proposals(self):
        return []


GET_ROUTES = {"/api/morning": ep_morning, "/api/status": ep_status, "/api/gates": ep_gates,
              "/api/capacity": ep_capacity, "/api/receipts": ep_receipts, "/api/corpus": ep_corpus,
              "/api/storage": ep_storage_read, "/api/apps": ep_apps, "/api/records": ep_records}
POST_ROUTES = {"/api/chat": ep_chat, "/api/draft/crossing": ep_draft_crossing,
               "/api/draft/storage": ep_draft_storage, "/api/draft/verify": ep_draft_verify,
               # local app management — operator config only, NO node call (not a disposition)
               "/api/apps/install": ep_app_install, "/api/apps/uninstall": ep_app_uninstall,
               "/api/apps/track": ep_app_track}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ("/", "/index.html"):
            html = (PUBLIC / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html)
            return
        fn = GET_ROUTES.get(path)
        if not fn:
            return self._json({"error": "no such route"}, 404)
        try:
            self._json(fn(urllib.parse.parse_qs(parsed.query)))
        except Exception as e:  # noqa: BLE001
            self._json({"ok": False, "error": f"{type(e).__name__}: {e}"}, 500)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        fn = POST_ROUTES.get(path)
        if not fn:
            return self._json({"error": "no such route"}, 404)
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "bad json"}, 400)
        try:
            self._json(fn(body))
        except Exception as e:  # noqa: BLE001
            self._json({"ok": False, "error": f"{type(e).__name__}: {e}"}, 500)


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="operator-web", description="Operator Web Surface (loopback, read/draft only)")
    p.add_argument("--host", default=os.environ.get("OPERATOR_WEB_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("OPERATOR_WEB_PORT", "8722")))
    a = p.parse_args(argv)
    if a.host not in LOOPBACK:
        sys.stderr.write(f"REFUSING: web surface is loopback-only (got host {a.host!r}). "
                         "It reads the node and drafts; it is not a public service.\n")
        raise SystemExit(2)
    print("∞Δ∞ Operator Web Surface — read/draft only · loopback")
    print(f"     open:  http://{a.host}:{a.port}/")
    print(f"     node:  {config.USN_BASE}  (GET-only from here)")
    print("     acts:  copy-to-keyboard RUN text; nothing is executed against the node here")
    with socketserver.ThreadingTCPServer((a.host, a.port), Handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
