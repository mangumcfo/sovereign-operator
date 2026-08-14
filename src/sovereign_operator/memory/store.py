"""store.py — the notebook. The one thing the USN deliberately does not have: durable conversational
and working memory. It lives WHOLLY under ~/.sovereign_operator/ (Q2 lock) in a local SQLite file.
The operator has no route that writes the USN registry — this is the only place it remembers.

Stdlib only (sqlite3). No network. The kernel never sees this file.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .. import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  thread TEXT NOT NULL,
  ts TEXT NOT NULL,
  role TEXT NOT NULL,          -- 'km' | 'operator'
  content TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS proposals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  kind TEXT NOT NULL,          -- capacity | crossing | gate | exit | storage
  summary TEXT NOT NULL,
  run_text TEXT,
  disposed TEXT                -- NULL = promised-but-undisposed; else 'approved'/'denied'/'done'/note
);
CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  units_offered INTEGER,       -- from /status at snapshot time (facts → memory)
  grants INTEGER
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Notebook:
    def __init__(self, path=None):
        config.ensure_home()
        self.path = str(path or config.NOTEBOOK_DB)
        self._db = sqlite3.connect(self.path)
        self._db.executescript(_SCHEMA)
        self._db.commit()

    def close(self):
        self._db.close()

    # --- conversation memory ---
    def append(self, thread: str, role: str, content: str) -> None:
        self._db.execute("INSERT INTO messages(thread,ts,role,content) VALUES(?,?,?,?)",
                         (thread, _now(), role, content))
        self._db.commit()

    def thread(self, thread: str, limit: int = 50) -> list[dict]:
        cur = self._db.execute(
            "SELECT ts,role,content FROM messages WHERE thread=? ORDER BY id DESC LIMIT ?",
            (thread, limit))
        rows = [{"ts": t, "role": r, "content": c} for t, r, c in cur.fetchall()]
        return list(reversed(rows))

    def threads(self) -> list[str]:
        cur = self._db.execute("SELECT DISTINCT thread FROM messages ORDER BY thread")
        return [r[0] for r in cur.fetchall()]

    # --- proposal ledger (what we promised / what KM disposed) ---
    def record_proposal(self, kind: str, summary: str, run_text: str = "") -> int:
        cur = self._db.execute("INSERT INTO proposals(ts,kind,summary,run_text) VALUES(?,?,?,?)",
                              (_now(), kind, summary, run_text))
        self._db.commit()
        return cur.lastrowid

    def dispose_proposal(self, pid: int, disposition: str) -> None:
        self._db.execute("UPDATE proposals SET disposed=? WHERE id=?", (disposition, pid))
        self._db.commit()

    def open_proposals(self) -> list[dict]:
        cur = self._db.execute(
            "SELECT id,ts,kind,summary FROM proposals WHERE disposed IS NULL ORDER BY id")
        return [{"id": i, "ts": t, "kind": k, "summary": s} for i, t, k, s in cur.fetchall()]

    # --- units snapshot (for the morning Δ; a memory line, labeled as such) ---
    def snapshot_units(self, units_offered, grants) -> None:
        self._db.execute("INSERT INTO snapshots(ts,units_offered,grants) VALUES(?,?,?)",
                         (_now(), units_offered, grants))
        self._db.commit()

    def last_snapshot(self) -> dict | None:
        cur = self._db.execute(
            "SELECT ts,units_offered,grants FROM snapshots ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        return {"ts": row[0], "units_offered": row[1], "grants": row[2]} if row else None
