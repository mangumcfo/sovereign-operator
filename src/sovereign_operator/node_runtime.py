"""Read-only observation of the local ERP node ceremony state."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from . import config
from .port_client import _loopback_or_die


class NodeRuntimeUnreachable(Exception):
    """The local ERP runtime did not provide authoritative open-state evidence."""


def _get(path: str) -> dict:
    url = _loopback_or_die(config.ERP_BASE + path)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"),
                                    timeout=config.USN_TIMEOUT) as response:  # noqa: S310
            body = json.loads(response.read().decode())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise NodeRuntimeUnreachable(str(exc)) from exc
    if not isinstance(body, dict):
        raise NodeRuntimeUnreachable(f"{path} returned no usable state")
    return body


def node_runtime() -> dict:
    """Combine surface-owned OPEN and identity facts; return no key or secret material."""
    vocab = _get("/api/vocab")
    status = _get("/api/status")
    identity = status.get("identity") or {}
    return {
        "ok": True,
        "open": vocab.get("open") is True,
        "expected_fp_configured": vocab.get("expected_fp_configured") is True,
        "fingerprint": identity.get("fingerprint") if identity.get("present") is True else None,
    }
