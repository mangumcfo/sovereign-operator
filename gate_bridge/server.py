#!/usr/bin/env python3
"""Separate loopback Gate Bridge. Exactly one write route; no generic shell or USN client."""
from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sovereign_operator.gate_bridge import BridgeRefusal, BridgeStore, execute  # noqa: E402


def handler(*, owner: str, secret: bytes, store: BridgeStore, effects: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _reply(self, code: int, value: dict):
            body = json.dumps(value).encode()
            self.send_response(code); self.send_header("Content-Type", "application/json")
            self.end_headers(); self.wfile.write(body)

        def do_GET(self):
            self._reply(200, {"ok": True, "service": "gate-bridge", "write_route": "/v1/execute"})

        def do_POST(self):
            if self.path != "/v1/execute":
                return self._reply(404, {"ok": False, "refusal": "NO_SUCH_ROUTE"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(size))
                receipt = execute(body.get("envelope") or {}, body.get("authorization") or {},
                                  owner=owner, owner_secret=secret, store=store, effect_dir=effects)
                self._reply(200, {"ok": True, "receipt": receipt})
            except (BridgeRefusal, json.JSONDecodeError) as exc:
                self._reply(403, {"ok": False, "refusal": getattr(exc, "code", "BAD_JSON")})
    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8733)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--owner-secret-file", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("REFUSING: Gate Bridge is loopback-only")
    if args.owner_secret_file.stat().st_mode & 0o077:
        raise SystemExit("REFUSING: owner secret file must be mode 0600 or stricter")
    secret = args.owner_secret_file.read_bytes().strip()
    server = ThreadingHTTPServer((args.host, args.port), handler(
        owner=args.owner, secret=secret, store=BridgeStore(args.state / "bridge.sqlite3"),
        effects=args.state / "effects"))
    server.serve_forever()


if __name__ == "__main__":
    main()
