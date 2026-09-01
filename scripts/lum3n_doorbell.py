#!/usr/bin/env python3
"""Poll Issue #1 for exact LUM3N DOORBELL comments and queue them to the Codex thread.

Transport only: this script neither interprets nor executes a steer. It records a high-water mark,
queues each new bell once, and fails loudly to its systemd journal when GitHub or Codex is unavailable.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

REPO = os.environ.get("LUM3N_GITHUB_REPO", "mangumcfo/sovereign-operator")
ISSUE = os.environ.get("LUM3N_GITHUB_ISSUE", "1")
THREAD = os.environ.get("LUM3N_THREAD_ID", "").strip()
STATE = Path(os.environ.get(
    "LUM3N_DOORBELL_STATE",
    str(Path.home() / ".sovereign_operator" / "lum3n-doorbell.json"),
))


def _run(args: list[str]) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=True)
    return result.stdout


def _comments() -> list[dict]:
    raw = _run(["gh", "issue", "view", ISSUE, "--repo", REPO, "--json", "comments"])
    return (json.loads(raw).get("comments") or [])


def _load_seen() -> set[str]:
    if not STATE.is_file():
        return set()
    try:
        return set(json.loads(STATE.read_text()).get("seen") or [])
    except (OSError, json.JSONDecodeError):
        return set()


def _save_seen(seen: set[str]) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.parent.chmod(0o700)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps({"seen": sorted(seen)}, indent=2) + "\n")
    tmp.replace(STATE)


def _is_bell(comment: dict) -> bool:
    body = str(comment.get("body") or "")
    return bool(body.splitlines()) and body.splitlines()[0].strip() == "LUM3N DOORBELL"


def tick(*, prime: bool = False, dry_run: bool = False) -> dict:
    comments = _comments()
    bells = [comment for comment in comments if _is_bell(comment)]
    seen = _load_seen()
    new = [comment for comment in bells if str(comment.get("id")) not in seen]
    if prime:
        seen.update(str(comment.get("id")) for comment in bells)
        _save_seen(seen)
        return {"ok": True, "primed": len(bells), "queued": 0}
    if new and not THREAD:
        raise RuntimeError("LUM3N_THREAD_ID is required when a new bell is waiting")
    queued = []
    for comment in new:
        cid = str(comment.get("id"))
        message = (
            "LUM3N DOORBELL — consume before new implementation. Read the linked PR and newest Issue #1 context; "
            "acknowledge the exact delta. This queues work but grants no additional authority.\n\n"
            + str(comment.get("body") or "")
            + f"\n\nSource: {comment.get('url') or 'Issue #1'}"
        )
        if not dry_run:
            _run(["codex", "queue", "--thread", THREAD, "--message", message])
            seen.add(cid)
            _save_seen(seen)
        queued.append(cid)
    return {"ok": True, "bells": len(bells), "new": len(new), "queued": len(queued),
            "dry_run": dry_run}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prime", action="store_true", help="mark existing bells seen without queueing")
    parser.add_argument("--dry-run", action="store_true", help="report new bells without queueing")
    args = parser.parse_args()
    print(json.dumps(tick(prime=args.prime, dry_run=args.dry_run)))


if __name__ == "__main__":
    main()
