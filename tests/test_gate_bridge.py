from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from sovereign_operator.gate_bridge import (
    BridgeRefusal, BridgeStore, execute, make_envelope, sign_for_test_or_human_client,
)

NOW = datetime(2026, 9, 2, tzinfo=timezone.utc)
SECRET = b"fixture-owner-secret"


def valid(tmp_path):
    env = make_envelope(execution_id="e1", nonce="n1",
                        expires_at=(NOW + timedelta(minutes=5)).isoformat(), message="yellow-proof")
    auth = sign_for_test_or_human_client(env, "KM-1176", SECRET)
    kwargs = {"owner": "KM-1176", "owner_secret": SECRET, "store": BridgeStore(tmp_path / "state.sqlite3"),
              "effect_dir": tmp_path / "effects", "now": NOW}
    return env, auth, kwargs


def test_clean_synthetic_non_money_path_receipts_verified_effect(tmp_path):
    env, auth, kwargs = valid(tmp_path)
    receipt = execute(env, auth, **kwargs)
    assert receipt["state"] == "RECEIPTED"
    assert receipt["verification"]["read_back"] is True
    assert receipt["effect"]["sha256"] == receipt["verification"]["sha256"]


@pytest.mark.parametrize(("mutation", "code"), [
    (lambda e, a: e["payload"].update(synthetic=False), "B1_SCOPE"),
    (lambda e, a: e["payload"].update(money=True), "B1_SCOPE"),
    (lambda e, a: a.update(owner="agent"), "OWNER"),
    (lambda e, a: a.update(signature="bad"), "AUTHORIZATION"),
    (lambda e, a: e.update(expires_at="2020-01-01T00:00:00+00:00"), "EXPIRED"),
    (lambda e, a: e["payload"].update(message="drifted"), "DRIFT"),
])
def test_each_guard_refuses(tmp_path, mutation, code):
    env, auth, kwargs = valid(tmp_path)
    mutation(env, auth)
    with pytest.raises(BridgeRefusal, match=code):
        execute(env, auth, **kwargs)


def test_single_use_refuses_execution_id_and_nonce_replay(tmp_path):
    env, auth, kwargs = valid(tmp_path)
    execute(env, auth, **kwargs)
    with pytest.raises(BridgeRefusal, match="REPLAY"):
        execute(env, auth, **kwargs)
    second = make_envelope(execution_id="e2", nonce="n1",
                           expires_at=(NOW + timedelta(minutes=5)).isoformat(), message="other")
    with pytest.raises(BridgeRefusal, match="REPLAY"):
        execute(second, sign_for_test_or_human_client(second, "KM-1176", SECRET), **kwargs)


def test_live_handler_drift_refuses_before_effect(tmp_path):
    env, auth, kwargs = valid(tmp_path)
    with pytest.raises(BridgeRefusal, match="DRIFT"):
        execute(deepcopy(env), auth, handler_bytes=b"changed handler", **kwargs)
    assert not (tmp_path / "effects").exists()


def test_identifier_cannot_escape_effect_directory(tmp_path):
    env, _auth, kwargs = valid(tmp_path)
    env["execution_id"] = "../../escape"
    env["one_shot_hash"] = "irrelevant"
    with pytest.raises(BridgeRefusal, match="IDENTIFIER_INVALID"):
        execute(env, {}, **kwargs)
    assert not (tmp_path / "escape.marker").exists()


def test_crash_safe_claim_remains_spent(tmp_path):
    env, _auth, kwargs = valid(tmp_path)
    kwargs["store"].claim(env["execution_id"], env["nonce"])
    assert kwargs["store"].spent(env["execution_id"], env["nonce"])
    with pytest.raises(BridgeRefusal, match="REPLAY"):
        execute(env, sign_for_test_or_human_client(env, "KM-1176", SECRET), **kwargs)
