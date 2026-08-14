"""retrieval.py — read-only hybrid retrieval over the built corpus index. Stdlib only.

Hybrid = dense (local Ollama embedding, cosine) + sparse (BM25), metadata pre-filter, then fuse.
Contract (design §4, AA C1/C2): CITE-OR-REFUSE — every substantive result carries a chapter-level
citation to a real chunk of a real catalogued title, or the tool refuses ("not in the corpus").
NO-INVENT-GAP — a query about a MISSING/void title (XRP) returns MISSING with the catalog row, never
prose and never a silently-substituted near neighbour. Summaries are labeled and never outrank a
sealed chunk (design §6, C6). No write path exists; no USN/kernel import; embedding is loopback-local.
"""
from __future__ import annotations

import json
import math
import os
import re
import urllib.request
from collections import Counter
from pathlib import Path

INDEX = Path(os.environ.get("CORPUS_INDEX", str(Path(__file__).resolve().parent / "index")))
EMBED_URL = os.environ.get("CORPUS_EMBED_URL", "http://127.0.0.1:11434/api/embeddings")
EMBED_MODEL = os.environ.get("CORPUS_EMBED_MODEL", "nomic-embed-text")
REFUSE = "not in the corpus"
SUMMARY_PENALTY = 0.85       # a matching sealed chunk outranks a matching summary (C6)
DENSE_W = 0.6                # hybrid fusion weight
MIN_SCORE = 0.30            # below this, cite-or-refuse fires


def _loopback_or_die(url: str) -> str:
    host = re.sub(r"^https?://", "", url).split("/")[0].rsplit(":", 1)[0]
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError(f"corpus embed is loopback-only (got {host!r}) — no cloud embed")
    return url


