"""cli.py — `operator morning · operator chat · operator export`.

The operator reads the node (GET-only), remembers in its notebook, and drafts. It never executes: every
material suggestion arrives as PROPOSE + RUN + GATE text for KM's keyboard. Node down → it says so and
degrades to memory-only, labeled; it never fabricates facts.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone

from . import config, export as export_mod, lens, tools
from .http_client import UsnUnreachable, mind_complete, mind_up, pick_model
from .memory.store import Notebook

SYSTEM = (
    "You are the Sovereign Operator — a secretary with a notebook standing in front of a node that is the "
    "law. You READ node state and REMEMBER across sessions; you do NOT execute anything. For any "
    "consequential act (renew/revoke a grant, a Port crossing, disposing a gate, an exit) you emit:\n"
    "  PROPOSE: <intent>\n  RUN: <exact command KM pastes>\n  GATE: <the human act — KM's keyboard / Gate Inbox>\n"
    "Never claim to have done it. Label facts (from the node) vs memory (from your notebook) — never blend "
    "them in one unlabeled sentence. Be concise and income/ops-useful. No cloud; you have a loopback mind only."
)


def _now():
    return datetime.now(timezone.utc).isoformat()


# Carry (AA agent-v0 / delta-F, confirmed on the operator): a loopback mind may CLAIM it acted. It never
# did — this operator is read-and-draft only (U3 GREEN). When the model's prose claims an act, prefix one
# honest line so the claim can never be mistaken for a deed. This flags text; it changes no fence.
_CLAIM_RE = re.compile(
    r"\b(i(?:'ve| have)?\s+(?:approved|sanctioned|renewed|revoked|issued|executed|disposed|deleted|sent|done)"
    r"|already\s+(?:approved|sanctioned|renewed|revoked|done)|(?:^|\.\s*)done\b)", re.I)


def _claim_guard(ans: str) -> str:
    if ans and _CLAIM_RE.search(ans):
        return "⚠ the model CLAIMS an act; this operator executed nothing (read-and-draft only).\n" + ans
    return ans


def _facts_or_none(nb):
    """Return (facts, pending_count, stale_note). facts=None if the node is unreachable."""
    try:
        s = tools.usn_status()
    except UsnUnreachable as e:
        return None, None, f"node unreachable at {config.USN_BASE} ({type(e).__name__}) — facts unknown as of {_now()}"
    if not s.get("ok"):
        return None, None, f"status route unavailable ({s.get('out_reason')})"
    facts = s["data"] or {}
    pend = None
    try:
        pg = tools.usn_list_pending_gates()
        pend = pg["data"]["count"] if pg.get("ok") else None
    except UsnUnreachable:
        pend = None
    facts["_pending_gate_count"] = pend
    return facts, pend, None


def cmd_morning(_args) -> int:
    nb = Notebook()
    facts, pend, stale = _facts_or_none(nb)
    print("∞Δ∞ operator morning · read-only · the node is the law, this is the notebook\n")
    if facts is None:
        print(f"  node : UNREACHABLE — {stale}")
        print("\n" + lens.render(None, nb, stale_note=stale))
        nb.close()
        return 0
    gpu = facts.get("gpu", {})
    gpu_s = (f"{gpu.get('free_mib')}/{gpu.get('total_mib')} MiB free · {gpu.get('util_pct')}% util"
             if gpu.get("state") == "ok" else f"{gpu.get('note','?')} [{gpu.get('state')}]")
    print(f"  node   : fp {facts.get('node_fp','?')}")
    print(f"  gpu    : {gpu_s}")
    print(f"  peers  : {facts.get('peers',{}).get('count',0)} {facts.get('peers',{}).get('labels',[])}")
    print(f"  puller : {'running' if facts.get('puller_running') else 'stopped'} · "
          f"model {'up' if facts.get('model_up') else 'down'}")
    print(f"  gates  : {pend if pend is not None else '?'} pending")
    print("\n" + lens.render(facts, nb))
    # snapshot units for tomorrow's Δ (a memory write — the notebook, never the USN)
    nb.snapshot_units(facts.get("units_offered"), len(facts.get("grants", []) or []))
    nb.close()
    return 0


def _print_tool(result: dict) -> None:
    if not result.get("ok"):
        print(f"  (OUT) {result.get('out_reason')}")
        return
    import json as _j
    print(_j.dumps(result["data"], indent=2))


def cmd_chat(args) -> int:
    nb = Notebook()
    thread = args.thread or "default"
    model = config.MIND_MODEL or (pick_model() or "")
    print("∞Δ∞ operator chat · memory persists in ~/.sovereign_operator/ · type /help, /quit\n")
    while True:
        try:
            line = input("km> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line in ("/quit", "/exit", "/q"):
            break
        nb.append(thread, "km", line)
        if line == "/help":
            print("  /status  node facts · /propose  capacity renew/revoke (verbatim) · /gates  pending\n"
                  "  /morning  the LGP lens · /export  notebook→markdown · /quit\n"
                  "  anything else → the loopback mind drafts (PROPOSE/RUN/GATE); nothing is executed")
            continue
        if line == "/status":
            _print_tool(_safe(tools.usn_status)); continue
        if line == "/propose":
            r = _safe(tools.usn_capacity_propose); _print_tool(r)
            if r.get("ok"):
                for p in r["data"]["proposals"]:
                    nb.record_proposal("capacity", f"renew/revoke {p['peer']} (expires {p['expires']})", p.get("renew_run", ""))
            continue
        if line == "/gates":
            _print_tool(_safe(tools.usn_list_pending_gates)); continue
        if line == "/morning":
            cmd_morning(args); continue
        if line == "/export":
            print("  exported →", export_mod.export(nb)); continue

        # prose → the loopback mind, grounded in live facts + recent memory
        facts, pend, stale = _facts_or_none(nb)
        ctx = _context(facts, stale, nb, thread)
        if not model or not mind_up():
            ans = ("(no loopback model up — facts + proposals only, no prose)\n"
                   + _facts_digest(facts, stale) + "\n"
                   "PROPOSE: use /propose for the node's exact renew/revoke commands · /gates for pending. "
                   "Nothing executed.")
        else:
            try:
                ans = mind_complete(f"{ctx}\n\nKM: {line}", system=SYSTEM, model=model)
            except UsnUnreachable:
                ans = "(node unreachable — memory-only)"
            except Exception as e:  # noqa: BLE001
                ans = f"(mind error: {type(e).__name__}) — {_facts_digest(facts, stale)}"
            ans = _claim_guard(ans)   # flag a lying mind's claim; the operator executed nothing
        print("operator>", ans)
        nb.append(thread, "operator", ans)
    nb.close()
    return 0


def _safe(fn):
    try:
        return fn()
    except UsnUnreachable as e:
        return {"ok": False, "out_reason": f"node unreachable ({type(e).__name__}) — facts stale, not fabricated"}


def _facts_digest(facts, stale) -> str:
    if facts is None:
        return f"facts: UNREACHABLE — {stale} (memory only; not fabricated)"
    g = facts.get("gpu", {})
    return (f"facts: puller={facts.get('puller_running')} model_up={facts.get('model_up')} "
            f"grants={len(facts.get('grants',[]) or [])} units={facts.get('units_offered')} "
            f"gpu={g.get('state')}")


def _context(facts, stale, nb, thread) -> str:
    recent = nb.thread(thread, limit=8)
    mem = "\n".join(f"  [{m['role']}] {m['content'][:200]}" for m in recent[:-1]) or "  (no prior turns)"
    return (f"NODE FACTS (label these 'facts'):\n  {_facts_digest(facts, stale)}\n"
            f"NOTEBOOK (label these 'memory'):\n{mem}")


def cmd_export(args) -> int:
    nb = Notebook()
    path = export_mod.export(nb, thread=args.thread)
    print("exported →", path)
    nb.close()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="operator", description="Sovereign Operator — read-and-draft secretary for your USN")
    sub = p.add_subparsers(dest="cmd")
    m = sub.add_parser("morning", help="one-screen status + LGP lens (facts vs memory labeled)")
    m.set_defaults(fn=cmd_morning)
    c = sub.add_parser("chat", help="conversational; memory persists across sessions")
    c.add_argument("--thread", default="default")
    c.set_defaults(fn=cmd_chat)
    e = sub.add_parser("export", help="notebook → human-readable markdown")
    e.add_argument("--thread", default=None)
    e.set_defaults(fn=cmd_export)
    args = p.parse_args(argv)
    if not getattr(args, "fn", None):
        p.print_help()
        return 0
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
