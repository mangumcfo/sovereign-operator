"""Read-only client for the local Port fleet membrane.

Port is a state/obligations feed into the human-day surface. It is not the household node and this
client deliberately has one operation: loopback GET. No Port write or generic request primitive is
exposed here.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from . import config


class PortUnreachable(Exception):
    """The local Port feed did not answer; callers must label the feed unavailable."""


def _loopback_or_die(url: str) -> str:
    host = re.sub(r"^https?://", "", url).split("/")[0].rsplit(":", 1)[0]
    if host not in config.LOOPBACK_HOSTS:
        raise ValueError(f"Port feed is loopback-only (got host {host!r})")
    return url


def port_state() -> dict:
    """GET the Port's machine-readable state projection. No caching and no fallback facts."""
    url = _loopback_or_die(config.PORT_BASE + "/api/state")
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=config.USN_TIMEOUT) as response:  # noqa: S310
            body = json.loads(response.read().decode())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise PortUnreachable(str(exc)) from exc
    if not isinstance(body, dict) or not body.get("ok"):
        raise PortUnreachable("Port /api/state returned no usable state")
    return body
