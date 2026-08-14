#!/usr/bin/env python3
"""build.py — build the sealed-corpus retrieval index (design: CORPUS_RETRIEVAL_DESIGN_2026-08-14).

Deterministic join: GB's seal_kind_registry.yaml (catalog authority, 131 rows) + series_roadmap.yaml
(titles/chapters) + the sealed chapter text. Text source = extracted text only (never the PDF binary):
- Series 5–14 sealed-runtime volumes → the press seed `chN.yaml` `prose:` fields (chapter-addressable).
- Foundational S0–S4 → `pdftotext` over the sealed PDF IF a local PDF is present (text is public-OK; the
  PDF binary never enters the tree/index).
- XRP (S0-04) → MISSING/void: catalog gap row, NO chunks, never prose.
- PRIV/concept → designed-not-built: catalog row, no chunks.

Output (all public-OK, committed to corpus/index/): catalog.jsonl · chunks.jsonl · embeddings.jsonl ·
gaps.jsonl · MANIFEST.json. Embeddings are LOCAL (Ollama nomic-embed-text, loopback) — zero cloud.
No USN/kernel/registry write; this is a reader.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml  # build-time only; the retrieval runtime is stdlib

WORKBENCH = Path(os.environ.get("CORPUS_WORKBENCH", os.path.expanduser("~/work-repos/breathline-workbench")))
REGISTRY = WORKBENCH / "artifacts/catalog/seal_kind_registry.yaml"
ROADMAP = WORKBENCH / "artifacts/series_roadmap.yaml"
SEEDS = WORKBENCH / "tools/press/seeds"
OUT = Path(__file__).resolve().parent / "index"
EMBED_URL = os.environ.get("CORPUS_EMBED_URL", "http://127.0.0.1:11434/api/embeddings")
EMBED_MODEL = os.environ.get("CORPUS_EMBED_MODEL", "nomic-embed-text")

TIER = {"S0": "teach", "S1": "teach", "S2": "spec", "S3": "spec", "S4": "spec",
        "S5": "sealed", "S6": "sealed", "S7": "sealed", "S8": "sealed", "S9": "sealed",
        "S10": "sealed", "S11": "sealed", "S12": "sealed", "S13": "sealed", "S14": "sealed",
        "PRIV": "private"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


# ── seed index: (series_num, vol_num) -> seed dir, for the S5–S14 text join ────────────────────────
def _vol_num(slug: str):
    m = re.search(r"(?:^|_|/)(?:vol_)?0*(\d{1,2})(?:_|$)", slug)
    return int(m.group(1)) if m else None


def build_seed_index() -> dict:
    idx = {}
    for d in sorted(SEEDS.glob("*_fs")):
        name = d.name[:-3]  # strip _fs
        m = re.match(r"s(\d+)_(\d+)_", name)
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2)))
        idx.setdefault(key, []).append((name, d))
    return idx


def _pick_seed(cands: list, reg_slug: str):
    """When >1 seed maps to a (series,vol) (rebuilds), pick the best token-overlap with the registry slug."""
    if len(cands) == 1:
        return cands[0]
    reg_tokens = set(re.findall(r"[a-z]+", reg_slug.lower()))
    best, best_ov = cands[0], -1
    for name, d in cands:
        ov = len(set(re.findall(r"[a-z]+", name.lower())) & reg_tokens)
        if ov > best_ov:
            best, best_ov = (name, d), ov
    return best


# ── chapter extraction ─────────────────────────────────────────────────────────────────────────────
def extract_seed_chapters(seed_dir: Path) -> list[dict]:
    """Return [{chapter, title, prose, source_path, source_sha}] from a seed dir's chN.yaml prose fields."""
    out = []
    for ch in sorted(seed_dir.glob("ch*.yaml"), key=lambda p: int(re.search(r"ch(\d+)", p.name).group(1))):
        try:
            y = yaml.safe_load(ch.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        prose = _norm(y.get("prose", ""))
        if not prose or len(prose) < 200:
            continue
        out.append({"chapter": y.get("chapter"), "title": _norm(y.get("title", "")),
                    "promise": _norm(y.get("promise", "")), "prose": prose,
                    "source_path": str(ch.relative_to(WORKBENCH)),
                    "source_sha": sha256_bytes(ch.read_bytes())})
    return out


# ── chapter-aware chunking (never cross a chapter; ~900 words, ~15% overlap), content-addressed ──────
def chunk_chapter(prose: str, words_per=900, overlap=0.15) -> list[str]:
    paras = [p.strip() for p in re.split(r"(?<=[.!?])\s{2,}|\n\n", prose) if p.strip()]
    if not paras:
        paras = [prose]
    # force-split any single paragraph longer than the window (else a wall of text = one mega-chunk)
    split = []
    for p in paras:
        w = p.split()
        if len(w) > words_per:
            for s in range(0, len(w), words_per):
                split.append(" ".join(w[s:s + words_per]))
        else:
            split.append(p)
    paras = split
    chunks, cur, cur_w = [], [], 0
    for p in paras:
        w = len(p.split())
        if cur_w + w > words_per and cur:
            chunks.append(" ".join(cur))
            keep = max(1, int(len(cur) * overlap))
            cur, cur_w = cur[-keep:], sum(len(x.split()) for x in cur[-keep:])
        cur.append(p); cur_w += w
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def embed(text: str) -> list[float]:
    body = json.dumps({"model": EMBED_MODEL, "prompt": "search_document: " + text}).encode()
    req = urllib.request.Request(EMBED_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 (loopback)
        return json.loads(r.read().decode())["embedding"]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reg = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    vols = reg["volumes"]
    roadmap_sha = sha256_bytes(ROADMAP.read_bytes()) if ROADMAP.exists() else None
    registry_sha = sha256_bytes(REGISTRY.read_bytes())
    seed_idx = build_seed_index()

    catalog, chunks, gaps = [], [], []
    embeddings = []
    covered = 0
    for key in sorted(vols):
        v = vols[key]
        series, slug = key.split("/", 1)
        kinds = v.get("seal_kind", [])
        stage = v.get("stage")
        missing = ("void" in kinds) or bool(v.get("never_publishable"))
        title = _norm(slug.split(":")[0].replace("_", " ")).title() if "_" in slug else _norm(slug)
        row = {"volume_id": key, "series": series, "slug": slug, "title": title,
               "tier": TIER.get(series, "?"), "seal_kind": kinds, "stage": stage,
               "missing": missing, "text_indexed": False, "chapters_indexed": 0,
               "note": v.get("note")}

        if missing:
            row["seal_status"] = "MISSING"
            gaps.append({"volume_id": key, "title": title, "reason": v.get("note", "unbuilt / never-publishable"),
                         "status": "MISSING"})
            catalog.append(row)
            continue
        if "concept" in kinds:
            row["seal_status"] = "concept"
            catalog.append(row)  # designed-not-built: catalog row, no chunks
            continue

        # find a text source (seed for S5–S14)
        vn = _vol_num(slug)
        snum = int(series[1:]) if series[1:].isdigit() else None
        chapters = []
        if snum is not None and vn is not None and (snum, vn) in seed_idx:
            _, seed_dir = _pick_seed(seed_idx[(snum, vn)], slug)
            chapters = extract_seed_chapters(seed_dir)
            row["text_source"] = f"seed:{seed_dir.name}"

        row["seal_status"] = stage or "sealed"
        if not chapters:
            catalog.append(row)  # foundational / no local text yet: catalog row, no chunks (honest)
            continue

        covered += 1
        row["text_indexed"] = True
        row["chapters_indexed"] = len(chapters)
        for ch in chapters:
            # a chapter-level SUMMARY artifact (the promise) — labeled, and down-weighted vs sealed chunks
            if ch["promise"]:
                sid = "sum_" + sha256_text(key + str(ch["chapter"]) + ch["promise"])[:14]
                chunks.append({"chunk_id": sid, "kind": "summary", "volume_id": key, "series": series,
                               "title": title, "chapter": ch["chapter"], "chapter_title": ch["title"],
                               "seal_kind": kinds, "text": ch["promise"],
                               "source_path": ch["source_path"], "source_sha": ch["source_sha"]})
                embeddings.append((sid, embed(ch["promise"])))
            for ci, ctext in enumerate(chunk_chapter(ch["prose"])):
                cid = sha256_text(ctext)[:16]  # content-addressed (design §5)
                chunks.append({"chunk_id": cid, "kind": "chunk", "volume_id": key, "series": series,
                               "title": title, "chapter": ch["chapter"], "chapter_title": ch["title"],
                               "chunk_ix": ci, "seal_kind": kinds, "text": ctext,
                               "source_path": ch["source_path"], "source_sha": ch["source_sha"]})
                embeddings.append((cid, embed(ctext)))
        catalog.append(row)
        print(f"  indexed {key} · {len(chapters)} ch · {row['chapters_indexed']} chapters", file=sys.stderr)

    # write index
    (OUT / "catalog.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in catalog) + "\n", encoding="utf-8")
    (OUT / "chunks.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in chunks) + "\n", encoding="utf-8")
    (OUT / "gaps.jsonl").write_text("\n".join(json.dumps(g, ensure_ascii=False) for g in gaps) + "\n", encoding="utf-8")
    with (OUT / "embeddings.jsonl").open("w", encoding="utf-8") as f:
        for cid, vec in embeddings:
            f.write(json.dumps({"chunk_id": cid, "v": [round(x, 6) for x in vec]}) + "\n")

    manifest = {
        "catalog_gen": 1,
        "generated_from": {"registry_sha256": registry_sha, "roadmap_sha256": roadmap_sha,
                           "registry_path": str(REGISTRY.relative_to(WORKBENCH)),
                           "seeds_dir": str(SEEDS.relative_to(WORKBENCH))},
        "embed": {"model": EMBED_MODEL, "endpoint": "loopback (Ollama)", "dim": len(embeddings[0][1]) if embeddings else 0,
                  "prefix": "search_document: / search_query:", "where": "operator iron (server1), zero cloud"},
        "counts": {"catalog_rows": len(catalog), "volumes_text_indexed": covered,
                   "chunks": sum(1 for c in chunks if c["kind"] == "chunk"),
                   "summaries": sum(1 for c in chunks if c["kind"] == "summary"),
                   "gaps_missing": len(gaps)},
        "shas": {"catalog": sha256_bytes((OUT / "catalog.jsonl").read_bytes()),
                 "chunks": sha256_bytes((OUT / "chunks.jsonl").read_bytes()),
                 "embeddings": sha256_bytes((OUT / "embeddings.jsonl").read_bytes())},
    }
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest["counts"], indent=2))
    print("catalog_rows=%d text_indexed=%d chunks=%d summaries=%d gaps=%d" % (
        len(catalog), covered, manifest["counts"]["chunks"], manifest["counts"]["summaries"], len(gaps)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
