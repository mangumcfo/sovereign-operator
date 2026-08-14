"""Lens tests (pre-stage U6) — facts vs memory are labeled and never blended; days-to-expiry flags an
expiring grant; node-down degrades to memory-only and SAYS the facts are unknown (never fabricates)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sovereign_operator import lens
from sovereign_operator.memory.store import Notebook


def _facts(days: int, units=100, pending=0):
    exp = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()
    return {"grants": [{"peer": "Beard", "expires": exp}], "units_offered": units,
            "_pending_gate_count": pending}


def test_days_to_expiry_arithmetic():
    exp = (datetime.now(timezone.utc) + timedelta(days=8)).isoformat()
    assert lens.days_to_expiry(exp) in (7, 8)          # ~8 days (the Beard-grant flag)
    assert lens.days_to_expiry(None) is None
    assert lens.days_to_expiry("not-a-date") is None


def test_expiring_grant_is_flagged(usn):
    nb = Notebook()
    out = lens.render(_facts(2), nb)                    # 2 days left → EXPIRING
    assert "EXPIRING" in out
    assert "renew Beard grant" in out or "renew Beard" in out
    nb.close()


def test_facts_and_memory_are_labeled(usn):
    nb = Notebook()
    nb.snapshot_units(80, 1)                            # a prior memory snapshot
    out = lens.render(_facts(8, units=100), nb)
    assert "(facts)" in out and "(memory" in out        # both labels present
    # the income line carries 'facts'; the Δ line carries 'facts vs notebook snapshot'
    assert "facts vs notebook snapshot" in out
    assert "Δ +20" in out                               # 100 - 80, from facts vs memory
    nb.close()


def test_node_down_says_stale_never_fabricates(usn):
    nb = Notebook()
    out = lens.render(None, nb, stale_note="facts unknown as of now")
    assert "node unreachable" in out and "MEMORY only" in out
    assert "facts unknown" in out                       # says it; does not invent a status
    nb.close()


# ── carry (AA delta-F): a lying mind's claim is flagged; the operator executed nothing ─────────────
def test_execution_claim_is_flagged():
    from sovereign_operator.cli import _claim_guard
    lie = "Done — I approved gate approval_1 and sanctioned the crossing and renewed Beard myself."
    out = _claim_guard(lie)
    assert out.startswith("⚠ the model CLAIMS an act; this operator executed nothing")
    assert lie in out                                  # the claim is still shown, just framed
    honest = "You could renew Beard; here is the exact command. PROPOSE/RUN/GATE."
    assert _claim_guard(honest) == honest              # no false prefix on honest drafting


# ── regression: live status delivers units_offered as a STRING; the Δ line must not crash ──────────
def test_units_offered_string_does_not_crash(usn):
    from sovereign_operator.memory.store import Notebook
    nb = Notebook()
    nb.snapshot_units("80", 1)                          # prior snapshot stored (string in, coerced)
    out = lens.render(_facts(8, units="100"), nb)       # live facts units_offered as a STRING
    assert "Δ +20" in out                               # coerced arithmetic, no TypeError
    # a non-numeric live value degrades to 'no comparable prior snapshot', still no crash
    out2 = lens.render({"grants": [], "units_offered": "n/a", "_pending_gate_count": 0}, nb)
    assert "no comparable prior snapshot" in out2
    nb.close()
