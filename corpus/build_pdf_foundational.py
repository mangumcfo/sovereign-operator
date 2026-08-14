#!/usr/bin/env python3
"""build_pdf_foundational.py — add the foundational/early tiers (the volumes without press-seed prose:
S0, S1, S2, S3, S4) to the corpus index by `pdftotext` over GB's gathered shelf (design §2 canonical
source). The PDF binary NEVER enters the tree — only extracted text + embeddings, bound to the PDF's
`artifact_sha256`. Appends to the existing index (idempotent, content-addressed). Local embed, no cloud.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import chunk_chapter, embed, sha256_bytes, sha256_text, _norm  # reuse

SHELF = Path(os.environ.get("CORPUS_SHELF", "/tmp/breathline_books_20260813"))
OUT = Path(__file__).resolve().parent / "index"

_CHAP = re.compile(r"^\s*(?:chapter|CHAPTER)\s+(\d+)\b[:.\-\s]*(.{0,70})$")


def find_pdf(series: str, slug: str):
    n = int(series[1:]) if series[1:].isdigit() else None
    if n is None:
        return None
    folder = next((d for d in SHELF.glob(f"S{n:02d}_*") if d.is_dir()), None)
    if not folder:
        return None
    hits = sorted(folder.glob(f"{slug}__*.pdf")) or sorted(folder.glob(f"{slug}*.pdf"))
    if not hits:  # fall back to the leading volume number (registry slug ≠ filename slug, e.g. 06_capture vs 06_the_capture)
        m = re.match(r"(?:vol_)?0*(\d+)", slug)
        if m:
            n = int(m.group(1))
            hits = [p for p in sorted(folder.glob("*.pdf")) if re.match(rf"(?:vol_)?0*{n}_", p.name)]
    return hits[0] if hits else None


_HEAD = re.compile(r"(?m)^[ \t]*chapter[ \t]+(\d+)\b[:.\-\s]*(.{0,60})$", re.IGNORECASE)


def _clean_paras(seg: str) -> str:
    """Preserve paragraph breaks (blank-line separated); drop page-number-only lines; normalize
    within-paragraph whitespace. Keeps \\n\\n so the chunker can split it."""
    paras = []
    for block in re.split(r"\n[ \t]*\n", seg):
        lines = [ln.strip() for ln in block.split("\n")
                 if ln.strip() and not re.fullmatch(r"\d+", ln.strip())]
        t = _norm(" ".join(lines))
        if len(t.split()) >= 8:
            paras.append(t)
    return "\n\n".join(paras)


def extract_chapters(pdf: Path):
    """Foundational tier: extract the full cleaned body and index it at SECTION level (chapter=None).

    Precise chapter boundaries are not recoverable reliably from these PDFs (running-header repeats +
    TOC clusters), so we do NOT fabricate chapter numbers. The body is cleaned (paragraphs preserved,
    front matter skipped) and the chunker force-splits it into many ~900-word sealed-text chunks, each
    cited at volume+section level — honest, and enough for tier-honest retrieval (C9). The 94
    sealed-runtime volumes keep true chapter-level cites from their seed manuscripts.
    """
    raw = subprocess.check_output(["pdftotext", "-q", str(pdf), "-"], text=True, errors="ignore")
    body = _clean_paras(raw)
    body = body[1500:] if len(body) > 4000 else body     # skip title/copyright/TOC front matter
    return [{"chapter": None, "title": "(section-level; foundational PDF)", "prose": body}] if len(body) > 500 else []


def main() -> int:
    catalog = [json.loads(l) for l in (OUT / "catalog.jsonl").read_text().splitlines() if l.strip()]
    chunks = [json.loads(l) for l in (OUT / "chunks.jsonl").read_text().splitlines() if l.strip()]
    seen = {c["chunk_id"] for c in chunks}
    manifest = json.loads((OUT / "MANIFEST.json").read_text())
    emb_lines = (OUT / "embeddings.jsonl").read_text().splitlines()

    # reset any prior pdf-sourced foundational chunks so re-runs are idempotent (content-addressed)
    pdf_ids = {c["chunk_id"] for c in chunks if str(c.get("source_path", "")).startswith("pdf:")}
    if pdf_ids:
        chunks = [c for c in chunks if c["chunk_id"] not in pdf_ids]
        emb_lines = [l for l in emb_lines if json.loads(l)["chunk_id"] not in pdf_ids]
        (OUT / "embeddings.jsonl").write_text("\n".join(emb_lines) + ("\n" if emb_lines else ""))
        for r in catalog:
            if str(r.get("text_source", "")).startswith("pdf:"):
                r["text_indexed"] = False
                for k in ("chapters_indexed", "text_source", "artifact_sha256"):
                    r.pop(k, None)
        seen = {c["chunk_id"] for c in chunks}
        print(f"  reset {len(pdf_ids)} prior pdf chunks", file=sys.stderr)

    added_vols, added_chunks, new_emb = 0, 0, []
    TARGET = {"S0", "S1", "S2", "S3", "S4"}
    for row in catalog:
        if row["series"] not in TARGET or row.get("missing") or "concept" in row.get("seal_kind", []) \
           or row.get("text_indexed"):
            continue
        pdf = find_pdf(row["series"], row["slug"])
        if not pdf:
            print(f"  no PDF for {row['volume_id']}", file=sys.stderr)
            continue
        art_sha = sha256_bytes(pdf.read_bytes())
        chs = extract_chapters(pdf)
        if not chs:
            print(f"  no extractable text for {row['volume_id']}", file=sys.stderr)
            continue
        row["text_indexed"] = True
        row["chapters_indexed"] = len(chs)
        row["text_source"] = f"pdf:{pdf.relative_to(SHELF)}"
        row["artifact_sha256"] = art_sha
        for ch in chs:
            for ci, ctext in enumerate(chunk_chapter(ch["prose"])):
                cid = sha256_text(ctext)[:16]
                if cid in seen:
                    continue
                seen.add(cid)
                chunks.append({"chunk_id": cid, "kind": "chunk", "volume_id": row["volume_id"],
                               "series": row["series"], "title": row["title"], "chapter": ch["chapter"],
                               "chapter_title": ch["title"], "chunk_ix": ci, "seal_kind": row["seal_kind"],
                               "text": ctext, "source_path": row["text_source"], "source_sha": art_sha})
                new_emb.append((cid, embed(ctext)))
                added_chunks += 1
        added_vols += 1
        print(f"  +pdf {row['volume_id']} · {len(chs)} ch · artifact {art_sha[:12]}", file=sys.stderr)

    # rewrite index
    (OUT / "catalog.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in catalog) + "\n")
    (OUT / "chunks.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + "\n")
    with (OUT / "embeddings.jsonl").open("a", encoding="utf-8") as f:
        for cid, vec in new_emb:
            f.write(json.dumps({"chunk_id": cid, "v": [round(x, 6) for x in vec]}) + "\n")

    manifest["counts"]["catalog_rows"] = len(catalog)
    manifest["counts"]["volumes_text_indexed"] = sum(1 for r in catalog if r.get("text_indexed"))
    manifest["counts"]["chunks"] = sum(1 for c in chunks if c["kind"] == "chunk")
    manifest["counts"]["summaries"] = sum(1 for c in chunks if c["kind"] == "summary")
    manifest.setdefault("text_sources", {})
    manifest["text_sources"] = {"sealed_runtime_S5_S14": "press seed chN.yaml prose (chapter-addressable)",
                                "foundational_S0_S4": "pdftotext over gathered shelf (artifact_sha256 bound); PDF binary NOT in tree"}
    manifest["shas"] = {"catalog": sha256_bytes((OUT / "catalog.jsonl").read_bytes()),
                        "chunks": sha256_bytes((OUT / "chunks.jsonl").read_bytes()),
                        "embeddings": sha256_bytes((OUT / "embeddings.jsonl").read_bytes())}
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    print(f"added {added_vols} foundational volumes · {added_chunks} chunks")
    print(json.dumps(manifest["counts"], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
