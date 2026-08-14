"""config.py — where the operator points and where it remembers. All loopback by default.

No secrets here and none read from the tree: the operator holds no keys. The USN base and the model
URL are loopback by construction; a non-loopback value is refused at the HTTP layer (see http_client).
The memory directory is the operator's own notebook home — NEVER the USN registry (Q2 lock).
"""
from __future__ import annotations

import os
import pathlib

# --- where the law lives (read-only, GET-only from here) ------------------------------------------
USN_BASE = os.environ.get("OPERATOR_USN_URL", "http://127.0.0.1:8421/api/v1").rstrip("/")

# --- the operator's own mind (loopback model; same fence the USN chat uses) ------------------------
MIND_URL = os.environ.get("OPERATOR_MIND_URL", "http://127.0.0.1:11434/v1/chat/completions")
MIND_MODEL = os.environ.get("OPERATOR_MIND_MODEL", "").strip()  # empty = ask the node/model to pick

# --- the notebook: the operator's memory, wholly repo/operator-side (Q2 lock) ----------------------
# Override with OPERATOR_HOME; default ~/.sovereign_operator/. NEVER inside the USN tree or registry.
HOME = pathlib.Path(os.environ.get("OPERATOR_HOME", os.path.expanduser("~/.sovereign_operator")))
NOTEBOOK_DB = HOME / "notebook.sqlite3"
EXPORT_DIR = HOME / "exports"

# --- F5 · multi-principal seam (reserved; v1 is exactly one principal) ------------------------------
PRINCIPAL = os.environ.get("OPERATOR_PRINCIPAL", "operator").strip() or "operator"

# --- HTTP timeouts (loopback → short) --------------------------------------------------------------
USN_TIMEOUT = float(os.environ.get("OPERATOR_USN_TIMEOUT", "6"))
MIND_TIMEOUT = float(os.environ.get("OPERATOR_MIND_TIMEOUT", "180"))

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "[::1]"}


def ensure_home() -> None:
    """Create the operator's notebook home (0700) if absent. Never touches the USN tree."""
    HOME.mkdir(parents=True, exist_ok=True)
    try:
        HOME.chmod(0o700)
    except OSError:
        pass
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
