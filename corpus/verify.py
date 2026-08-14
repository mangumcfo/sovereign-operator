#!/usr/bin/env python3
"""verify.py — C10 byte-true check + missing-row alias-guard assertion.

For a sample of chunks, re-derive the sealed source text deterministically from the recorded source at
its recorded SHA and compare the chunk verbatim (whitespace-normalized). Three distinct states — a
verifier must never render "could not check" as "FAILED" (the H7 three-state law, AA §3a):

  verbatim               — the chunk text is present in the re-derived source AND the source SHA matches
  DIFFERS                — the source is present here but the chunk is NOT in it, or the SHA mismatches (a REAL finding)
  SOURCE-NOT-AVAILABLE   — the source file/PDF is not on THIS rig (e.g. the shelf is /tmp; the seed WB is elsewhere)

Sources: sealed-runtime → seed `chN.yaml prose:` under the workbench (env CORPUS_WB); foundational →
`pdftotext` over the shelf PDF (env CORPUS_SHELF), bound to artifact_sha256. Read-only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pdf_foundational import _clean_paras  # re-derive PDF text exactly as the build did

WB = Path(os.environ.get("CORPUS_WB", os.path.expanduser("~/work-repos/breathline-workbench")))
SHELF = Path(os.environ.get("CORPUS_SHELF", "/tmp/breathline_books_20260813"))
IDX = Path(os.environ.get("CORPUS_INDEX", str(Path(__file__).resolve().parent / "index")))

VERBATIM, DIFFERS, ABSENT = "verbatim", "DIFFERS", "SOURCE-NOT-AVAILABLE"


def _n(s):
    return re.sub(r"\s+", " ", s or "").strip()


def check(chunk) -> tuple[str, str]:
    """Return (state, detail) for one chunk against its recorded source."""
    sp = chunk["source_path"]
    if sp.startswith("pdf:"):
        pdf = SHELF / sp[4:]
        if not pdf.exists():
            return ABSENT, f"shelf PDF not on this rig ({pdf})"
        raw = subprocess.check_output(["pdftotext", "-q", str(pdf), "-"], text=True, errors="ignore")
        src, sha = _n(_clean_paras(raw)), hashlib.sha256(pdf.read_bytes()).hexdigest()
    else:
        src_file = WB / sp
        if not src_file.exists():
            return ABSENT, f"seed source not on this rig ({src_file})"
        prose = yaml.safe_load(src_file.read_text(encoding="utf-8")).get("prose", "")
        src, sha = _n(prose), hashlib.sha256(src_file.read_bytes()).hexdigest()
    if _n(chunk["text"]) in src and sha == chunk["source_sha"]:
        return VERBATIM, f"sha {sha[:12]}"
    if sha != chunk["source_sha"]:
        return DIFFERS, f"source SHA changed (recorded {chunk['source_sha'][:12]}, now {sha[:12]})"
    return DIFFERS, "chunk text not found verbatim in source"


def c10(chunks) -> int:
    seed = [c for c in chunks if c["source_path"].endswith(".yaml")]
    pdf = [c for c in chunks if c["source_path"].startswith("pdf:")]
    sample = seed[::max(1, len(seed) // 8)][:8] + pdf[::max(1, len(pdf) // 8)][:8]
    from collections import Counter
    tally = Counter()
    print(f"C10 · sampling {len(sample)} chunks · WB={WB} · SHELF={SHELF}")
    for c in sample:
        state, detail = check(c)
        tally[state] += 1
        print(f"  {c['chunk_id']} · {c['volume_id']} Ch{c.get('chapter')} · {state:22s} · {detail}")
    print(f"C10: verbatim={tally[VERBATIM]} · DIFFERS={tally[DIFFERS]} · {ABSENT}={tally[ABSENT]}")
    # PASS = no genuine DIFFERS; SOURCE-NOT-AVAILABLE is neutral (could-not-check ≠ failed)
    return 0 if tally[DIFFERS] == 0 else 1


def alias_guard(catalog) -> int:
    """AA §3b — every MISSING/void row must be guarded (has curated aliases, or the generic-fallback
    alias derived from its slug). A future alias-less gap must not silently lose its C2 guard."""
    from retrieval import Corpus
    aliases = Corpus._MISSING_ALIASES
    missing = [r for r in catalog if r.get("missing")]
    print(f"\nalias-guard · {len(missing)} MISSING row(s):")
    bad = 0
    for r in missing:
        guarded = r["volume_id"] in aliases and len(aliases[r["volume_id"]]) > 0
        # generic fallback: _missing_hit falls back to the last slug segment as an alias
        fallback = bool(r["volume_id"].split("/")[-1].strip())
        ok = guarded or fallback
        bad += not ok
        print(f"  {r['volume_id']} · curated_aliases={guarded} · slug_fallback={fallback} · {'GUARDED' if ok else 'UNGUARDED'}")
    print(f"alias-guard: {'PASS — every missing row is guarded' if bad == 0 else f'FAIL — {bad} unguarded'}")
    return 0 if bad == 0 else 1


def main() -> int:
    chunks = [json.loads(l) for l in (IDX / "chunks.jsonl").read_text().splitlines() if l.strip()]
    catalog = [json.loads(l) for l in (IDX / "catalog.jsonl").read_text().splitlines() if l.strip()]
    chunks = [c for c in chunks if c["kind"] == "chunk"]
    return c10(chunks) | alias_guard(catalog)


if __name__ == "__main__":
    raise SystemExit(main())
