"""Tree-hygiene tests (U5/U8) — run without the fake node; pure source greps over the repo.

Forbidden-token patterns are assembled from fragments so the literals never appear in this file
(otherwise the scan would flag itself); this file is also excluded from the scan set.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
TESTS = ROOT / "tests"
SELF = pathlib.Path(__file__).name

# built from fragments on purpose (see module docstring)
_TELE = ["lang" + "smith", "post" + "hog", "sentry" + r"\.io", "OTEL" + "_", "smith" + r"\.langchain"]
_SECRET_RE = re.compile("|".join([r"192\.168\.", r"207\.244\.", r"\.nodekey"] + _TELE))
_CLOUD_RE = re.compile(r"\bimport\s+(anthropic|openai|" + "goog" + r"le|boto3)\b|from\s+(anthropic|openai)\b")


def _py_files(*dirs):
    for d in dirs:
        for f in d.rglob("*.py"):
            if f.name != SELF:
                yield f


_KERNEL_IMPORT = re.compile(r"^\s*(from|import)\s+sovereign_agent", re.M)


# ── U5 · no kernel imports: the operator composes over HTTP, importing zero USN packages ───────────
# (matches import STATEMENTS only — the fake status doc's `source` string is data, not an import)
def test_no_kernel_imports():
    hits = [str(f) for f in _py_files(SRC, TESTS) if _KERNEL_IMPORT.search(f.read_text())]
    assert hits == [], f"kernel import found (must be HTTP-only): {hits}"


# ── U2/U3 · tools never send a real request: no raw HTTP, no model, no usn_post exists ──────────────
# ('POST' appears in tools.py ONLY inside _curl(...) draft strings — that is text KM pastes, not an act)
def test_tools_send_no_real_request():
    text = (SRC / "sovereign_operator" / "tools.py").read_text()
    assert "usn_get" in text                       # the one client tools use — GET-only
    assert "import urllib" not in text and "urlopen" not in text   # no raw HTTP in the tool layer
    assert "mind_complete" not in text             # tools don't even touch the model
    assert 'method="POST"' not in text             # no real POST request is constructed here


def test_no_usn_post_function_anywhere():
    for f in _py_files(SRC):
        assert "def usn_post" not in f.read_text(), f"a usn_post() must never exist ({f})"


# ── the ONLY real POST request in the tree is the loopback model call in http_client.mind_complete ─
def test_only_real_post_is_the_loopback_mind():
    for f in _py_files(SRC):
        if 'method="POST"' in f.read_text():
            assert f.name == "http_client.py", f"unexpected real POST in {f} — only the loopback mind may POST"


# ── U8 · no secrets / real IPs / keys / telemetry hosts committed ──────────────────────────────────
def test_no_secrets_or_telemetry_in_tree():
    scan = list(_py_files(SRC, TESTS)) + list(ROOT.glob("*.toml")) + list((ROOT / "docs").rglob("*.md"))
    for f in scan:
        assert not _SECRET_RE.search(f.read_text()), f"forbidden token (IP/key/telemetry) in {f}"


# ── no cloud SDKs imported (U1 partial — the rest is AA's live dead-proxy session) ─────────────────
def test_no_cloud_sdk_imports():
    for f in _py_files(SRC):
        assert not _CLOUD_RE.search(f.read_text()), f"cloud SDK import in {f} — the operator is loopback-only"
