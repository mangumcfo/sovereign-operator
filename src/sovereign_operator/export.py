"""export.py — spec F1. Human-readable markdown export of the notebook: threads, proposals made and
disposed. Plain files KM owns under ~/.sovereign_operator/exports/ — no format lock-in, readable with
`less`. (Optional-later, flag only: offer the file as RUN text for POST /storage/datum on KM's
keyboard — a Merkle-bound snapshot. NOT built in v1; the agent would only draft that command.)
"""
from __future__ import annotations

import re
from datetime import datetime, timezone


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "notebook"


def export(notebook, *, thread: str | None = None, out_dir=None) -> str:
    """Write a markdown export; return the file path. thread=None → all threads + the proposal ledger."""
    from . import config
    out_dir = out_dir or config.EXPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = _slug(thread) if thread else "all"
    path = out_dir / f"{stamp}_{slug}.md"

    lines = [f"# Operator notebook export — {slug}",
             f"_generated {datetime.now(timezone.utc).isoformat()} · memory only, not law (facts live in the node)_", ""]

    threads = [thread] if thread else notebook.threads()
    for th in threads:
        msgs = notebook.thread(th, limit=10_000)
        if not msgs:
            continue
        lines.append(f"## Thread: {th}\n")
        for m in msgs:
            who = "KM" if m["role"] == "km" else "operator"
            lines.append(f"- **{who}** · {m['ts']}\n\n  {m['content'].strip()}\n")

    lines.append("## Proposals (made · disposed)\n")
    openp = notebook.open_proposals()
    if openp:
        lines.append("_open (promised, not yet disposed):_\n")
        lines += [f"- [{p['kind']}] {p['summary']} · {p['ts']}" for p in openp]
        lines.append("")
    lines.append("_full ledger is in the notebook db; this export lists open items above._")

    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
