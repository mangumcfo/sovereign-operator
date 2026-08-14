# corpus — sealed-book retrieval plane (v1)

A read-only retrieval plane over the Breathline sealed book catalog, living in its own folder inside
`sovereign-operator` so it can split to a standalone repo later. It lets the operator (and later agents)
**speak architecture from sealed truth, with citations** — or refuse.

Design: [`CORPUS_RETRIEVAL_DESIGN_2026-08-14.md`](CORPUS_RETRIEVAL_DESIGN_2026-08-14.md) (GB) · bar:
AA C1–C10.

## Locks (KM 2026-08-14)

- **126 volumes + XRP as a MISSING row** — XRP (S0-04) is `void` / never-publishable: a catalog gap
  with **no chunks**, so a query about it returns MISSING, never fabricated prose.
- **Public-OK: catalog, extracted text, embeddings. NO PDF/EPUB** in the tree or the index.
- **Chapter-level cites** · content-addressed chunk ids · hybrid dense+BM25 · metadata filters.
- **Local-first embeddings** on operator iron (model+version recorded). **No cloud embed.**
- **No USN/kernel/registry write** — the corpus is a reader; it holds no keys and arms nothing.

## Layout

```
corpus/
  build.py          # extract → chunk → local-embed → index (build-time: pyyaml + loopback Ollama)
  retrieval.py      # stdlib-only: load index, hybrid dense+BM25, cite-or-refuse, the 4 tools
  query.py          # the bar demo (on-corpus cite · XRP MISSING · summary-vs-chunk rank)
  index/            # PUBLIC-OK artifacts:
    catalog.jsonl   #   all 131 rows (126 built + XRP MISSING + 4 concept), seal_kind + stage honest
    chunks.jsonl    #   chapter-aware sealed-text chunks + labeled summary artifacts
    embeddings.jsonl#   768-dim nomic-embed-text vectors (local)
    gaps.jsonl      #   the MISSING rows (XRP)
    MANIFEST.json   #   source SHAs, embed model+version, counts
```

## Source of truth

- **Catalog authority:** GB's `artifacts/catalog/seal_kind_registry.yaml` (131 rows) + `series_roadmap.yaml`,
  in `breathline-workbench`. The corpus is a *projection*; a book change flows in only from a new seal.
- **Text:** Series 5–14 sealed-runtime chapter prose from the press seed `chN.yaml prose:` fields
  (chapter-addressable). Foundational S0–S4 via `pdftotext` when a local PDF is present (text is
  public-OK; the PDF binary never enters the tree). XRP: no text (MISSING).

## The 4 tools (design §4, read-only, cite-or-refuse)

- `corpus_search(query, filters?, k?)` → cited sealed chunks, or `{refuse: "not in the corpus"}`.
- `corpus_get(series, vol, chapter?)` → chapter text + citation, or `{status: MISSING, reason}`.
- `corpus_homes(capability)` → the sealed home citation(s) for a capability.
- `corpus_status(series?, vol?)` → catalog rows (tier · seal_kind · seal_status · MISSING flags).

## Run

```bash
# build (needs a local Ollama with nomic-embed-text; workbench checked out for the source):
python3 corpus/build.py
# demo / bar:
cd corpus && python3 query.py
```

Fences: `retrieval.py` is stdlib-only, embeds over **loopback only** (a non-loopback URL is refused),
imports no USN/kernel package, and has no write path. Summaries are labeled and down-weighted so a
sealed chunk always outranks a matching summary.
