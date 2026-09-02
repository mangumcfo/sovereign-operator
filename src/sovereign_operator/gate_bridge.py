"""Sovereign Effect Envelope bridge core for narrowly allowlisted local effects.

This module is intentionally independent of ``web/server.py``. It exposes no shell, URL, module,
or callable supplied by a request. v0.1 has one reversible synthetic handler for proving the gate.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

HANDLER = "synthetic.marker.v1"
HANDLER_SPEC = b"write payload.message to an operator-owned synthetic marker; read it back exactly"
POLICY = b"synthetic=true;money=false;human-owner-signature;single-use;expires"


class BridgeRefusal(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def live_handler_bytes() -> bytes:
    return Path(__file__).read_bytes()


def one_shot_hash(envelope: dict, *, handler_bytes: bytes | None = None,
                  spec: bytes = HANDLER_SPEC, policy: bytes = POLICY) -> str:
    frozen = {
        "execution_id": envelope["execution_id"], "nonce": envelope["nonce"],
        "expires_at": envelope["expires_at"], "handler": envelope["handler"],
        "payload": envelope["payload"],
        "handler_digest": digest(handler_bytes if handler_bytes is not None else live_handler_bytes()),
        "spec_digest": digest(spec), "policy_digest": digest(policy),
    }
    return digest(_canonical(frozen))


def make_envelope(*, execution_id: str, nonce: str, expires_at: str, message: str,
                  handler_bytes: bytes | None = None) -> dict:
    envelope = {
        "execution_id": execution_id, "nonce": nonce, "expires_at": expires_at,
        "handler": HANDLER,
        "payload": {"synthetic": True, "money": False, "message": message},
    }
    envelope["one_shot_hash"] = one_shot_hash(envelope, handler_bytes=handler_bytes)
    return envelope


def sign_for_test_or_human_client(envelope: dict, owner: str, secret: bytes) -> dict:
    """Construct an owner proof. Live callers must obtain this from the human client, never a model."""
    signature = hmac.new(secret, envelope["one_shot_hash"].encode(), hashlib.sha256).hexdigest()
    return {"owner": owner, "signature": signature}


@dataclass
class BridgeStore:
    path: Path

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS spent (execution_id TEXT PRIMARY KEY, nonce TEXT UNIQUE, state TEXT NOT NULL, receipt TEXT)")

    def spent(self, execution_id: str, nonce: str) -> bool:
        with sqlite3.connect(self.path) as db:
            return db.execute("SELECT 1 FROM spent WHERE execution_id=? OR nonce=?", (execution_id, nonce)).fetchone() is not None

    def claim(self, execution_id: str, nonce: str) -> None:
        with sqlite3.connect(self.path) as db:
            try:
                db.execute("INSERT INTO spent VALUES (?,?,?,?)", (execution_id, nonce, "EXECUTING", None))
            except sqlite3.IntegrityError:
                raise BridgeRefusal("REPLAY") from None

    def finish(self, execution_id: str, state: str, receipt: dict) -> None:
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE spent SET state=?, receipt=? WHERE execution_id=?",
                       (state, json.dumps(receipt, sort_keys=True), execution_id))


def execute(envelope: dict, authorization: dict, *, owner: str, owner_secret: bytes,
            store: BridgeStore, effect_dir: Path, now: datetime | None = None,
            handler_bytes: bytes | None = None) -> dict:
    """Validate and execute exactly one synthetic effect, then independently read it back."""
    payload = envelope.get("payload") or {}
    if payload.get("synthetic") is not True or payload.get("money") is not False:
        raise BridgeRefusal("B1_SCOPE")
    if envelope.get("handler") != HANDLER or set(payload) != {"synthetic", "money", "message"}:
        raise BridgeRefusal("HANDLER_NOT_ALLOWLISTED")
    execution_id, nonce = str(envelope.get("execution_id", "")), str(envelope.get("nonce", ""))
    if (not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", execution_id)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", nonce)):
        raise BridgeRefusal("IDENTIFIER_INVALID")
    if store.spent(execution_id, nonce):
        raise BridgeRefusal("REPLAY")
    current = now or datetime.now(timezone.utc)
    try:
        expiry = datetime.fromisoformat(str(envelope["expires_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        raise BridgeRefusal("EXPIRY_INVALID") from None
    if expiry <= current:
        raise BridgeRefusal("EXPIRED")
    expected_hash = one_shot_hash(envelope, handler_bytes=handler_bytes)
    if not hmac.compare_digest(str(envelope.get("one_shot_hash", "")), expected_hash):
        raise BridgeRefusal("DRIFT")
    if authorization.get("owner") != owner:
        raise BridgeRefusal("OWNER")
    expected_sig = hmac.new(owner_secret, expected_hash.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(str(authorization.get("signature", "")), expected_sig):
        raise BridgeRefusal("AUTHORIZATION")

    # Durable claim is the last gate and occurs before any effect. The UNIQUE execution_id + nonce
    # constraints make concurrent submissions single-use; a crash leaves EXECUTING for reconciliation,
    # never an apparently-unused envelope that can silently retry.
    store.claim(execution_id, nonce)
    effect_dir.mkdir(parents=True, exist_ok=True)
    target = effect_dir / f"{execution_id}.marker"
    data = str(payload["message"]).encode()
    target.write_bytes(data)
    verification = target.read_bytes() == data
    if not verification:
        raise BridgeRefusal("EFFECT_UNVERIFIED")
    receipt = {
        "execution_id": execution_id, "state": "RECEIPTED", "handler": HANDLER,
        "authorization": {"owner": owner, "proposal_hash": expected_hash},
        "execution": {"handler_digest": digest(handler_bytes if handler_bytes is not None else live_handler_bytes())},
        "effect": {"marker": target.name, "sha256": digest(data)},
        "verification": {"read_back": True, "sha256": digest(target.read_bytes())},
    }
    store.finish(execution_id, "RECEIPTED", receipt)
    return receipt
