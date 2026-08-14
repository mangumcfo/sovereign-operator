#!/usr/bin/env python3
"""verify.py — C10 byte-true check. For a sample of chunks, re-derive the sealed source text
deterministically from the recorded source at its recorded SHA, and assert the chunk's text appears
verbatim in it (whitespace-normalized on both sides). Sealed-runtime chunks re-derive from the seed
`chN.yaml prose:`; foundational chunks re-derive from `pdftotext` over the shelf PDF (bound to
artifact_sha256). Also re-confirms the recorded source SHA. Read-only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_pdf_foundational import _clean_paras  # re-derive PDF text exactly as the build did

WB = Path(os.path.expanduser("~/work-repos/breathline-workbench"))
SHELF = Path(os.environ.get("CORPUS_SHELF", "/tmp/breathline_books_20260813"))
IDX = Path(__file__).resolve().parent / "index"


def _n(s):
    return re.sub(r"\s+", " ", s or "").strip()


def rederive(chunk) -> tuple[str, str | None]:
    """Return (normalized_source_text, recomputed_sha) for a chunk's source."""
    sp = chunk["source_path"]
    if sp.startswith("pdf:"):
        pdf = SHELF / sp[4:]
        if not pdf.exists():
            return "", None
        txt = subprocess.check_output(["pdftotext", "-q", str(pdf), "-"], text=True, errors="ignore")
        return _n(_clean_paras(txt)), hashlib.sha256(pdf.read_bytes()).hexdigest()
    src = WB / sp
    if not src.exists():
        return "", None
    prose = yaml.safe_load(src.read_text(encoding="utf-8")).get("prose", "")
    return _n(prose), hashlib.sha256(src.read_bytes()).hexdigest()


def main():
    chunks = [json.loads(l) for l in (IDX / "chunks.jsonl").read_text().splitlines() if l.strip()]
    chunks = [c for c in chunks if c["kind"] == "chunk"]
    seed = [c for c in chunks if c["source_path"].endswith(".yaml")]
    pdf = [c for c in chunks if c["source_path"].startswith("pdf:")]
    # sample deterministically (every Nth) across both sources
    sample = seed[::max(1, len(seed) // 8)][:8] + pdf[::max(1, len(pdf) // 8)][:8]
    ok = 0
    print(f"C10 · sampling {len(sample)} chunks ({len(seed)} seed-sourced, {len(pdf)} pdf-sourced total)")
    for c in sample:
        src_text, sha = rederive(c)
        sub = _n(c["text"]) in src_text
        sha_ok = (sha == c["source_sha"])
        ok += (sub and sha_ok)
        print(f"  {c['chunk_id']} · {c['volume_id']} Ch{c.get('chapter')} · "
              f"verbatim={sub} · source_sha_match={sha_ok}")
    print(f"C10 result: {ok}/{len(sample)} chunks byte-true to their recorded source")
    return 0 if ok == len(sample) else 1


if __name__ == "__main__":
    raise SystemExit(main())
