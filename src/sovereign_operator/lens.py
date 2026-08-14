"""lens.py — the morning LGP lens (spec F3). One short block; every line labeled by SOURCE.

Law folded in (F3): a line derived from the notebook is labeled `memory`; a line from /api/v1/status
is labeled `facts`; the two never blend in one unlabeled sentence. The lens INITIATES the morning
ritual; it asserts nothing the node did not say. `days-to-expiry` is arithmetic on a fact, still a fact.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _as_int(x):
    """Coerce to int, or None. The node's status doc may deliver units_offered as a string (registry
    payload) — never subtract raw across types; a non-numeric value degrades to 'no delta', not a crash."""
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def days_to_expiry(expires_iso: str | None):
    """Whole days from now (UTC) until an ISO expiry. None if unparseable. Arithmetic on a fact."""
    if not expires_iso:
        return None
    try:
        exp = datetime.fromisoformat(expires_iso.replace("Z", "+00:00"))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (exp - datetime.now(timezone.utc)).days


def grant_lines(facts: dict) -> list[str]:
    """One 'facts:' line per grant with days-to-expiry (the Beard-grant flag the success bar names)."""
    out = []
    for g in facts.get("grants", []) or []:
        d = days_to_expiry(g.get("expires"))
        left = f"{d} days left" if d is not None else "expiry unparseable"
        flag = "  ⚠ EXPIRING" if (d is not None and d <= 3) else ""
        out.append(f"  income   : {g.get('peer','?')} grant — {left} (facts){flag}")
    if not out:
        out.append("  income   : no active grants (facts)")
    return out


def render(facts: dict | None, notebook, *, stale_note: str | None = None) -> str:
    """Build the LGP block. `facts` None → node unreachable; say so, use memory only, never fabricate."""
    lines = ["LGP today  (facts: /api/v1/status · memory: notebook — notebook ≠ law)"]

    if facts is None:
        lines.append(f"  ⚠ node unreachable — {stale_note or 'facts stale/unknown'}; the lines below are MEMORY only")
        snap = notebook.last_snapshot()
        if snap:
            lines.append(f"  income   : last known units_offered={snap['units_offered']} at {snap['ts']} (memory)")
        openp = notebook.open_proposals()
        lines.append(f"  attention: promised-but-undisposed proposals: {len(openp)} (memory)")
        lines.append("  one move : start the node, then re-run `operator morning` for live facts (PROPOSAL)")
        return "\n".join(lines)

    # income — grants + days-to-expiry (facts), plus Δ units vs last snapshot (facts vs memory, labeled)
    lines += grant_lines(facts)
    snap = notebook.last_snapshot()
    now_units = facts.get("units_offered")
    ni = _as_int(now_units)
    si = _as_int(snap.get("units_offered")) if snap else None
    if ni is not None and si is not None:
        delta = ni - si
        lines.append(f"           units_offered now {ni} (facts) · Δ {delta:+d} since {snap['ts']} (facts vs notebook snapshot)")
    else:
        lines.append(f"           units_offered now {now_units} (facts) · no comparable prior snapshot (memory)")

    # attention — pending gates (facts) vs promised-but-undisposed (memory)
    pend = facts.get("_pending_gate_count")
    openp = notebook.open_proposals()
    pg = f"{pend}" if pend is not None else "?"
    lines.append(f"  attention: pending gates: {pg} (facts) · promised-but-undisposed proposals: {len(openp)} (memory)")

    # one move — a single drafted suggestion, marked PROPOSAL
    lines.append("  one move : " + _one_move(facts, openp))
    return "\n".join(lines)


def _one_move(facts: dict, open_proposals: list) -> str:
    # priority: an expiring grant → renew; else a pending gate → dispose; else quiet
    for g in facts.get("grants", []) or []:
        d = days_to_expiry(g.get("expires"))
        if d is not None and d <= 3:
            return f"renew {g.get('peer','?')} grant ({d} days left) — `operator chat` then /propose (PROPOSAL, not executed)"
    if facts.get("_pending_gate_count"):
        return "dispose the pending gate(s) at the console Gate Inbox (PROPOSAL — owner acts, not the operator)"
    if open_proposals:
        return f"close out {len(open_proposals)} promised proposal(s) from the notebook (PROPOSAL)"
    return "nothing pressing — the node is clear (PROPOSAL: none)"
