"""http_client.py — the ONLY wire in the operator. Pure stdlib. Two callers, two fences.

1. `usn_get(path)` — the ONLY function that talks to the USN node. It is **GET-only**: there is no
   usn_post anywhere in this repo, by design (Q1 lock, verify row U2). Every consequential USN act is
   returned to KM as RUN text by the tool layer; no tool ever POSTs a USN route. The USN's access log
   therefore shows GETs and nothing else from the operator.
2. `mind_complete(...)` — the operator's own loopback model (Ollama/vLLM). This is NOT the USN; it is
   the secretary's mind. It POSTs to the MODEL url only, and only after the loopback fence. Frontier
   models are never a fallback here — reaching one is a drafted Port crossing KM sanctions (tools).

Both are loopback-fenced: a non-loopback host is refused, not tried (verify row U1). No third-party
package is imported; no telemetry endpoint exists (F4).
"""
from __future__ import annotations

import json
import pathlib
import re
import stat
import urllib.error
import urllib.request

from . import config


class UsnUnreachable(Exception):
    """The node API did not answer. Callers degrade to memory-only and SAY the facts are stale."""


def _loopback_or_die(url: str) -> str:
    host = re.sub(r"^https?://", "", url).split("/")[0].rsplit(":", 1)[0]
    if host not in config.LOOPBACK_HOSTS:
        raise ValueError(f"operator is loopback-only (got host {host!r}) — no cloud, no remote node")
    return url


def usn_get(path: str) -> tuple[int, object | None]:
    """GET a USN route. Returns (status_code, parsed_json_or_None). GET-only by construction.

    Connection refused / timeout → UsnUnreachable (node down; caller labels facts stale). A 4xx/5xx
    returns (status, body) so the tool layer can map 404 → deny-by-default 'OUT'.
    """
    url = _loopback_or_die(config.USN_BASE + path)
    headers = {}
    token_file = pathlib.Path(config.USN_TOKEN_FILE)
    if token_file.is_file():
        mode = stat.S_IMODE(token_file.stat().st_mode)
        if mode & 0o077:
            raise ValueError(f"refusing broad-permission node credential ({mode:04o}); require 0600")
        token = token_file.read_text().strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")  # GET-only, authenticated if configured
    try:
        with urllib.request.urlopen(req, timeout=config.USN_TIMEOUT) as r:  # noqa: S310 (loopback-fenced)
            body = r.read().decode()
            try:
                return r.status, json.loads(body)
            except json.JSONDecodeError:
                return r.status, None
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:  # noqa: BLE001
            return e.code, None
    except (urllib.error.URLError, OSError) as e:  # connection refused / DNS / timeout
        raise UsnUnreachable(str(e)) from e


def mind_complete(prompt: str, *, system: str, model: str) -> str:
    """Loopback model completion (OpenAI-compatible, Ollama-native fallback). Not the USN.

    This is the operator's OWN mind. It never falls back to a cloud model — reaching a frontier model
    is a drafted Port crossing (tools.usn_propose_port_crossing), gated on KM's keyboard, never here.
    """
    url = _loopback_or_die(config.MIND_URL)
    if "/v1/" in url or url.endswith("/chat/completions"):
        payload = {"model": model, "messages": [{"role": "system", "content": system},
                                                 {"role": "user", "content": prompt}], "stream": False}
        req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=config.MIND_TIMEOUT) as r:  # noqa: S310 (loopback-fenced)
            data = json.loads(r.read().decode())
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "") or ""
    # Ollama-native /api/generate fallback
    payload = {"model": model, "prompt": f"{system}\n\n{prompt}", "stream": False}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=config.MIND_TIMEOUT) as r:  # noqa: S310
        return json.loads(r.read().decode()).get("response", "")


def pick_model() -> str | None:
    """Largest installed local tag (loopback Ollama /api/tags). Never a cloud model. None if none."""
    base = re.sub(r"(/v1/.*|/api/.*)$", "", config.MIND_URL)
    try:
        with urllib.request.urlopen(_loopback_or_die(base + "/api/tags"), timeout=5) as r:  # noqa: S310
            data = json.loads(r.read().decode())
    except Exception:  # noqa: BLE001
        return None
    best, best_pb = None, -1.0
    for m in data.get("models", []):
        name = m.get("name")
        if not name:
            continue
        pm = re.search(r"([\d.]+)\s*B", (m.get("details") or {}).get("parameter_size", ""), re.I)
        pb = float(pm.group(1)) if pm else 0.0
        if pb > best_pb:
            best, best_pb = name, pb
    return best


def mind_up() -> bool:
    """Is the loopback model server answering? (liveness, not identity)."""
    base = re.sub(r"(/v1/.*|/api/.*)$", "", config.MIND_URL)
    for p in ("/api/tags", "/v1/models"):
        try:
            urllib.request.urlopen(_loopback_or_die(base + p), timeout=3)  # noqa: S310
            return True
        except Exception:  # noqa: BLE001
            continue
    return False
