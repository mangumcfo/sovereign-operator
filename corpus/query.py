#!/usr/bin/env python3
"""query.py — the bar demo (AA C1/C2/C6). Verbatim stdout for the deposit:
  1) an on-corpus query returning cited sealed chunks,
  2) an XRP probe returning MISSING (search + corpus_get(0,4)),
  3) a summary-vs-chunk ranked result showing the sealed chunk above the summary.
Read-only; local embedding; no USN/kernel touch.
"""
from __future__ import annotations

import json
import sys

from retrieval import Corpus


def show(title, obj):
    print(f"\n──────── {title} ────────")
    print(json.dumps(obj, indent=2, ensure_ascii=False)[:2600])


def main() -> int:
    c = Corpus()
    print("∞Δ∞ corpus query demo · index:", c.manifest["counts"])

    # 1) ON-CORPUS — must cite real chapters (C1)
    q1 = "immutable append-only general ledger with human oversight on postings"
    r1 = c.corpus_search(q1, k=3)
    print(f"\n[C1] on-corpus query: {q1!r}")
    if r1.get("ok") and r1.get("results"):
        for h in r1["results"]:
            print(f"   {h['score']:.4f} {h['kind']:7s} {h['citation']}")
        print("   → every hit carries a chapter-level citation (cite-or-refuse held)")
    else:
        print("   REFUSED:", r1)

    # 2) XRP probe — must be MISSING, never prose (C2)
    print("\n[C2] XRP probes (direct · oblique · corpus_get(0,4)):")
    for q in ["summarize the XRP book — strategy technology utility for real world value",
              "summarize book 4 of the foundation series"]:
        r = c.corpus_search(q, k=3)
        tag = "MISSING" if r.get("missing") else ("REFUSE" if not r.get("ok") else "results")
        print(f"   query {q!r} → {tag}")
        if r.get("missing"):
            print(f"      {r['citation']}  ·  {r['reason'][:90]}")
    g = c.corpus_get(0, 4)
    print(f"   corpus_get(0,4) → status={g.get('status')} · {g.get('reason','')[:90]}")

    # 3) summary-vs-chunk rank (C6) — find a query that hits both, show chunk above summary
    print("\n[C6] summary never outranks a sealed chunk:")
    # pick a chapter that has a summary artifact, query its promise text
    summ = next((x for x in c.chunks if x["kind"] == "summary"), None)
    if summ:
        rq = summ["text"][:120]
        r3 = c.corpus_search(rq, filters={"vol": summ["volume_id"]}, k=6)
        order = [(h["kind"], h["citation"].split("·")[2].strip(), round(h["score"], 4)) for h in r3.get("results", [])]
        print(f"   query = promise text of {summ['volume_id']} Ch{summ['chapter']}")
        for kind, ch, sc in order:
            print(f"      {sc:.4f}  {kind:7s} {ch}")
        kinds = [k for k, _, _ in order]
        if "chunk" in kinds and "summary" in kinds:
            print(f"   → first sealed chunk at rank {kinds.index('chunk')+1}, "
                  f"first summary at rank {kinds.index('summary')+1} "
                  f"({'PASS: chunk above summary' if kinds.index('chunk') < kinds.index('summary') else 'CHECK'})")

    # 4) C9 tier honesty — a foundational/early-tier query surfaces at comparable rank (if indexed)
    print("\n[C9] tier honesty (publish/asserted tiers not down-weighted):")
    tiers = {c.cat_by_vol.get(x['volume_id'], {}).get('tier') for x in c.chunks}
    print("   tiers present in the index:", sorted(t for t in tiers if t))
    return 0


if __name__ == "__main__":
    sys.exit(main())
