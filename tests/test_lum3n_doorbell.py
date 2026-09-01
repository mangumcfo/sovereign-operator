from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "lum3n_doorbell.py"
SPEC = importlib.util.spec_from_file_location("lum3n_doorbell", SCRIPT)
doorbell = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(doorbell)


def comment(first: str) -> dict:
    return {"id": first, "body": first + "\nrest"}


def test_matches_machine_and_real_no1_grammar():
    assert doorbell._is_bell(comment("LUM3N DOORBELL"))
    assert doorbell._is_bell(comment("KM-NO1 GO — execute"))
    assert doorbell._is_bell(comment("KM-NO1 STEER + GO — room"))
    assert doorbell._is_bell(comment("NO1 — hold"))


def test_ignores_lum3n_updates_and_unrelated_comments():
    assert not doorbell._is_bell(comment("LUM3N DOORBELL ACK — consumed"))
    assert not doorbell._is_bell(comment("LUM3N IMPLEMENTATION UPDATE"))
    assert not doorbell._is_bell(comment("ordinary issue comment"))