def _tok(s: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", (s or "").lower())


class Corpus:
    def __init__(self, index=INDEX):
        self.dir = Path(index)
        self.catalog = [json.loads(l) for l in (self.dir / "catalog.jsonl").read_text().splitlines() if l.strip()]
        self.chunks = [json.loads(l) for l in (self.dir / "chunks.jsonl").read_text().splitlines() if l.strip()]
        self.gaps = [json.loads(l) for l in (self.dir / "gaps.jsonl").read_text().splitlines() if l.strip()]
        self.manifest = json.loads((self.dir / "MANIFEST.json").read_text())
        self.vecs = {}
        for l in (self.dir / "embeddings.jsonl").read_text().splitlines():
            if l.strip():
                o = json.loads(l); self.vecs[o["chunk_id"]] = o["v"]
        self.by_id = {c["chunk_id"]: c for c in self.chunks}
        self.cat_by_vol = {r["volume_id"]: r for r in self.catalog}
        self._bm25_prep()

    # ── BM25 ──
    def _bm25_prep(self):
        self.docs_tok = [_tok(c["text"]) for c in self.chunks]
        self.doclen = [len(t) for t in self.docs_tok]
        self.avgdl = (sum(self.doclen) / len(self.doclen)) if self.doclen else 0
        df = Counter()
        for t in self.docs_tok:
            for w in set(t):
                df[w] += 1
        N = len(self.docs_tok)
        self.idf = {w: math.log(1 + (N - n + 0.5) / (n + 0.5)) for w, n in df.items()}

    def _bm25_scores(self, q_tok, cand_ix, k1=1.5, b=0.75):
        out = {}
        for i in cand_ix:
            tf = Counter(self.docs_tok[i])
            s = 0.0
            for w in q_tok:
                if w not in tf:
                    continue
                idf = self.idf.get(w, 0.0)
                s += idf * (tf[w] * (k1 + 1)) / (tf[w] + k1 * (1 - b + b * self.doclen[i] / (self.avgdl or 1)))
            out[i] = s
        return out

    # ── dense ──
    def _embed_query(self, q: str) -> list[float]:
        body = json.dumps({"model": EMBED_MODEL, "prompt": "search_query: " + q}).encode()
        req = urllib.request.Request(_loopback_or_die(EMBED_URL), data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (loopback)
            return json.loads(r.read().decode())["embedding"]

    @staticmethod
    def _cos(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    # ── the ONE ranked query used by the tools ──
    def _rank(self, query: str, filters: dict | None, k: int):
        filters = filters or {}
        cand = list(range(len(self.chunks)))
        def keep(i):
            c = self.chunks[i]
            if filters.get("series") and c["series"] != filters["series"]:
                return False
            if filters.get("vol") and c["volume_id"] != filters["vol"]:
                return False
            if filters.get("chapter") and c.get("chapter") != filters["chapter"]:
                return False
            if filters.get("sealed_only") and self.cat_by_vol.get(c["volume_id"], {}).get("tier") != "sealed":
                return False
            if filters.get("tier") and self.cat_by_vol.get(c["volume_id"], {}).get("tier") != filters["tier"]:
                return False
            return True
        cand = [i for i in cand if keep(i)]
        if not cand:
            return []
        q_tok = _tok(query)
        bm = self._bm25_scores(q_tok, cand)
        qv = self._embed_query(query)
        dense = {i: self._cos(qv, self.vecs[self.chunks[i]["chunk_id"]])
                 for i in cand if self.chunks[i]["chunk_id"] in self.vecs}

        def norm(d):
            if not d:
                return {}
            lo, hi = min(d.values()), max(d.values())
            return {i: (0.0 if hi == lo else (v - lo) / (hi - lo)) for i, v in d.items()}
        nb, nd = norm(bm), norm(dense)
        fused = {i: DENSE_W * nd.get(i, 0.0) + (1 - DENSE_W) * nb.get(i, 0.0) for i in cand}
        # C6 (design §6): a summary NEVER outranks a sealed chunk. Hard rule — sealed chunks sort ahead
        # of every summary; within each kind, by fused relevance. Summaries are labeled aids, shown after.
        ranked = sorted(cand, key=lambda i: (0 if self.chunks[i]["kind"] == "chunk" else 1, -fused[i]))[:k]
        return [(i, fused[i]) for i in ranked]

    def _citation(self, c: dict) -> str:
        return (f"[{c['series']} · {c['title']} · Ch {c.get('chapter','?')}"
                f"{' ' + c['chapter_title'] if c.get('chapter_title') else ''}"
                f" · {'/'.join(c.get('seal_kind', []))} · {c['kind']} {c['chunk_id'][:8]}]")

    # ── the void/MISSING guard (C2 no-invent-gap) ──
    # DISTINCTIVE aliases only — never common words like "value"/"strategy"/"world" (which appear in
    # XRP's title but also in many legitimate sealed queries; matching them would mis-route real queries).
    _MISSING_ALIASES = {
        "S0/XRP: Decoding Strategy, Technology, and Utility": [
            "xrp", "s0-04", "s0 04", "s0/04", "decoding strategy", "ripple xrp",
            "book 4 of the foundation", "book four of the foundation", "foundation series book 4",
            "book 4 foundation", "fourth book of the foundation", "s0-4 xrp"],
    }

    def _missing_hit(self, query: str):
        ql = " " + query.lower() + " "
        for r in self.catalog:
            if not r.get("missing"):
                continue
            aliases = self._MISSING_ALIASES.get(r["volume_id"], [r["volume_id"].split("/")[-1].lower()])
            if any(a in ql for a in aliases):
                return r
            # "book 4"/"volume 4" of the foundational/executive series → S0-04 XRP
            if re.search(r"\bbook\s*(4|four)\b|\bvol(?:ume)?\s*4\b", ql) and \
               re.search(r"\bfoundation|executive|series\s*0\b|\bs0\b|mangum\b", ql):
                return r
        return None

    # ════════ TOOLS (design §4) ════════
    def corpus_search(self, query: str, filters: dict | None = None, k: int = 5) -> dict:
        miss = self._missing_hit(query)
        if miss:
            return {"ok": True, "missing": True, "status": "MISSING",
                    "reason": f"{miss['volume_id']} — {miss.get('note') or 'unbuilt/never-publishable'}: "
                              "Atlas gap, not a book. No sealed text exists; nothing is generated over it.",
                    "citation": f"[catalog: {miss['volume_id']} · seal_kind {'/'.join(miss['seal_kind'])} · MISSING]",
                    "results": []}
        hits = self._rank(query, filters, k)
        if not hits or hits[0][1] < MIN_SCORE:
            return {"ok": False, "refuse": REFUSE,
                    "reason": f"no catalogued chapter scored above the citation floor ({MIN_SCORE}); "
                              "refusing rather than presenting un-cited prose."}
        out = []
        for i, score in hits:
            c = self.chunks[i]
            out.append({"chunk_id": c["chunk_id"], "kind": c["kind"], "score": round(score, 4),
                        "text": c["text"][:600] + ("…" if len(c["text"]) > 600 else ""),
                        "citation": self._citation(c),
                        "source": {"path": c["source_path"], "sha256": c["source_sha"]}})
        return {"ok": True, "results": out}

    # Atlas positions whose registry slug carries no number (the MISSING gap): S0-04 = XRP.
    _ATLAS = {("S0", 4): "S0/XRP: Decoding Strategy, Technology, and Utility"}

    def corpus_get(self, series: int, vol: int, chapter: int | None = None) -> dict:
        # resolve to a catalog row by (series, vol number), then by known Atlas position (numberless gaps)
        want = f"S{series}"
        row = None
        for r in self.catalog:
            if r["series"] == want and re.search(rf"(?:^|_|/)0*{vol}(?:_|$)", r["slug"]):
                row = r; break
        if not row and (want, vol) in self._ATLAS:
            row = self.cat_by_vol.get(self._ATLAS[(want, vol)])
        if not row:
            return {"status": "MISSING", "reason": f"S{series}-{vol:02d} not in the catalog — not a book."}
        if row.get("missing"):
            return {"status": "MISSING",
                    "reason": f"{row['volume_id']} — {row.get('note') or 'unbuilt / never-publishable'}: "
                              "Atlas gap, not a book.", "citation": f"[catalog: {row['volume_id']} · MISSING]"}
        chs = [c for c in self.chunks if c["volume_id"] == row["volume_id"] and c["kind"] == "chunk"
               and (chapter is None or c.get("chapter") == chapter)]
        if not chs:
            return {"status": "NO_TEXT",
                    "reason": f"{row['volume_id']} is catalogued (seal_kind {'/'.join(row['seal_kind'])}, "
                              f"tier {row['tier']}) but no extracted chapter text is indexed in this build.",
                    "seal_status": row.get("seal_status")}
        chs.sort(key=lambda c: (c.get("chapter", 0), c.get("chunk_ix", 0)))
        return {"seal_status": row.get("seal_status"), "seal_kind": row["seal_kind"],
                "citation": self._citation(chs[0]),
                "text": "\n\n".join(c["text"] for c in chs)}

    def corpus_homes(self, capability: str) -> dict:
        """Sealed home(s) for a capability — cite-or-refuse via retrieval (v1: no separate card map yet)."""
        r = self.corpus_search(capability, filters={"sealed_only": True}, k=3)
        if not r.get("ok") or r.get("missing"):
            return {"ok": False, "capability": capability, "refuse": REFUSE}
        homes = [{"capability": capability, "sealed_home_citation": h["citation"], "score": h["score"]}
                 for h in r["results"] if h["kind"] == "chunk"]
        return {"ok": True, "homes": homes} if homes else {"ok": False, "capability": capability, "refuse": REFUSE}

    def corpus_status(self, series: int | None = None, vol: int | None = None) -> dict:
        rows = self.catalog
        if series is not None:
            rows = [r for r in rows if r["series"] == f"S{series}"]
        if vol is not None:
            rows = [r for r in rows if re.search(rf"(?:^|_|/)0*{vol}(?:_|$)", r["slug"])]
        view = [{"volume_id": r["volume_id"], "title": r["title"], "tier": r["tier"],
                 "seal_kind": r["seal_kind"], "seal_status": r.get("seal_status"),
                 "text_indexed": r.get("text_indexed", False), "missing": r.get("missing", False)}
                for r in rows]
        return {"ok": True, "count": len(view), "volumes": view,
                "totals": self.manifest["counts"]}
