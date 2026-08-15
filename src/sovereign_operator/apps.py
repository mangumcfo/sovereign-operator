"""App registry — install / list / uninstall an operator APP as a PRIVATE instance.

The operator web console is a generic, shareable host. An "app" is a named instance a specific operator installs
into it — e.g. a personal business that tracks its own records under one mandate. The GENERIC mechanism lives in
this repo (public); an installed instance's data lives ENTIRELY under the operator's private home
(`config.HOME/apps/<name>/`, default `~/.sovereign_operator/apps/`) — NEVER inside this repo, never committed.

That separation is the point: the mechanism builds toward the public operator repo; the operator's personal
business stays private and is installable / uninstallable as an app, so it can be removed without a trace in the
console. This module holds NO node credential and performs NO node act — an app is local operator config
(a manifest + a private list of the record ids the operator tracks), not a disposition.
"""
from __future__ import annotations

import json
import re
import shutil
from typing import Optional

from . import config

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,38}$")   # a lowercase slug; no paths, no personal prose in the name


def _apps_root():
    root = config.HOME / "apps"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _app_dir(name: str):
    if not _NAME_RE.match(name or ""):
        raise ValueError(f"invalid app name {name!r} — use a lowercase slug [a-z0-9_-], no paths")
    return _apps_root() / name


def list_apps() -> list[dict]:
    """Installed apps (metadata only) from the PRIVATE home. Returns [] if none — a clean console."""
    out = []
    root = _apps_root()
    for d in sorted(root.iterdir() if root.exists() else []):
        mf = d / "manifest.json"
        if d.is_dir() and mf.exists():
            try:
                m = json.loads(mf.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 — a corrupt manifest is surfaced, never silently dropped
                m = {"name": d.name, "_error": "manifest unreadable"}
            m["records"] = _record_ids(d)
            out.append(m)
    return out


def get_app(name: str) -> Optional[dict]:
    d = _app_dir(name)
    mf = d / "manifest.json"
    if not mf.exists():
        return None
    m = json.loads(mf.read_text(encoding="utf-8"))
    m["records"] = _record_ids(d)
    return m


def install_app(name: str, *, mandate: str, node_url: str = "", at: str = "", label: str = "") -> dict:
    """Create a PRIVATE app instance under the operator home. Idempotent-safe: re-install updates the manifest,
    never wipes the tracked record ids. `at` is a caller-stated timestamp (this module reads no clock)."""
    if not mandate:
        raise ValueError("an app needs a mandate (the scope its records live under) — none given")
    d = _app_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": name,
        "label": label or name,
        "mandate": mandate,
        "node_url": node_url or config.USN_BASE,
        "installed_at": at,
        "note": ("PRIVATE operator app instance — lives under the operator home, NOT the public operator repo. "
                 "Uninstall removes it with no trace in the console."),
    }
    (d / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (d / "records.json").touch()
    return manifest


def uninstall_app(name: str) -> bool:
    """Remove a PRIVATE app instance entirely (manifest + its private record list). Returns True if it existed.
    Node-safe: touches only the operator's private home; disposes nothing on the node."""
    d = _app_dir(name)
    if not d.exists():
        return False
    shutil.rmtree(d)
    return True


def track_record(name: str, record_id: str, note: str = "") -> None:
    """Append a record id the operator wants the app to watch (its OWN private list). No node call."""
    d = _app_dir(name)
    if not (d / "manifest.json").exists():
        raise ValueError(f"app {name!r} is not installed")
    ids = _record_ids(d)
    if record_id not in {r["id"] for r in ids}:
        ids.append({"id": record_id, "note": note})
        (d / "records.json").write_text(json.dumps(ids, indent=2) + "\n", encoding="utf-8")


def _record_ids(app_dir) -> list[dict]:
    f = app_dir / "records.json"
    if not f.exists():
        return []
    txt = f.read_text(encoding="utf-8").strip()
    if not txt:
        return []
    try:
        data = json.loads(txt)
        return data if isinstance(data, list) else []
    except Exception:  # noqa: BLE001
        return []
